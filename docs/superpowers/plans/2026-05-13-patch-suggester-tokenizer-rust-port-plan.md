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

## 5. ROI 추정 (실측 기반, 2026-05-13 갱신)

**초기 추정 (50-200ms) 은 틀렸음**. Rust isolated bench 측정 결과 ROI 가 훨씬 작음.

### Rust isolated bench (`cargo run --release --example bench_tokenizer`, 1M iter)
| 함수 | 시간 | ns/call | Python ns/call (cProfile) | 가속 |
|---|---|---|---|---|
| `intent_tokens` | 3.02s | 3,021 | 86,000 | 28× |
| `expand_token` | 1.04s | 1,036 | 19,400 | 19× |
| `decompose_korean_compound` | 4.7ms | 5 | 5,390 | 1,078× |

### Workload 환산 (recover --preview 의 실제 호출 횟수)
- 141k intent_tokens × 3,021 ns = 0.43s
- 468k non-nested expand_token × 1,036 ns = 0.49s
- 705k decompose × 5 ns = 4ms
- **Rust 자체 tokenizer 작업 ≈ 1.0s** (Python 의 ~3.7s 대비 73% 절감)

### 옵션 매트릭스 (recover --preview 4.7s → ?)
| 옵션 | Python tokenizer 제거 | IPC 오버헤드 | Rust 자체 | Total | Win | Packaging cost |
|---|---|---|---|---|---|---|
| A. ipc per-leaf | -3.7s | +600k × 1ms = 600s | 1s | unviable | — | low |
| **B. PyO3 ffi** | -3.7s | ~0s | 1s | **~2.0s** | **2.35×** | **multi-week** (mac+Win wheel + PyInstaller hooks + dev Rust toolchain) |
| **C. batch IPC** (per `_score_all_files` 사이클) | -3.7s | ~1ms | 1s | **~2.0s** | **2.35×** (B 와 동일) | none (기존 ipc infra 재사용) |
| C-narrow. batch per-leaf-call | -3.7s | 328 × 1ms = 0.3s | 1s | ~2.3s | 2.04× | none |

**B 와 C(top-level batch) 의 latency gap = ~0s, packaging cost 차이 = multi-week.** → **C 가 명백히 win**.

### 추정 vs 실측 검증
다음 세션 단계 5 에서 `time vib recover --preview --json` warm 3 runs 재측정. 실측이 2.0s 보다 빨라야 정상 (cProfile 의 _intent_tokens cumtime 12s 는 profiling overhead 포함 — warm 4.7s 안에 ~3.7s 만 실제 tokenizer 시간).

---

## 6. 다음 세션 실행 계획

| 단계 | 산출물 | 검증 | 상태 |
|---|---|---|---|
| 1 | Python golden fixtures (`tests/fixtures/tokenizer_goldens/`) | ≥ 100 case × 6 함수 | ✅ **2026-05-13 완료** (102 case × 6 = 612 record, commit `b10fb29`) |
| 2 | Rust `tokenizer.rs` 모듈 (leaf 6 + const table 113) | cargo test parity assert | ✅ **2026-05-13 완료** (612 assertion 통과, commit `7409285`) |
| 3 | C-batch wire + Python `_rust_tokenizer_enabled()` opt-in | `pytest tests/test_patch_*.py` 무회귀 + recover preview 실측 | 다음 세션 |
| 4 | wire smoke (선택) — `wire_smoke_phase3.rs` 패턴 재사용 | `cargo run --example wire_smoke_tokenizer` | 다음 세션 |
| 5 | Bench 재측정 + 본 plan §5 갱신 + 마스터 plan 동기화 | recover --preview before/after | 다음 세션 |

### 단계 3 세부 (이번 세션 design 결과)

- **선택**: C-batch (top-level batch IPC). B (PyO3) 의 packaging 비용 multi-week 가 ROI 0~0.3s 차이로 정당화 안 됨.
- **Refactor 범위 추정**: `patch_suggester.py` 내 leaf 직접 호출 ~17 사이트 (line 317/517/719/763/773/968/1023/1028/1057/1082/1110/1118/1157/1428/1441/1460 등). pre-pass 50 LOC 으로는 부족, deep refactor 500 LOC 까지는 안 감 → **~200 LOC C-medium** 추정. 단일 세션 boundary 시도, 막히면 multi-session 분해.
- **IPC 디자인**: `EngineRequest::TokenizeBatch { inputs: Vec<String>, mode: TokenMode }` 단일 variant. `TokenMode` = `IntentTokens` | `PathTokens` | `Tokenize` (3 outer 함수 모두 batch). leaf 6 함수는 outer 안에서 only 호출되므로 별도 노출 불필요.
- **Opt-in flag**: `VIBELIGN_RUST_TOKENIZER=1` env (secret_scan 선례 그대로). default off, 한 릴리즈 검증 → 다음 default on.

---

## 7. Risks

| Risk | 영향 | 완화 |
|---|---|---|
| R1. 추정 ROI 빗나감 | 본 plan 무가치 | 단계 5 실측, 부족하면 batch shape 재설계 |
| R2. `_TOKEN_ALIASES` 가 자주 수정됨 | Python ↔ Rust drift | Python 을 source-of-truth 로 두고 build-time codegen script (`tools/sync_tokenizer_aliases.py`) 권장. 현재는 fixture regenerate + cargo test 가 drift 감지 |
| R3. opt-in flag 디폴트 전환 시점 | 회귀 가능 | secret_scan 패턴: 한 릴리즈 opt-in → 다음 default on |
| R4. AI provider / write 의존 leak | 단일 세션 무리 | leaf 함수가 모두 pure 임을 확인 완료 — Rust 포팅이 어떤 외부 자원도 끌어들이지 않음 ✅ 단계 2 검증됨 |
| R5. PyO3 packaging multi-week cost | 옵션 B 선택 시 mac+Win 양쪽 native wheel + PyInstaller hooks + dev Rust toolchain. 메모리 `vibelign_gui_vib_sidecar_onedir` 의 sidecar 번들링 burn 이력 있음 | 옵션 C 선택 (이번 세션 결정) — 기존 ipc infra 재사용, packaging 변화 없음. B 는 ROI gap 이 측정적으로 정당화될 때만 재검토 |
| R6. C-medium refactor 가 단일 세션 boundary 넘김 | 단계 3 multi-session 분해 | sub-slice 가능 — outer 함수 단위 (`intent_tokens`/`path_tokens`/`tokenize`) 각각 별 commit. 첫 outer 만 진행 후 측정해도 절반 win 확보 |

---

## 8. 이번 세션 산출물 (2026-05-13)

design phase + 단계 1 + 단계 2 모두 완료 (코딩 진입은 단계 3 부터).

- ✅ 본 plan 문서 (one-pager, 5 commit 누적 후 §5/§6/§7/§8 실측 기반 갱신)
- ✅ 부모 plan `2026-05-07-rust-engine-utilization-plan.md` 에 한 줄 reference 추가
- ✅ `tests/fixtures/tokenizer_goldens/` — fixture 6개 (102 case × 6 함수 = 612 expected record) + `_regenerate.py` (`uv run python ...` 호출)
- ✅ `vibelign-core/src/tokenizer.rs` — 6 leaf 함수 + 3 const table + 2 OnceLock regex
- ✅ `vibelign-core/examples/bench_tokenizer.rs` — isolated bench (1M iter)
- ✅ `vibelign-core/src/lib.rs` — `mod tokenizer;` private (`#[allow(dead_code)]` 단계 3 노출 시 제거)
- ✅ 검증: `cargo test --lib` 134 → 140 / `cargo check` (vibelign-gui/src-tauri) 0 warnings/errors
- ✅ advisor 2회 호출로 (1) hot path 식별 (recovery → patch_suggester) (2) 옵션 매트릭스 (A/B/C) 결정 (3) ROI 계산 정정 (94× → 2.35×)

다음 세션 진입점: §6 단계 3 (C-batch wire + opt-in flag).
