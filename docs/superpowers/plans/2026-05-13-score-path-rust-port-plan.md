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

### Probe (Session 1, 2026-05-13 실행 완료)

`_meaningful_overlap` Rust 1:1 port (commit `740c22c`) + ipc variant + Python opt-in single callsite wire (commit `8a04c8d`) 완료. score_path body line 537 (path-level 1번/path = 328 호출) 만 routing.

| Mode | Wall warm × 3 mean |
|---|---|
| `VIBELIGN_RUST_SCORE_PATH=0` (baseline) | 4.556s |
| `VIBELIGN_RUST_SCORE_PATH=1` (single callsite, 328 IPC) | 4.511s |
| diff | ~45ms (variance 안, noise) |

**결과**:
- 🟢 wire infra 작동 — pytest 회귀 0 (`test_patch_suggester_score_candidates` / `test_recovery_planner` 30 passed), IPC + Python fallback 정상.
- 🟡 single callsite wall ROI = noise — 144k 호출 중 328 (path-level 1번/path) 만 routing 이라 wall 측정 단순 비교 불가.
- 🟢 IPC budget 검증 — single callsite 가 wall regression / timeout 없음. **infra fits inside budget** (advisor probe 의도 통과).
- 🔴 batch wire 필수성 입증 — 144k 호출 중 99% 가 nested loop 안 (`score_path` line 726/770/780 의 anchor/alias/desc loops + `_score_anchor_names` line 325 등). path-level pre-pass refactor 가 진짜 답.

**ROI bound 유지: 0~2.43s** — single callsite 측정으로 IPC dominate 배제 됨. batch wire 후 실측으로 다시 좁힘.

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

### Session 1 — probe (2026-05-13 완료)
- ✅ Rust `vibelign-core/src/score_path.rs::meaningful_overlap` 1:1 port + 5 unit tests (commit `740c22c`).
- ✅ ipc variant `EngineRequest::MeaningfulOverlap` + handler dispatch (commit `740c22c`).
- ✅ Python opt-in wire `VIBELIGN_RUST_SCORE_PATH=1` + score_path body line 537 single callsite routing (commit `8a04c8d`).
- ✅ wall 측정 (warm × 3): rust off 4.556s vs rust on 4.511s = ~45ms (noise). §5 Probe 표 참조.
- 🟢 wire infra fits inside budget — pytest 회귀 0, regression/timeout 없음.
- 🔴 batch wire 필수성 입증 — single callsite 만으로는 wall ROI 0 (144k 중 328 만 routing).

### Session 1.5 — batch wire shape 디자인 (다음 세션 첫 작업)
- score_path body line 510~920 정독 → 모든 `_meaningful_overlap` 호출 위치 카탈로그 (line 537 / 726 / 770 / 780 + `_score_anchor_names` line 325 + 다른 분기 line 1064 / 1089 / 1117 / 1125 / 1164 등).
- `_score_all_files` pre-pass refactor 디자인 — 모든 (request_tokens, candidate_tokens) tuples 수집 → 1 IPC → result dict → score_path 안에서 dict lookup.
- ipc variant `EngineRequest::MeaningfulOverlapBatch { pairs: Vec<(Vec<String>, Vec<String>)> }` 정의.
- batch wire 후 wall 재측정 — ROI bound 좁힘 (실측).
- 결과 nonn-noise 면 본 plan §6 Session 2~6 진행, noise 면 §9 retraction precedent 적용.

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

---

## 9. Retraction / Skip-rate Lessons (2026-05-13, Session 1.5 진입 후)

### Skip-rate discriminator (advisor 권고)

Session 1 probe 후 Session 1.5 batch wire 디자인 시도. score_path body 의 `_meaningful_overlap` 호출 4군데 (line 537/726/770/780) 모두 conditional iteration 안 (anchor / alias / desc loops). pre-pass batch 가 단순 refactor 가 아니라 score_path 본체 port (Session 5) 와 동일 → framing 자체 무너짐.

또 advisor 권고 한 가지 더: **Python 의 빠른 conditional skip path 가 Rust batch 의 net win 잡아먹을 수 있음**. 측정:

```
total _meaningful_overlap 호출: 144,551
empty results: 140,175 → skip rate 97.0%
non-empty (Python 실제 작업): 4,376 (3.0%)
```

→ Python 은 144k 호출 중 4k 만 진짜 작업, 나머지 140k 는 `set(candidate_tokens)` + iteration 후 즉시 `if not matched: continue` 로 빠른 path. Rust batch 가 144k 모두 계산 = ~0.5-1s, Python 의 4k 작업 (~수십 ms) 보다 비쌈. **net win 마이너스 또는 noise**.

### 추가 sub-slice 측정 (옵션 C 의 결과)

`_score_anchor_names` stub `(0, [])` × 3 (uv harness):

| Mode | Wall (mean) |
|---|---|
| baseline | 4.268s |
| `_score_anchor_names` stub | 4.255s |
| diff | ~13ms (noise) |

→ `_score_anchor_names` 도 wall hot 아님 (호출 횟수 656 회, 작음). 160 LOC port 의 ROI 도 noise.

### 종합 진단

- `_meaningful_overlap` 자체 가속 ROI = ~수십 ms (skip 97% 의 hot path 가 짧음)
- `_score_anchor_names` ROI = ~13ms
- score_path 의 wall ~2.4s 는 **다양한 분기 cumulative** (KEYWORD_HINTS dict iteration / `_FRONTEND_EXTS` set 체크 / `_BACKEND_*` hint sets / conditional branches / `path_tokens` 호출 / anchor scoring 등) — 어느 sub-slice 도 dominant 아님
- score_path 통째 Rust port (4~6 session) 의 잠재 win 도 conditional skip 빠른 path 가 Rust 의 cost 와 비슷하거나 작음 — net win ~수십 ms 수준
- **결론: 4~6 multi-session 비용 vs ~수십 ms ROI = 명백히 정당화 안 됨**

### Measurement lessons (tokenizer §9 보강)

1. **stub-patch wall diff 는 위 추정** — 진짜 ROI 는 conditional flow 가 share. real Rust impl 은 conditional skip 도 모두 계산 (또는 skip 정보 IPC 로 전달 — 추가 복잡성).
2. **Skip rate 가 sufficient discriminator** — 90% 이상이면 leaf-port batch 가치 작음. 측정 30초.
3. **3 stub-patch 비교 (single helper / score_path 통째 / 부모 caller) 가 wall share 결정** — 호출 횟수 (cProfile ncalls) 와 wall share 가 직접 비례하지 않음.

### 트랙 status update

- ✅ **Session 1 probe artifacts 보존** (Rust 측):
  - `vibelign-core/src/score_path.rs::meaningful_overlap` (1:1 port + 5 parity tests, commit `740c22c`)
  - `EngineRequest::MeaningfulOverlap` / `EngineResponse::MeaningfulOverlapOk` ipc variants (commit `740c22c`)
  - `ipc::handler` dispatch arm (commit `740c22c`)
  - `cargo test --lib` 140 → 145 passed. Python alias drift parity 가치 + 미래 score_path port 시도 시 dormant library.
- 🔁 **Python wire revert** (commit `af2036f`) — `_rust_score_path_enabled()` flag + `_meaningful_overlap_with_rust()` wrapper + score_path body line 537 conditional. tokenizer §9 의 lru_cache revert + tokenizer.rs 보존 패턴 그대로.
- 🛑 **§6 Session 1.5 ~ Session 6 retract** — 4~6 multi-session 비용 vs ~수십 ms ROI 가 정당화 안 됨.
- 🆕 **새 트랙 후보 (별 plan)**: 만약 진짜로 recover preview 가속이 필요하면, score_path 전체 통째 Rust port 가 multi-session 큰 작업 — net win bound 도 작아서 다른 트랙 (예: recovery preview 자체의 cache, 또는 Python skip path 의 추가 최적화) 가 ROI 더 좋을 수도. 별 plan 검토 필요.

### Rust artifact 보존 정당화

- `vibelign-core/src/score_path.rs`: 정확한 1:1 port + 5 parity tests. Python `_meaningful_overlap` 의 dict.fromkeys 순서 보장이 Rust HashSet 으로 byte-equal — alias drift / refactor 시 자동 검증. `#[allow(dead_code)]` 추가 시 ipc 노출 후 제거 가능 — 현재 ipc 통해 호출 가능하므로 dead_code warning 없음.
- ipc variant `MeaningfulOverlap`: 외부 consumer (예: GUI 의 path scoring widget, 또는 미래 score_path 통째 port 시도) 가 호출 가능. 영구 노출 유지.

---

## 끝 — 본 plan 의 트랙은 §9 retraction 으로 종료. artifacts (commit `740c22c`) 보존.
