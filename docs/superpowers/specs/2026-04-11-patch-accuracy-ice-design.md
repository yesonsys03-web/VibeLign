# Patch Codespeak Accuracy — ICE Session (2026-04-11)

VibeLign `vib patch` 파이프라인의 **앵커 배치 정확도**와 **의도/스코프 해석 정확도**를 데이터 근거로 개선하기 위한 1회성 ICE 세션 기록. 이 문서는 측정 → 분류 → 후보 도출 → 점수 → 선정 전 과정을 남기고, 선정된 후보를 writing-plans 단계로 넘기는 인수인계서 역할을 한다.

---

## 1. Goal & Scope

### 목표
사용자 요청을 받았을 때 `vib patch`가
- 올바른 **파일**을 고르는가 (의도/스코프 = "C")
- 올바른 **앵커**를 고르는가 (앵커 배치 = "A")

두 가지 정확도 축만 측정·개선한다.

### 범위 제외
- **B. 코드 생성 정확도** (앵커 안에서 생성되는 코드의 문법/의도 정확도)
- **D. apply 성공률** (계획은 옳았으나 실제 파일 적용이 실패)
- **자동 벤치마크 러너 구축** — §8 Backlog에 고정 보존하되 이 세션에서 구현하지 않는다

### 성공 기준 (세 가지 모두 충족)
1. `tests/benchmark/sample_project/` 에 대해 5개 시나리오(조건 B, 앵커 인덱스 제공)의 수동 실행 결과가 표로 정리되어 있다.
2. 실패/부정확 케이스가 **근본 원인별 유형**으로 분류되어 있다 (최소 2개 이상의 유형; 단 실패 0건이면 §4에서 조기 종료).
3. 유형별 개선 후보가 ICE 점수와 함께 ranked list로 제시되고, 상위 1~2개가 "다음 plan" 대상으로 선정되어 있다.

---

## 2. Measurement

### 실행 방식 (실측)
- **주체:** Claude Code 세션이 이 자리에서 직접 실행 (사용자가 수동으로 돌리지 않음 — `vib bench` 시스템을 발견한 뒤 경로 β 로 재정렬, 2026-04-11)
- **샌드박스:** `/tmp/vibelign-ice-sandbox` — `tests/benchmark/sample_project/` 를 복사한 뒤 `vib start` → `vib anchor --auto` 로 24개 앵커 + intent 자동 생성
- **조건:** `vib patch --json "<request>"` 단일 조건 (앵커/코드맵 모두 구축된 상태)
- **AI 플래그:** `--ai` **미사용**. 기본 휴리스틱 경로(키워드 매칭 + AI 생성 intent 매칭)만 측정. `--ai` 경로는 §6에서 ICE 후보로 별도 평가.
- **파싱:** JSON 출력의 `data.patch_plan.target_file` / `target_anchor` / `steps[]` 필드 추출

### 원시 결과 표

| 시나리오 ID | AI 선택 파일 | AI 선택 앵커 | confidence | 비고 |
|---|---|---|---|---|
| change_error_msg       | `pages/login.py`     | `LOGIN_RENDER_LOGIN_ERROR`     | low    | intent 매칭이 "로그인/실패/시" 키워드를 render_login_error 로 끌고 감 |
| add_email_domain_check | `core/validators.py` | `VALIDATORS_VALIDATE_EMAIL_DOMAIN` | medium | 호출자(signup) 대신 유틸리티 정의부로 직행 |
| fix_login_lock_bug     | `api/auth.py`        | `AUTH_LOGIN_USER`              | low    | 정답과 일치 |
| add_bio_length_limit   | `api/users.py`       | `USERS_GET_USER_PROFILE`       | low    | UI(profile.py) 대신 서비스 get 앵커로, 동사(update)도 반영 안 됨 |
| add_password_change    | `core/validators.py` | `VALIDATORS_VALIDATE_PASSWORD` | medium | 다중 파일 요청이 단일 유틸로 붕괴, `steps[]` 는 1개 |

---

## 3. Scoring

`tests/benchmark/scenarios.json` 의 `correct_files` / `forbidden_files` / `correct_anchor` 를 기준으로 판정한다.

### 판정 규칙
- **files_ok** — `correct_files` 가 모두 포함되고, `forbidden_files` 중 어느 것도 포함되지 않으면 ✅
- **anchor_ok** — `correct_anchor` 와 일치하면 ✅. 시나리오의 `correct_anchor` 가 `null` 이면(`add_password_change`) 이 열은 "N/A" 로 기록하고 스코어에서 제외
- **overall** — files_ok 와 anchor_ok 둘 다 ✅(또는 N/A)이면 ✅

### 채점 표

| 시나리오 ID | files_ok | anchor_ok | overall |
|---|---|---|---|
| change_error_msg       | ✅ | ❌ (기대 `LOGIN_HANDLE_LOGIN`) | ❌ |
| add_email_domain_check | ❌ (기대 `pages/signup.py`) | ❌ (기대 `SIGNUP_HANDLE_SIGNUP`) | ❌ |
| fix_login_lock_bug     | ✅ | ✅ | ✅ |
| add_bio_length_limit   | ❌ (기대 `pages/profile.py`) | ❌ (기대 `PROFILE_HANDLE_PROFILE_UPDATE`) | ❌ |
| add_password_change    | ❌ (기대 `api/auth.py` + `pages/profile.py` 다중 파일) | N/A (`correct_anchor = null`) | ❌ |

### 집계
- files 정확도: **1 / 5** (20%)
- anchor 정확도: **1 / 4** (25%) — add_password_change 는 N/A 로 제외
- overall 정확도: **1 / 5** (20%)

---

## 4. Failure Taxonomy

4개의 실패 케이스에서 4종의 근본 원인을 추출했다.

### F1 — 같은 파일 내 "잘못된 형제 앵커" 선택 (키워드 교집합 편향)

- **영향 시나리오:** `change_error_msg` (1건)
- **추정 원인:** `vibelign/core/patch_suggester.py::_score_anchor_names` 와 intent 매칭 루프가 **요청 토큰과 앵커 토큰의 집합 교집합 개수 × 3** 으로만 점수를 계산한다. 요청의 **동사**(바꿔줘 = update)는 점수에 전혀 반영되지 않아, 같은 파일에서 키워드가 많이 겹치는 **display-only 앵커**(`LOGIN_RENDER_LOGIN_ERROR`, intent: "로그인 실패 시 오류 메시지를 보여줍니다")가 **실제 변경이 필요한 핸들러 앵커**(`LOGIN_HANDLE_LOGIN`, 응답 딕셔너리의 literal을 반환) 보다 더 높은 점수를 받는다.
- **코드 근거:** `patch_suggester.py:277-312` — 점수 = `match_count * 3`, verb 가중치 없음.

### F2 — 레이어 오배치: 호출자(caller) 대신 유틸리티(utility) 정의부로 직행

- **영향 시나리오:** `add_email_domain_check`, `add_password_change` (2건)
- **추정 원인:** 요청에 "이메일 도메인 검사", "비밀번호 변경" 같은 명사가 들어가면 매처가 **해당 이름의 유틸리티 함수 앵커** (`VALIDATORS_VALIDATE_EMAIL_DOMAIN`, `VALIDATORS_VALIDATE_PASSWORD`) 에 최고점을 주고, 실제로 수정해야 하는 **호출자 측**(`SIGNUP_HANDLE_SIGNUP`, `AUTH_*` / `PROFILE_*`) 은 놓친다. "use existing utility from caller" 와 "modify utility" 를 구분하는 로직이 없다.
- **코드 근거:** `patch_suggester.py` 에 `project_map.ui_modules` 는 AI 후보 확장에만 쓰이고, 레이어 기반 라우팅 규칙은 없음.

### F3 — 요청 동사 무시 (GET vs UPDATE, RENDER vs HANDLE)

- **영향 시나리오:** `add_bio_length_limit` (1건)
- **추정 원인:** F1 과 같은 뿌리. 요청에 "수정 시 제한"(update) 이 있음에도 매처는 `USERS_GET_USER_PROFILE` 같은 read 계열 앵커를 선택했다. 앵커 이름에 이미 `GET_*`, `HANDLE_*`, `UPDATE_*`, `RENDER_*` 같은 verb 클러스터가 있음에도, 점수 계산에서 **요청 verb ↔ 앵커 verb 매칭** 자체가 없다.
- **F1 과의 관계:** 해결책은 공유 가능 (verb-aware scoring) — §6 에서 하나의 후보로 통합.

### F4 — 다중 파일 요청의 단일 타깃 붕괴

- **영향 시나리오:** `add_password_change` (1건, F2 와 중첩)
- **추정 원인:** "비밀번호 변경 기능 추가" 는 명백히 `api/auth.py` (서비스 로직) + `pages/profile.py` (UI) 두 파일 수정이 필요하지만, `vib patch --json` 출력의 `steps[]` 배열은 단일 엔트리, `sub_intents` 는 `null`. 의도 파서가 multi-intent 구조를 감지하지 못함. `--lazy-fanout` 플래그가 존재하지만 opt-in 이라 기본 경로에서는 활성화되지 않는다.

### 유형 빈도 요약

| 유형 ID | 영향 케이스 수 | 전체 실패 중 비중 |
|---|---|---|
| F1 | 1 | 25% |
| F2 | 2 | 50% |
| F3 | 1 | 25% |
| F4 | 1 | 25% |

(F2+F4 중첩 1건 — `add_password_change`)

> **조기 종료 조건:** overall 정확도가 5/5 이면 "현 시점에서 A+C 범위는 개선 불필요"로 판정하고 세션을 종료한다. 현 측정 결과는 1/5 (20%) 이므로 조기 종료 조건 미해당, 정상 경로로 진행.

---

## 5. ICE Rubric

### 스케일: 1~5 정수

### Impact — "이 후보를 적용하면 벤치마크 실패가 얼마나 줄어들 것인가"
- **5** — 측정된 실패 케이스의 과반(≥50%)을 직접 해소
- **4** — 한 유형 전체 또는 여러 유형의 일부 해소
- **3** — 한 유형의 일부 케이스만 해소
- **2** — 간접적 개선 (관측성/로깅 등)
- **1** — 벤치마크 수치에는 거의 영향 없음

### Confidence — "그 Impact가 실제로 발생할 것이라는 확신"
- **5** — 근본 원인을 코드에서 직접 확인함, 재현 방식도 이해 완료
- **4** — 실패 로그·산출물을 보고 원인이 강하게 추정됨
- **3** — 그럴듯한 가설, 검증은 후보 실행 후에나 가능
- **2** — 추측에 가깝고 반증 가능성 상당
- **1** — 그냥 찍는 수준

### Effort — "구현·검증에 드는 총 시간 (반비례)"
- **5** — 30분 이내 (예: 프롬프트 몇 줄 수정)
- **4** — 1~2시간 (단일 함수 수정 + 기존 테스트 보강)
- **3** — 반나절 (여러 파일 수정 또는 새 소형 모듈)
- **2** — 1~2일 (구조 변경 포함)
- **1** — 3일 이상 또는 불확실성 큼

### 공식
```
ICE = (Impact × Confidence) / (6 − Effort)
```
- Effort가 5(쉬움)면 분모 1 → 쉬운 후보 상위
- Effort가 1(어려움)이면 분모 5 → 페널티
- 일반 공식의 "Effort=1이 쉬움이냐 어려움이냐" 모호성을 회피

### 타이브레이커
점수 동점이면 (1) Confidence 높은 쪽 → (2) Effort 점수 높은 쪽(=더 쉬운 쪽) 우선.

> 이 §5 블록은 향후 다른 주제의 ICE 세션에서도 그대로 복사해 쓸 수 있도록 self-contained 하게 작성됨.

---

## 6. Candidates & ICE Table

실패 유형 F1~F4 에 대응하는 5개 후보. 점수는 `(I × C) / (6 − E)`.

| ID  | 후보 | 대상 유형 | I | C | E | 점수 | 근거 | 구현 힌트 |
|---|---|---|---|---|---|---|---|---|
| C1  | **Verb-aware 앵커 스코어링** — `_score_anchor_names` 와 intent 매칭에 요청-동사 ↔ 앵커-동사 클러스터 매칭을 추가. 클러스터: MUTATE(바꿔/수정/변경), CREATE(추가/만들/생성), DELETE(삭제/제거), READ(조회/보기/표시). 앵커 이름 접두어(HANDLE/UPDATE/SET/CREATE/ADD/GET/READ/RENDER) 와 intent 본문 동사를 같은 클러스터로 분류. 매칭시 +5, 불일치시 −2. 기존 키워드 교집합 점수는 base 로 유지. | F1, F3 | 5 | 5 | 3 | **8.33** | F1/F3 모두 동일 뿌리(동사 무시). 근본 원인 코드(`patch_suggester.py:277-312`, `731-742`)에서 직접 확인. 실패 2건/4건(50%) 직접 해소 가능. | `vibelign/core/patch_suggester.py` 수정 대상. 기존 테스트: `tests/test_patch_anchor_priority.py` 에 회귀 추가. 리스크: verb 클러스터 누락 → 기본 점수 동작으로 자연 fallback. |
| C2  | **레이어-라우팅 규칙** — 요청에 등장한 명사가 utility 함수 이름과 일치해도, 해당 utility 가 이미 다른 파일에서 import/호출되고 있으면 caller 측 앵커를 우선. `project_map` 의 `ui_modules`/`service_modules` 계층 정보를 anchor scoring 단계에 주입. | F2 | 5 | 3 | 2 | **3.75** | F2 2건 전부 해소 가능성. 단 caller-detection 로직(import 그래프 스캔)을 새로 붙여야 해서 설계 리스크 존재. | `project_map` 에 caller 인덱스 추가 or 기존 `connects` 필드 활용. 큰 구조 변경 가능성. |
| C3  | **`--ai` 기본 활성화 + 효과 측정** — 플래그 기본값 반전 후 같은 5 시나리오 재실행. 개선 폭이 의미 있으면 릴리스. | F1, F2, F3 (간접) | 3 | 2 | 3 | **2.00** | 현재 `quiet_ai` 경로가 json 모드에서 이미 일부 AI를 쓰고 있어 순수 효과가 불확실. 측정 없이 Confidence를 올릴 수 없음. API 비용/latency 트레이드오프. | 2줄 변경 + 벤치 재실행. 단 AI 경로가 anchor selection 직접 개입 여부 확인 필요. |
| C4  | **다중 의도 기본 fanout** — `--lazy-fanout` 기본을 `False → True` 로 반전, 또는 `intent_ir.operation == "create"` 이고 request 길이 > N 일 때 자동 fanout. | F4 | 3 | 3 | 3 | **3.00** | F4 1건 해소. 단 현재 `sub_intents`/`steps` 가 비어있는 건 fanout 플래그와 별개로 intent 파서가 multi-intent 를 인식 못 하는 게 원인일 수 있음 → 추가 조사 필요. | `vibelign/core/codespeak.py` + intent parser 조사. 부작용(의도 과분할) 가드 필요. |
| C5  | **`vib patch` 전용 벤치마크 러너 자동화** — 오늘 수동 실행한 스크립트를 `vib bench --patch` 서브모드로 이식. 입력: `scenarios.json`. 출력: files/anchor 채점 표 + 회귀 대비 baseline 저장. | (측정 인프라) | 2 | 5 | 3 | **3.33** | 오늘 직접 돌려봤기 때문에 실행 가능성 Confidence 최고. 하지만 직접적 정확도 개선은 없음 — 후속 개선의 **회귀 가드레일**. | `vibelign/commands/vib_bench_cmd.py` 에 `--patch` 모드 추가. `_run_score` 재사용. |

### 정렬된 점수
1. **C1 — 8.33**
2. C2 — 3.75
3. C5 — 3.33
4. C4 — 3.00
5. C3 — 2.00

C2 가 2위지만 §7 sanity check 에서 Confidence 3 의 설계 불확실성 때문에 이번 라운드에서는 후보에서 제외되고, 대신 C5(측정 인프라) 를 C1 후속 plan 으로 배치한다.

---

## 7. Selection

### 선정 규칙
1. ICE 점수 내림차순 정렬
2. 상위 **1개**를 이번 라운드 구현 대상으로 확정
3. 2위 후보의 점수가 1위의 **80% 이상**이면 2개 모두 선정 (병렬 가능 여부는 writing-plans에서 판단)
4. 그 외 후보는 §8 Backlog로

### Sanity Check (3가지, 하나라도 걸리면 재검토)
- **근거 확인:** 선정된 후보가 §4의 어떤 실패 유형을 직접 해소하는지 1문장으로 말할 수 있는가?
- **Effort 현실성:** 선정 후보의 Effort가 4~5면 정말 그 시간 안에 끝나는지 낙관 편향을 한 번 더 경계
- **측정 연결:** 구현 후 같은 5개 시나리오를 재실행하여 개선을 재현 가능하게 확인할 수 있는가?

### 선정 결과

**선정: C1 단독** (Verb-aware 앵커 스코어링)

### 선정 이유

- **격차:** C1(8.33) 와 2위 C2(3.75) 의 비율은 45% → 80% 임계 미달 → 단독 선정.
- **근거 확인:** C1 은 F1(change_error_msg) 과 F3(add_bio_length_limit) 두 실패 케이스를 동일한 코드 변경으로 해소한다 — "요청 verb 가 anchor scoring 에서 무시되는 것"이라는 단일 근본 원인.
- **Effort 현실성 (낙관 편향 점검):** E=3(반나절) 추정은 `_score_anchor_names` 한 함수의 수정 + verb 클러스터 상수 정의 + 기존 테스트에 회귀 2건 추가 범위. 낙관 없음, 오히려 verb 클러스터 목록이 다국어라 소폭 overshoot 가능성 있음(최대 1일).
- **측정 연결:** 구현 후 동일 5 시나리오를 재실행하여 `change_error_msg` 의 앵커가 `LOGIN_HANDLE_LOGIN` 로, `add_bio_length_limit` 의 파일/앵커가 `pages/profile.py::PROFILE_HANDLE_PROFILE_UPDATE` 로 바뀌면 성공. 재현 방식은 오늘 사용한 one-shot Bash 루프를 그대로 쓰면 됨.

### 선정에서 제외된 이유

- **C2 (layer routing)**: Impact 는 최고지만 설계 불확실성이 Confidence 3 로 드러났고, caller-detection 인프라를 새로 붙여야 해서 이번 라운드로는 overshoot 위험. C1 구현 후 재측정 결과에서 F2 가 여전히 남으면 다음 라운드 1순위 후보.
- **C5 (벤치마크 러너)**: 측정 인프라는 **C1 구현 완료 직후** 에 착수하는 것이 옳음 — C1 효과 검증에 바로 쓰이고, 이후 모든 회귀 가드레일이 됨. §9 에서 "C1 구현 plan 뒤에 이어지는 2차 plan 후보"로 명시.
- **C3 (--ai 기본)**: Confidence 2 는 "의사결정을 내릴 만큼 모르는 상태". 측정(half day) 후 재평가하는 게 맞고, 이건 C5 의 러너가 있으면 훨씬 싸짐.
- **C4 (multi-fanout)**: F4 1건만 해소. C1 이 반영된 뒤에도 `add_password_change` 가 여전히 틀리면 재조사.

---

## 8. Backlog

선정되지 않은 후보는 아래에 보존한다. 다음 라운드 또는 C1 구현 후 재측정 결과에 따라 재평가.

| ID | 후보 | 대상 유형 | 점수 | 보관 이유 |
|---|---|---|---|---|
| C5 | `vib patch` 벤치마크 러너 자동화 (`vib bench --patch`) | 측정 인프라 | 3.33 | C1 구현 직후 2차 plan 후보. 회귀 가드레일 역할. |
| C2 | 레이어-라우팅 규칙 (caller vs utility) | F2 | 3.75 | C1 적용 후에도 F2(`add_email_domain_check`, `add_password_change`) 가 남아있을 가능성 높음. 다음 ICE 라운드 1순위. |
| C4 | 다중 의도 기본 fanout | F4 | 3.00 | F4 는 단일 케이스라 우선순위 낮음. C2 와 함께 조사 예정. |
| C3 | `--ai` 기본 활성화 | F1/F2/F3 간접 | 2.00 | C5 가 먼저 생기면 측정 비용이 크게 줄어 재평가 가치 상승. |

---

## 9. Next Step

- **즉시 다음 작업:** writing-plans 스킬을 호출하여 **C1 (Verb-aware 앵커 스코어링)** 구현 plan 을 작성한다. plan 경로: `docs/superpowers/plans/2026-04-11-patch-accuracy-c1-verb-aware-scoring.md`.
- **C1 plan 완료 후 이어지는 작업:** C5 (벤치마크 러너 자동화) plan 을 별도로 작성하여 C1 의 회귀 가드레일로 배치. C5 가 생기면 C3 재평가 비용이 급감하므로, 그 시점에서 C3 투자 여부 재판단.
- **C1 구현·검증 이후의 다음 ICE 라운드:** 재측정 결과에서 F2/F4 가 여전히 남아있으면 C2/C4 를 대상으로 새로운 ICE 세션 개시.
