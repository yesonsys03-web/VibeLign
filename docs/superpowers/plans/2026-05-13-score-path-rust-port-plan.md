# score_path Rust port — multi-session 트랙 plan

- 작성: 2026-05-13
- 상태: **design phase** (코딩 미진입)
- 부모 plan: `2026-05-07-rust-engine-utilization-plan.md`
- 선행 트랙: `2026-05-13-patch-suggester-tokenizer-rust-port-plan.md` (§9 retraction lesson 의 후속)

---

## 1. 동기 / 측정 데이터

### 시발점
tokenizer leaf port 트랙 §9 retraction lesson: "진짜 hot 은 `score_path` 의 caller-side set 처리 — leaf level Rust port 만으로는 wall ROI 0, multi-session 트랙으로 이관". 본 plan 이 그 트랙.

### Apples-to-apples wall (2026-05-13, `uv run python -c "<vib_cli.main>"` harness, warm × 3)

| Mode | Wall (mean) |
|---|---|
| baseline (normal `score_path`) | **4.51s** |
| `score_path` stub `(0, [])` | **2.08s** |

→ stub diff = **2.43s**. 이전 stub 측정 2.84s 는 `vib` binary vs `uv run python -c` harness 차이로 부풀려진 값.

### ROI bound (§9 lesson 적용)

- stub `(0, [])` 은 downstream `_score_all_files` ranking 을 short-circuit (empty candidates → 다른 분기 skip).
- real Rust impl 은 정확한 score 반환 → downstream 정상 작동 → wall ROI 가 stub diff 보다 작을 수 있음.
- **wall ROI 범위 = 0 ~ 2.43s** (구현 전 측정 불가, probe 후 확정 필요).
- 사용자 체감 = recover preview 패널 (RecoveryOptionsCard `useEffect` mount auto-call) lag. 4.5→2.1s 면 명백한 win, 4.5→4.0s 면 marginal.

### Probe (다음 세션 첫 작업, ROI bound 좁히기)

- 가장 작은 hot helper (`_meaningful_overlap`, 8 LOC pure) Rust 포팅 + batch wire 1 callsite → wall 재측정.
- 실측이 4.5s → 4.3s 정도면 IPC overhead dominate → 트랙 retract (§9 precedent).
- 실측이 4.5s → 3.0s 정도면 batch 자체가 wall 큰 부분 처리 → 본 plan 전체 진행 가치 확정.

---

## 2. 트랙 사이즈 (총 ~600~700 LOC 포팅 + 데이터 모델)

| 항목 | LOC | 카테고리 |
|---|---|---|
| `score_path` body (line 510~920) | 411 | orchestration |
| `_score_anchor_names` | 160 | scoring helper |
| boolean helpers (`_is_ui_request` / `_is_navigation_request` / `_is_service_request` / `_is_stateful_ui_request` / `_classify_request_verb`) | ~40 | pure |
| `_meaningful_overlap` | 8 | pure |
| Module-level constants (`KEYWORD_HINTS` / `LOW_PRIORITY_NAMES` / `_FRONTEND_EXTS` / `_BACKEND_CHECKPOINT_HINTS` / `_CHROME_FILE_HINTS` / `_COMMAND_FILE_HINTS` / `_NAVIGATION_FILE_HINTS` / `_STATE_OWNER_FILE_HINTS`) | ~200 | data |

추가 외부 의존:
- `ProjectMapSnapshot.classify_path` — `vibelign/core/project_map.py` 의 method (별도 모듈).
- `vibelign-core/src/tokenizer.rs` — `_path_tokens` 의 leaf 6 함수 (이미 dormant library 로 존재, 본 트랙에서 재사용).

---

## 3. Plan-blocker 결정 (측정으로 해소됨)

### classify_path conflict — 비-issue

- 기존 framing: 메모리 룰 "절대 옮기지 말 것" 의 `change_explainer.py:60` 의 `def classify_path`.
- 실측: `score_path` body line 577 의 `project_map.classify_path(rel_path)` = `ProjectMapSnapshot` **method** (`vibelign/core/project_map.py` 안). `change_explainer` 의 함수와 **무관**.
- → 룰 위반 없이 진행 가능. project_map 모듈은 룰에 없음. 옵션: (a) Rust 도 `classify_path` 포팅, (b) Python 측 pre-pass 로 path → classification dict 전달 (batch IPC input 의 일부).
- 권장: (b) Python 측 pre-pass — project_map 자체는 Python 유지, IPC input 으로 결과만 전달.

### Batch wire 필수성

- `_meaningful_overlap` 호출 횟수 = **144,414** (1 score_path 당 ~440번).
- per-call IPC (daemon socket ~1ms) × 144k = ~144s = **unviable**.
- → **batch 디자인 필수**: `score_path` 의 path-level pre-pass refactor — Python 측에서 모든 candidate 의 input 을 모은 후 1 IPC 로 Rust 가 batch 내 모든 score 계산.

### IPC shape (제안)

```rust
EngineRequest::ScorePathBatch {
    request_tokens: Vec<String>,
    candidates: Vec<ScorePathCandidate>,
    ui_request: bool,
    navigation_request: bool,
    service_request: bool,
    stateful_ui_request: bool,
    // ... (boolean helpers 의 결과를 Python 측에서 미리 계산 후 전달 — leaf rust-port 의 필요성 약화)
}

struct ScorePathCandidate {
    path: String,
    rel_path: String,
    stem: String,
    path_tokens: Vec<String>,  // _path_tokens(rel_path) 결과 — 이미 Rust 가능
    classification: Option<String>,  // project_map.classify_path(rel_path) Python pre-compute
    anchor_meta: Option<AnchorMetaEntry>,
    // ...
}

EngineResponse::ScorePathBatchOk {
    scored: Vec<ScoredPath>,  // (score, rationale) tuples
}
```

→ 1 IPC per `_score_all_files` cycle (preview 마다 1번) = ~1ms IPC overhead, Rust 가 batch 내 모든 logic 계산. 진짜 답.

---

## 4. 분해 plan (4~6 multi-session 추정)

### Session 1 — probe + plan 확정 (다음 세션)
- (a) `score_path` body line 510~920 정독 → 외부 의존성 정확 매핑 (각 분기 의 input 카탈로그)
- (b) batch wire shape 디자인 확정 — `ScorePathCandidate` struct 의 필드 nature 결정
- (c) probe: `_meaningful_overlap` 단일 Rust 포팅 + batch wire 1 callsite → wall 재측정
- (d) 본 plan §5 ROI 갱신 (실측 기반)
- 산출: plan 확정 + Rust skeleton + probe wall 측정. 코딩 일부 시작.

### Session 2 — Module-level data Rust const
- 8 const table (`KEYWORD_HINTS` 등) → `vibelign-core/src/score_path_data.rs`
- Python source-of-truth + cargo test data parity (~200 LOC data)
- secret_scan / tokenizer 패턴 그대로
- `tests/fixtures/score_path_data/` (또는 inline const)

### Session 3 — Pure helpers (boolean + overlap)
- `_is_ui_request` / `_is_navigation_request` / `_is_service_request` / `_is_stateful_ui_request` / `_classify_request_verb` / `_meaningful_overlap` 6 함수 Rust 1:1 port
- Golden fixtures (Python source-of-truth) + cargo test parity
- (probe 의 `_meaningful_overlap` 보강)

### Session 4 — `_score_anchor_names`
- 160 LOC anchor scoring helper port
- anchor_meta input 직렬화 (`AnchorMetaEntry` struct)
- parity fixtures

### Session 5 — score_path body batch handler
- 411 LOC body → Rust `score_path_batch(request: ScorePathBatch) -> Vec<ScoredPath>`
- ProjectMapSnapshot 직렬화 (path → classification dict 사전 계산해서 input 으로 전달)
- BatchScoreRequest 입력 구조 + handler
- parity fixtures: whole recover preview run 의 ranked_candidates 결과 byte-equal 검증

### Session 6 — Wire integration + opt-in flag + Python retire
- `EngineRequest::ScorePathBatch` variant 노출
- Python `_rust_score_path_enabled()` opt-in (`VIBELIGN_RUST_SCORE_PATH=1`, secret_scan 선례)
- `vibelign/core/patch_suggester.py::_score_all_files` 가 flag on 시 batch IPC 경로
- recover preview wall before/after 실측 + 본 plan §1 갱신
- 한 릴리즈 opt-in → 다음 default on

---

## 5. Risks

| Risk | 영향 | 완화 |
|---|---|---|
| R1. 실제 ROI 가 bound 의 하단 (~0s) | 본 plan 무가치 | Session 1 probe 후 즉시 측정. 작으면 **트랙 retract** (§9 retraction precedent). 측정 전 commit 없음. |
| R2. ProjectMapSnapshot 직렬화 비용 | IPC overhead 가 ROI 잡아먹음 | 일회성 large input + 결과 small. 호출 외부 (per-preview) 에 1번만. Session 1 probe 로 검증. JSON serialize 가 너무 크면 binary (bincode) 고려. |
| R3. score_path 411 LOC 의 conditional branch 복잡 | Rust 정확 port 어려움 | parity fixtures (whole recover preview ranked_candidates 결과 캡처) 로 byte-equal 검증 + Session 5 분해 |
| R4. `KEYWORD_HINTS` 자주 수정됨 (tokenizer alias drift 같은 패턴) | Python ↔ Rust 동기 깨짐 | Python source-of-truth + cargo test 가 drift 감지 (tokenizer 트랙 패턴 그대로) |
| R5. `_score_anchor_names` 160 LOC 가 anchor_meta dict 깊은 의존 | Rust struct 직렬화 큼 | Session 4 별 session 으로 분리 |
| R6. 측정 lesson 미적용 risk | tokenizer 트랙 §9 retraction 재발 | apples-to-apples baseline + stub-patch wall diff 룰 적용. cProfile/pyinstrument cumtime 신뢰 X. |

---

## 6. 이번 세션 산출물

- 본 plan 문서 (one-pager, design phase)
- 메모리 + handoff 갱신 (next 세션 probe 진입)

코딩 없음. Session 1 probe 부터 코딩 시작.

부모 plan (`2026-05-07-rust-engine-utilization-plan.md`) 에 reference 한 줄 추가 권장:

> 🆕 **2026-05-13 신규 multi-session 트랙 진입**: score_path Rust port — tokenizer leaf port 트랙 §9 retraction lesson 의 후속. stub diff 2.43s wall (apples-to-apples), ROI bound 0~2.43s (probe pending). 4~6 multi-session 분해. 상세: `2026-05-13-score-path-rust-port-plan.md`.
