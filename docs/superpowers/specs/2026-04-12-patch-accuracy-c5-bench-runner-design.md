# C5: Patch Accuracy Bench Runner 설계

**작성일:** 2026-04-12
**상태:** 설계 확정, 구현 플랜 작성 대기
**관련 문서:**
- `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md` (ICE 라운드, C5 후보 정의)
- `docs/superpowers/plans/2026-04-12-patch-accuracy-c6-ai-deference.md` (C6 완료)

## 1. 목표

`vib bench --patch` 커맨드를 추가해 patch accuracy 회귀 테스트를 **1 커맨드**로 재현 가능하게 한다.
C1/C6 까지는 사람이 수동으로 `suggest_patch()` 를 호출하고 눈으로 숫자를 옮겨 적었고,
이는 (a) 노동집약적이고 (b) 측정 경로가 글로 표준화돼 있지 않아 실행자마다 숫자가 다르게 나왔다.
C5 는 이 두 문제를 해결하는 것이 유일한 목적이다.

**비목표 (명시적 제외):**
- 시나리오 히스토리/트렌드 시각화
- 다중 provider (gemini/claude/gpt) 스위칭 비교
- 랜덤 샘플링, flaky run 재시도, 통계적 분포 분석
- 기존 `vib bench` A/B anchor-effect 경로 (`--generate` / `--score` / `--report`) 변경

## 2. 측정 원칙

### 2.1 Pinned-intent 샌드박스가 canonical

`vib anchor --auto` 는 intent 생성을 LLM 에 의존해 매 실행마다 drift 가 생긴다.
드리프트는 `suggest_patch` 의 스코어링 입력을 바꾸므로 "어제의 숫자"와 "오늘의 숫자"가
코드 변경 없이도 달라진다. 이는 회귀 가드로서 치명적이다.

C5 는 `tests/test_patch_accuracy_scenarios.py::_prepare_sandbox` 와 **동일한 로직**을 사용한다:
1. `tests/benchmark/sample_project` 를 tmp 로 copytree
2. `vib start` → `vib anchor --auto` 실행 (마커 삽입 + `anchor_index.json` 생성, 둘 다 결정적)
3. `anchor_meta.json` 을 pinned `PINNED_INTENTS` dict 로 덮어쓰기

`vib patch --ai --json` CLI 경로는 **점수 근거로 쓰지 않는다**. 그건 wiring smoke test 용이다.
C5 는 `suggest_patch()` 를 Python 으로 직접 호출한다.

### 2.2 Pinned-intent 픽스처 공유

현재 `_PINNED_INTENTS` 와 `_prepare_sandbox` 는 `tests/test_patch_accuracy_scenarios.py` 안에 private (`_` prefix) 로 갇혀 있다.
C5 러너와 테스트 양쪽에서 쓰려면 공유 위치가 필요하다.

**위치:** `vibelign/commands/bench_fixtures.py` (신규)
- `PINNED_INTENTS: dict[str, str]` — 24 앵커의 pinned intent
- `prepare_patch_sandbox(tmp: Path) -> Path` — copytree + vib start + vib anchor --auto + intent 덮어쓰기

테스트 파일은 이를 re-export 또는 직접 import 하도록 얇게 수정한다.
프로덕션 코드 (`vibelign/commands/`) 로 옮기는 이유: 러너가 이를 런타임에 쓰기 때문에
test-only 경로에 두면 import 상 `tests/` 가 sys.path 에 있어야 한다는 이상한 의존이 생긴다.

## 3. 메트릭

3 개 메트릭을 시나리오별 × 모드별 (`deterministic` vs `--ai`) 로 기록한다.

### 3.1 `files_ok`
`result.target_file` 이 `scenario.correct_files` 에 포함되는가.
→ **최종 정확도 메트릭.** 사람이 보는 숫자.

### 3.2 `anchor_ok`
`result.target_anchor == scenario.correct_anchor`.
단, `scenario.correct_anchor` 가 null 인 경우 (= 앵커 단위까지는 판정 안 함) 해당 시나리오는 이 메트릭에서 제외.
→ `correct_files` 에서 정답을 맞혔을 때 앵커 단위까지 정확했는지 측정.

### 3.3 `prefilter_recall@3`
**신규 메트릭.** Deterministic 파일 랭킹 상위 3 개 안에 정답이 들어 있는가.
- 측정 대상은 deterministic 경로 (= AI 호출 전 원시 랭킹) 1 곳만
- `--ai` 모드에도 동일 값이 적용된다 (AI 호출 전 prefilter 는 같음)
- 숫자 3 의 근거: `_ai_select_file` 은 top 10 을 AI 에게 넘기지만, C6 deference 이후
  high-confidence 케이스는 AI 가 아예 안 불린다. 즉 "AI 가 볼 수 있는 범위" 는 가치 프록시가 아니고
  "deterministic 이 정답을 최상위권에 얼마나 집중시켰는가" 가 실제 가치다. Top-3 는 이 엄격한 프록시.
- Top-5 는 10 중 절반이라 사실상 거의 항상 맞는다 → 회귀 감지 감도가 낮음

## 4. 새 API: `score_candidates`

메트릭 3.3 을 측정하려면 `suggest_patch` 내부에서 파일 랭킹만 따로 꺼낼 수 있어야 한다.
현재는 랭킹이 `suggest_patch` 함수 중간에 스코프드 변수로 들어 있어 외부에서 접근 불가.

**리팩토링 (behavior-preserving):**
- `vibelign/core/patch_suggester.py` 에 `score_candidates(root: Path, request: str) -> list[tuple[Path, float]]` 추가
- `suggest_patch` 내부의 파일 랭킹 로직을 이 함수로 추출
- `suggest_patch` 는 `score_candidates` 를 호출해 기존 동작 그대로 재현
- 반환값은 내림차순 정렬된 `(Path, score)` 튜플 리스트 (앵커는 포함하지 않음 — 파일 단위 prefilter 측정용)

**회귀 가드:** 기존 `tests/test_patch_accuracy_scenarios.py` 의 3 개 assertion 이 여전히 통과해야 한다.
리팩토링이 어떤 시나리오든 바꾸면 실패.

## 5. Baseline 파일

### 5.1 위치
`tests/benchmark/patch_accuracy_baseline.json`

### 5.2 형태
```json
{
  "pinned_intents_version": "2026-04-12",
  "generated_at": "2026-04-12",
  "scenarios": {
    "change_error_msg": {
      "det": {"files_ok": true, "anchor_ok": true, "recall_at_3": true},
      "ai":  {"files_ok": true, "anchor_ok": true, "recall_at_3": true}
    },
    "add_email_domain_check": { ... },
    "fix_login_lock_bug":     { ... },
    "add_bio_length_limit":   { ... },
    "add_password_change":    { ... }
  },
  "totals": {
    "det": {"files_ok": "3/5", "anchor_ok": "3/4", "recall_at_3": "4/5"},
    "ai":  {"files_ok": "3/5", "anchor_ok": "3/4", "recall_at_3": "4/5"}
  }
}
```

### 5.3 업데이트 정책: **수동**
`vib bench --patch` 단독 실행은 baseline 을 **읽기만** 한다. 차이가 있으면 리포트에 표시하고
regression 이 있으면 exit 1.

개발자가 의도된 변경이라고 판단할 때만 `vib bench --patch --update-baseline` 으로 덮어쓴다.
자동 갱신은 회귀를 침묵시킬 수 있어 위험하다 (점수가 떨어져도 baseline 이 따라 내려가면 통과).

### 5.4 초기 값
C6 완료 시점 측정값을 커밋한다: det 3/5·3/4·4/5, ai 3/5·3/4·4/5.

## 6. CLI 모양

```
vib bench --patch                    # 측정 + baseline diff 리포트 + (regression → exit 1)
vib bench --patch --update-baseline  # baseline 덮어쓰기 (출력은 신값, 항상 exit 0)
vib bench --patch --json             # 머신 판독 (전체 결과 JSON, regression → 여전히 exit 1)
```

Exit code 규칙:
- regression 없음 → exit 0
- regression 1 개 이상 → exit 1 (JSON 출력 모드에서도 동일)
- `--update-baseline` → 항상 exit 0 (baseline 이 새 값이 되므로 regression 개념 없음)

`--patch` 없는 기존 `vib bench` (A/B anchor-effect) 는 변경 없음. 새 플래그는 mutually exclusive 로 취급.

## 7. 리포트 출력 (사람용)

```
Patch accuracy benchmark (pinned intents, 5 scenarios × 2 modes)
Baseline: tests/benchmark/patch_accuracy_baseline.json (2026-04-12)

                     deterministic       --ai
  files_ok           3/5  (=)            3/5  (=)
  anchor_ok          3/4  (=)            3/4  (=)
  prefilter_recall@3 4/5  (=)            4/5  (=)

Per-scenario:
  change_error_msg          det ✓ ✓ ✓   ai ✓ ✓ ✓
  add_email_domain_check    det ✗ — ✗   ai ✗ — ✗
  fix_login_lock_bug        det ✓ ✓ ✓   ai ✓ ✓ ✓
  add_bio_length_limit      det ✓ ✓ ✓   ai ✓ ✓ ✓
  add_password_change       det ✗ ✗ ✓   ai ✗ ✗ ✓

Regressions: none
Improvements: none
```

표기:
- `=` baseline 동일, `+N` 개선, `-N` 회귀
- 시나리오 행은 `files_ok / anchor_ok / recall@3` 순 (`—` = 해당 없음)

## 8. 파일별 변경 요약

| 파일 | 종류 | 목적 |
|---|---|---|
| `vibelign/commands/bench_fixtures.py` | 신규 | `PINNED_INTENTS` + `prepare_patch_sandbox` |
| `vibelign/core/patch_suggester.py` | 수정 | `score_candidates` 추출 (behavior-preserving) |
| `vibelign/commands/vib_bench_cmd.py` | 수정 | `--patch` 플래그 + `_run_patch_accuracy` 추가 |
| `tests/benchmark/patch_accuracy_baseline.json` | 신규 | 초기 baseline (C6 측정값) |
| `tests/test_patch_accuracy_scenarios.py` | 수정 | `_PINNED_INTENTS` / `_prepare_sandbox` → `bench_fixtures` 로 이동, re-export |
| `tests/test_patch_suggester_score_candidates.py` | 신규 | `score_candidates` behavior-preserving unit test |
| `tests/test_bench_patch_command.py` | 신규 | `vib bench --patch --json` subprocess E2E + regression 감지 |

## 9. 테스트 전략

### 9.1 Unit test: `score_candidates`
`tests/test_patch_suggester_score_candidates.py` (신규)
- 5 시나리오 각각에 대해 `score_candidates(sandbox, request)` 호출
- top-1 파일이 기존 `suggest_patch` 의 `target_file` 과 일치하는지 (behavior-preserving 증명)
- 반환 리스트가 score 내림차순인지
- 길이 > 0 확인

### 9.2 E2E: `vib bench --patch --json`
`tests/test_bench_patch_command.py` (신규)
- subprocess 로 실행, exit code 확인
- JSON 파싱해서 `scenarios` 와 `totals` 구조 검증
- baseline 과 동일한 상태에서 돌리면 exit 0, regressions=none
- 임시로 baseline 을 모두 true 로 조작한 뒤 돌리면 exit 1 (regression 감지 검증)

### 9.3 회귀 가드
기존 `tests/test_patch_accuracy_scenarios.py` 전체가 그대로 통과해야 한다.

## 10. 스코프 제외 (YAGNI 명시)

- **히스토리/트렌드:** baseline 은 단일 스냅샷. 과거 추이는 git history 로 본다.
- **다중 샌드박스:** 하나의 sample_project, 하나의 pinned intent 세트. 2 종류 이상 필요해지면 그때 확장.
- **Provider 스위칭:** `--ai` 는 현재 기본 provider (Gemini) 만 측정. Claude/GPT 비교는 별개 초점.
- **Flaky 탐지:** pinned intent 는 결정론적이다. 불안정성이 관찰되면 그 자체가 버그이고 별도로 조사한다.
- **CI 자동 차단:** 이번 스코프는 로컬 재현성 확보까지. CI 에 붙이는 것은 후속 과제.

## 11. 성공 기준

1. `vib bench --patch` 가 1 커맨드로 현재 숫자를 재현한다 (det 3/5·3/4·4/5, ai 3/5·3/4·4/5)
2. 아무 코드 변경 없이 두 번 연속 실행해도 동일한 결과가 나온다 (결정성 검증)
3. `patch_suggester.py` 에 회귀를 일으키는 변경을 넣으면 `vib bench --patch` 가 exit 1 로 알린다
4. 차기 ICE 후보 (C2/C4) 구현 시 기획 → 구현 → `vib bench --patch` 1 회 → 숫자 공유 의 flow 가 성립한다

## 12. 열린 질문

없음. C2/C4 시점에 다시 열릴 수 있는 항목:
- Baseline 파일의 stale 판정 기준 (지금은 수동 판단)
- Pinned intent drift 감지 (지금은 `pinned_intents_version` 문자열만 기록)
