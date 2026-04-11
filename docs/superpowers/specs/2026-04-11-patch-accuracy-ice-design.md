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

### 실행 방식
- **주체:** 사용자 본인
- **대상:** `tests/benchmark/sample_project/`
- **조건:** B (앵커 인덱스가 프롬프트에 포함된 상태) 단일 조건
- **횟수:** `scenarios.json` 의 5개 시나리오 각 1회
- **명령:** 각 시나리오의 `request` 텍스트를 그대로 `vib patch` 에 전달
- **기록 항목:** 시나리오 ID, AI가 선택한 파일 목록, AI가 선택한 앵커 이름, 제안된 변경 요약(선택 사항)

### 원시 결과 표

| 시나리오 ID | AI 선택 파일 | AI 선택 앵커 | Notes |
|---|---|---|---|
| change_error_msg     | _(to fill)_ | _(to fill)_ | |
| add_email_domain_check | _(to fill)_ | _(to fill)_ | |
| fix_login_lock_bug   | _(to fill)_ | _(to fill)_ | |
| add_bio_length_limit | _(to fill)_ | _(to fill)_ | |
| add_password_change  | _(to fill)_ | _(to fill)_ | |

> 이 표는 사용자가 5회 실행을 마친 뒤 함께 채운다. 이후 §3 Scoring 블록이 자동 생성된다.

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
| change_error_msg     | _(to fill)_ | _(to fill)_ | _(to fill)_ |
| add_email_domain_check | _(to fill)_ | _(to fill)_ | _(to fill)_ |
| fix_login_lock_bug   | _(to fill)_ | _(to fill)_ | _(to fill)_ |
| add_bio_length_limit | _(to fill)_ | _(to fill)_ | _(to fill)_ |
| add_password_change  | _(to fill)_ | N/A         | _(to fill)_ |

### 집계
- files 정확도: _X_ / 5
- anchor 정확도: _Y_ / 4  (add_password_change 제외)
- overall 정확도: _Z_ / 5

---

## 4. Failure Taxonomy

실패한 케이스에서 공통 원인을 추출하여 유형 ID를 부여한다.

| ID | 유형명 | 영향 시나리오 | 추정 원인 |
|---|---|---|---|
| F? | _(to fill)_ | _(to fill)_ | _(to fill)_ |

> **조기 종료 조건:** overall 정확도가 5/5 이면 "현 시점에서 A+C 범위는 개선 불필요"로 판정하고, §5~§8을 비운 상태로 "범위를 B(코드 생성) 또는 D(apply)로 전환 권고"를 §9에 기록한 뒤 writing-plans 호출 없이 세션을 종료한다.

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

각 실패 유형마다 1~3개의 해결 후보를 도출하고 점수를 매긴다.

| ID | 후보 | 대상 유형 | I | C | E | 점수 | 근거 | 구현 힌트 |
|---|---|---|---|---|---|---|---|---|
| C? | _(to fill)_ | F? | _ | _ | _ | _ | _(to fill)_ | _(to fill)_ |

- **점수 열**은 `(I × C) / (6 − E)` 계산값
- **구현 힌트 열**은 writing-plans 단계에서 바로 소비됨 — 대상 파일/함수 추정, 기존 테스트 재사용 여부, 예상 리스크 등 1~2줄

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
_(to fill — 점수 매김 후 기록)_

---

## 8. Backlog

선정되지 않은 후보는 아래에 보존한다. 다음 라운드(또는 측정 데이터가 바뀌었을 때) 재평가 대상.

| ID | 후보 | 대상 유형 | 점수 | 보관 이유 |
|---|---|---|---|---|
| _ | _(to fill)_ | _ | _ | _ |

> **고정 포함 후보:** "자동 벤치마크 러너 구축" — 이번 세션에서는 구현하지 않지만, §1에서 명시적으로 backlog 행으로 남긴다. 다음 ICE 라운드부터는 수동 5회가 아니라 자동 실행으로 전환할지 여기서 평가한다.

---

## 9. Next Step

- **정상 경로:** 선정된 후보 1~2개에 대해 writing-plans 스킬을 호출하여 구현 plan을 작성한다. plan 경로는 `docs/superpowers/plans/2026-04-11-patch-accuracy-<후보 ID>.md` 형식.
- **데이터 반증 경로:** overall 정확도 5/5 → writing-plans 호출 없음, "범위 전환 권고"로 마감.
