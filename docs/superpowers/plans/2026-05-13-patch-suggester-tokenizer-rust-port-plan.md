# patch_suggester tokenizer — Rust leaf hot-path port plan

- 작성: 2026-05-13
- 상태: **design phase** (코딩 미진입)
- 트랙: 기존 7-candidate consumer migration 리스트 외 신규 후보 (어제 핸드오프의 "트랙 B" 진입 시 피벗된 결과)
- 부모 plan: `2026-05-07-rust-engine-utilization-plan.md`

---

## 1. 동기 / 측정 데이터

### 시발점
2026-05-12 핸드오프: "남은 7개 runVib 호출은 모두 multi-session 후보". 트랙 B (multi-session) 진입 시 ROI 측정에서 doctor vs recovery 둘 다 read-only sub-slice 매칭으로 좁힘.

### Python 벤치 (warm, 3 runs)
| 명령 | 평균 |
|---|---|
| `vib doctor --json` | ~118 ms |
| `vib recover --preview --json` | **~4,700 ms** |

→ 40× 차이로 recovery 우선. 그러나 4.7s 분포를 모르고 분해 plan 사이즈를 못 정함 → cProfile.

### cProfile (recover --preview, 15.5s with profiling overhead)
| 항목 | cumtime | 비율 |
|---|---|---|
| `patch_suggester._score_all_files` | 13.288s | **86 %** |
| → `_intent_tokens` (141,672 calls) | 12.17s | |
| → `_expand_token` (609,631 calls) | 11.82s | |
| → `_normalize_korean_token` (609,631 calls) | 5.91s | |
| → `_decompose_korean_compound` (705,303 calls) | 3.80s | |
| `recovery/signals.collect_basic_signals` | 1.97s | |
| subprocess / IPC | 1.66s | |

**결론**: recovery 가 무거운 것이 아님. `patch_suggester` 의 한국어 토큰 분해/정규화 hot loop 이 모든 시간을 잡아먹음.

---

## 2. 후보 재정의 (recovery → patch_suggester tokenizer)

원래 후보 (`recoveryPreview` consumer migration) 에서 hot path 그 자체로 재정의.

### 포팅 대상 (pure leaf 함수 6개, ~60 LOC)
- `vibelign/core/patch_suggester.py:187` `_decompose_korean_compound`
- `vibelign/core/patch_suggester.py:215` `_split_identifier_parts`
- `vibelign/core/patch_suggester.py:220` `_normalize_korean_token`
- `vibelign/core/patch_suggester.py:230` `_expand_token`
- `vibelign/core/patch_suggester.py:252` `tokenize`
- `vibelign/core/patch_suggester.py:293` `_intent_tokens`

### Rust const table 이식 대상 (~113 static entries)
- `_TOKEN_ALIASES` — 37 entries (Korean → English alias list)
- `_KOREAN_ALIAS_KEYS` — 37 keys (sorted desc by length for greedy match)
- `_KOREAN_PARTICLE_SUFFIXES` — 39 entries

### Python 유지 (out-of-scope)
- `_score_all_files`, `score_path`, `suggest_patch` orchestration — 328 호출만 (leaf 609,631 대비 0.05%). leaf 가속만으로 ~90% 시간 회수.

### Consumer 팬아웃 (1 포팅 → 다중 consumer 가속)
- `vibelign/core/codespeak.py:760` — AI codespeak suggest (`suggest_patch`)
- `vibelign/core/recovery/planner.py:8` — recovery preview (`suggest_recovery_level2_patch`)
- `vibelign/patch/patch_contract_helpers.py:6` — patch contract (`tokenize`)
- `vibelign/patch/patch_targeting.py:7` — patch targeting (`resolve_target_for_role`)
- `vibelign/commands/vib_bench_cmd.py:78` — bench (`score_candidates`, `suggest_patch`)
- (간접) `vibelign/core/anchor_tools.py:770` — `_TOKEN_ALIASES` reverse 룩업

---

## 3. Parity 전략 (secret_scan 선례)

레퍼런스: `vibelign-core/src/secret_scan.rs` 헤더 — *"Python is the source of truth"*.

1. **Golden fixtures**: `tests/fixtures/tokenizer_goldens/` — 영어/한국어 mixed input 100 case + Python 현재 출력 JSON 기록 (`*.input.txt` + `*.expected.json`)
2. **Python opt-in flag**: `vibelign/core/patch_suggester.py` 에 `_rust_tokenizer_enabled()` (env `VIBELIGN_RUST_TOKENIZER=1` 또는 config). 기본 off → 한 릴리즈 검증 → 다음 릴리즈 default on (secret_scan 패턴)
3. **Rust unit test**: 각 leaf 함수별 golden assert (`cargo test`)
4. **Wire integration**: `_normalize_korean_token` 등 entry point 에서 Rust 호출 + fallback to Python (flag off 시)

---

## 4. Single-session sub-slice 확신 근거

| 지표 | 값 | 비고 |
|---|---|---|
| Leaf 함수 LOC | ~60 | 6 함수, pure |
| Static data | 113 entries | const table |
| IPC | 없음 | pure CPU |
| AI provider | 없음 | |
| File / git side-effect | 없음 | |
| Write | 없음 | read-only |
| 선례 | secret_scan | 동일 패턴, 이미 닫힌 슬라이스 |

→ **단일 세션 가능성 매우 높음**.

---

## 5. ROI 추정 (보수적, 추정은 추정)

- Python 4.7s warm → Rust 50–200 ms (regex + unicode 가 CPU-bound 라 Rust 의 ICU/unicode-segmentation 으로 명백한 win)
- `recoveryPreview` 패널 mount lag: 4.7s → ~0.2s — 사용자 체감 명확 (RecoveryOptionsCard `useEffect` 마운트 자동 호출)
- AI codespeak / patch suggest 호출도 동시 가속

**추정 vs 실측 검증**: 첫 슬라이스 끝나면 동일 bench (`time vib recover --preview --json` warm 3 runs) 재측정 후 plan 갱신.

---

## 6. 다음 세션 실행 계획 (코딩 — 이번 세션 X)

| 단계 | 산출물 | 검증 |
|---|---|---|
| 1 | Python golden fixtures 생성 | `tests/fixtures/tokenizer_goldens/` ≥ 100 case |
| 2 | Rust `tokenizer.rs` 모듈 (leaf 6 + const table) | cargo test parity assert |
| 3 | Python `_rust_tokenizer_enabled()` opt-in + per-call fallback | `pytest tests/test_patch_*.py` 무회귀 |
| 4 | wire smoke (선택) — `wire_smoke_phase3.rs` 패턴 재사용 | `cargo run --example wire_smoke_tokenizer` |
| 5 | Bench 재측정 + 본 plan §5 갱신 + 마스터 plan 동기화 | recover --preview before/after 비교 |

---

## 7. Risks

| Risk | 영향 | 완화 |
|---|---|---|
| R1. 추정 50ms 가 빗나감 | ROI 낮음 | 첫 슬라이스 직후 실측, 부족하면 IPC 형태 재설계 |
| R2. `_TOKEN_ALIASES` 가 자주 수정됨 | Python ↔ Rust drift | Python 을 source-of-truth 로 두고 build-time codegen script (`tools/sync_tokenizer_aliases.py`) 권장 |
| R3. opt-in flag 디폴트 전환 시점 | 회귀 가능 | secret_scan 패턴: 한 릴리즈 opt-in → 다음 default on |
| R4. AI provider / write 의존 leak | 단일 세션 무리 | leaf 함수가 모두 pure 임을 확인 완료 (이번 세션) — Rust 포팅이 어떤 외부 자원도 끌어들이지 않음 |

---

## 8. 이번 세션 산출물

본 plan 문서 자체. 다음 세션부터 §6 단계 1~5 실행.

부모 plan (`2026-05-07-rust-engine-utilization-plan.md`) 에 한 줄 reference 추가 권장:

> 🆕 **2026-05-13 신규 트랙 진입**: patch_suggester tokenizer leaf hot-path port — recovery preview 4.7s 의 86% 가 한국어 토큰 분해. 7-candidate consumer migration 외 신규 후보. 상세: `2026-05-13-patch-suggester-tokenizer-rust-port-plan.md`
