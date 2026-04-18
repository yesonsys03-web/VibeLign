# Doctor 기능 개선 설계

## 목표

`vib doctor`를 단순 진단 출력에서 **문제 발견 → 복구 안내 → 안전한 자동 적용 판단**까지 이어지는 도구로 개선한다.

이번 범위의 핵심은 진단 종류를 무작정 늘리는 것이 아니라, 이미 존재하는 진단 결과를 더 구조화해서 CLI와 GUI가 그대로 활용할 수 있게 만드는 것이다.

---

## 현재 상태 요약

현재 구조는 이미 세 단계로 나뉘어 있다.

- `vibelign/core/doctor_v2.py` — 프로젝트 분석과 doctor envelope 생성
- `vibelign/commands/vib_doctor_cmd.py` — `--json`, `--plan`, `--patch`, `--apply`, `--fix` 흐름 제어
- `vibelign-gui/src/pages/Doctor.tsx` — report / plan / apply GUI 표시

하지만 현재는 다음 문제가 있다.

1. GUI가 severity를 엔진이 아니라 문자열로 추론한다.
2. 각 이슈에 대해 “왜 중요한지”는 일부 있지만, “정확히 어떻게 고치는지”는 구조화가 약하다.
3. `--apply`가 자동으로 무엇을 할 수 있고 무엇은 못 하는지 사용자가 명확히 알기 어렵다.
4. CLI와 GUI가 같은 분석 결과를 공유하지만, 복구 액션 계약은 아직 약하다.
5. GUI status badge가 `Healthy`를 기준으로 색상을 고르지만, 백엔드 status는 `Safe / Good / Caution / Risky / High Risk`를 사용한다.

---

## 설계 원칙

1. **엔진이 진실의 원천이다.**  
   CLI와 GUI는 진단 결과를 해석하지 말고, 엔진이 내려준 구조를 그대로 표시한다.

2. **복구 가능성은 이슈 단위로 표현한다.**  
   각 이슈마다 자동 수정 가능 여부와 권장 명령을 가진다.

3. **기존 doctor 흐름은 유지한다.**  
   `vib doctor`, `vib doctor --json`, `vib doctor --plan`, `vib doctor --apply`의 큰 틀은 바꾸지 않는다.

4. **Phase 1은 복구 안내 강화다.**  
   자동 수정 범위 확대는 후속 단계로 두고, 이번 단계는 “안전한 액션 계약”을 먼저 만든다.

---

## 대상 파일

### 수정 대상

- `vibelign/core/doctor_v2.py`
- `vibelign/commands/vib_doctor_cmd.py`
- `vibelign-gui/src/pages/Doctor.tsx`
- `tests/test_vib_doctor_v2.py`

### 필요 시 추가 테스트 대상

- `tests/test_plain_doctor_guard_render.py`
- doctor CLI/GUI 계약 검증용 신규 테스트 파일

---

## 데이터 모델 변경

현재 `DoctorV2Report.issues`는 `list[dict[str, object]]` 구조를 쓰고 있다. 이 구조는 유지하되, 이슈 항목에 다음 필드를 표준으로 추가한다.

```python
{
    "found": str,
    "why_it_matters": str,
    "next_step": str,
    "path": str | None,
    "severity": "high" | "medium" | "low",
    "category": str,
    "recommended_command": str | None,
    "can_auto_fix": bool,
    "auto_fix_label": str | None,
}
```

### 필드 의미

- `severity`  
  GUI가 문자열 추론 없이 바로 색상/강조를 결정할 수 있게 한다.

- `category`  
  구조, anchor, MCP, prepared-tool, project-map 같은 진단 분류를 제공한다.

- `recommended_command`  
  사용자가 바로 실행할 수 있는 복구 명령을 제공한다. 예: `vib start --tools cursor`, `vib anchor --suggest`

- `can_auto_fix`  
  현재 `--apply` 또는 `--fix` 흐름으로 자동 복구 가능한지 나타낸다.

- `auto_fix_label`  
  GUI 버튼 문구나 CLI 설명에 재사용할 짧은 라벨이다. 예: `앵커 자동 추가`

---

## 진단 분류 규칙

이번 단계에서 최소한 다음 category를 표준화한다.

- `anchor`
- `project_map`
- `mcp`
- `prepared_tool`
- `structure`
- `metadata`

이 category는 점수 계산용이 아니라 **표시/행동 그룹화용**이다. 나중에 category별 필터나 묶음 실행으로 확장할 수 있다.

### 카테고리 분류 전략

카테고리는 **이슈를 생성하는 appender가 직접 지정**한다. 중앙 분류기(문자열 파싱)를 쓰지 않는다.

- `_append_mcp_issues()` → `category: "mcp"`
- `_append_prepared_tool_issues()` → `category: "prepared_tool"`
- `_issue_details()`의 legacy `risk_analyzer` 이슈 → 이슈 원본의 `check_type` 필드로 결정:
  - 파일 길이/함수 수/코드 혼합 → `"structure"`
  - 앵커 누락 → `"anchor"`
  - project_map 관련 → `"project_map"`
  - 그 외 → `"metadata"`

이를 위해 `risk_analyzer.py`의 이슈도 `list[str]` 대신 `list[dict]`로 변경하여, 생성 시점에 `category`를 포함시킨다.

### severity 분류 규칙

| severity | 해당 이슈 |
|----------|----------|
| `high` | MCP 설정 누락, project_map 무효/부재, 1000줄 이상 파일, 순환 참조 |
| `medium` | 앵커 누락, prepared-tool 파일 부분 누락, 500~999줄 파일, 함수 과다, 코드 혼합 |
| `low` | 200줄 이상 진입 파일, metadata 경고, catch-all 파일명 |

appender가 이슈를 생성할 때 severity도 함께 지정한다.

---

## 내부 데이터 흐름 변경

### 현재 (변경 전)

`risk_analyzer.py`가 `issues: list[str]`, `suggestions: list[str]` 두 개의 평문 리스트를 반환하고, `doctor_v2.py`의 `_issue_details()`가 이를 zip하여 dict로 변환한다. MCP/prepared-tool 이슈도 별도의 문자열 리스트로 append된다.

### 변경 후

각 appender가 직접 구조화된 dict를 생성한다:

```
risk_analyzer.analyze_project()
  → issues: list[dict]  (category, severity, found, next_step 등 포함)

_append_mcp_issues()
  → list[dict]

_append_prepared_tool_issues()
  → list[dict]
```

`_issue_details()`는 이 dict 리스트를 받아 `recommended_command`, `can_auto_fix`, `auto_fix_label` 등 복구 관련 필드를 보강하는 역할로 축소한다.

### `next_step`과 `recommended_command`의 경계

- `recommended_command`: 실행 가능한 bare 명령어. 예: `vib start --tools cursor`
- `next_step`: 사람이 읽는 설명 문장. 명령어를 포함하지 않는다. 예: `Cursor MCP 설정을 등록해야 AI 자동화 흐름이 연결돼요`

기존 `next_step`에 백틱으로 감싼 명령어가 포함된 경우, 마이그레이션 시 `recommended_command`로 분리한다.

---

## 캐시 스키마 마이그레이션

`vibelign/core/analysis_cache.py`의 `ANALYSIS_CACHE_SCHEMA`를 **1 → 2**로 올린다.

이슈 dict 구조가 변경되므로, 구버전 캐시는 자동으로 무효화되어야 한다. 기존 캐시 로드 시 스키마 버전이 2 미만이면 캐시를 무시하고 재분석한다. 사용자 조치는 필요 없다.

---

## CLI 설계

### 기본 출력

기존 markdown 출력 형식을 유지하되, 각 이슈에 다음 정보가 더 잘 드러나야 한다.

- severity
- path
- next_step
- recommended_command
- 자동 수정 가능 여부

예시:

```text
1. [HIGH][mcp] .cursor/mcp.json에 vibelign MCP 등록이 없어요
   왜 중요해요: AI 툴에서 VibeLign MCP를 못 써서 자동화 흐름이 끊겨요.
   다음 단계: Cursor MCP 설정을 등록해야 AI 자동화 흐름이 다시 연결돼요.
   추천 명령: vib start --tools cursor
   자동 수정: 불가
```

또는:

```text
2. [MEDIUM][anchor] 앵커가 없는 파일이 3개 있어요
   왜 중요해요: AI가 수정 범위를 잘못 잡을 가능성이 커져요.
   다음 단계: 앵커를 자동으로 추가한 뒤 다시 doctor를 실행해 결과를 확인해요.
   추천 명령: vib doctor --fix
   자동 수정: 가능 (앵커 자동 추가)
```

### `--json`

JSON envelope는 기존 포맷을 유지하되, 각 issue에 위 새 필드를 포함한다.

### `--plan`

현재 plan 출력은 “무엇을 할지”는 알려주지만, 이슈와의 연결이 약하다. 이번 단계에서는 각 action이 어떤 category 또는 어떤 문제군을 다루는지 더 잘 드러내도록 텍스트를 보강한다.

### `--apply`

이번 단계에서는 `--apply`의 실제 자동 복구 범위를 크게 넓히지 않는다. 대신:

1. 자동 적용 가능한 항목 수
2. 수동 조치가 필요한 항목 수
3. 체크포인트 생성 여부
4. 복구 후 재검사 안내

를 더 명확히 출력한다.

---

## GUI 설계

`vibelign-gui/src/pages/Doctor.tsx`는 현재 `inferSeverity()`로 severity를 문자열에서 추론한다. 이 로직은 제거 대상이다.

### 변경 방향

1. 엔진이 내려준 `issue.severity`를 그대로 사용한다.
2. 각 issue 카드에 다음 표시를 추가한다.
   - category badge
   - recommended command
   - auto-fix 여부
3. apply 가능 항목이 있는 경우, 전체 apply 메시지와 개별 issue의 자동 수정 가능 상태가 어긋나지 않도록 한다.
4. status badge도 백엔드의 `Safe / Good / Caution / Risky / High Risk` 계약을 직접 사용한다.

### GUI에서 보여줄 정보

각 이슈 카드:

- 제목: `issue.found`
- 경로: `issue.path`
- 설명: `issue.why_it_matters`
- 다음 단계: `issue.next_step`
- 추천 명령: `issue.recommended_command`
- 자동 수정 가능 여부: `issue.can_auto_fix`

### GUI에서 하지 않을 일

- 문자열 기반 severity 추론
- issue 문구 파싱으로 버튼 종류를 결정하는 로직

즉, GUI는 표시 계층만 담당한다.

---

## 자동 수정 범위 정의

이번 단계에서 `can_auto_fix=True`가 가능한 경우는 **현재 doctor가 이미 안전하게 다룰 수 있는 항목만** 포함한다.

대표 예:

- 앵커 누락 → `vib doctor --fix`

반대로 다음은 여전히 수동 또는 별도 명령 대상이다.

- MCP 설정 등록 누락 → `vib start --tools ...`
- prepared tool 파일 누락 → `vib start --tools ...`
- invalid JSON 설정 → 관련 설정 재생성 유도

이렇게 해서 “자동 수정 가능”이라는 문구가 과장되지 않도록 한다.

---

## 테스트 설계

### 기존 테스트 확장

`tests/test_vib_doctor_v2.py`에서 다음을 검증한다.

1. issue 항목에 `severity`, `category`, `recommended_command`, `can_auto_fix`가 포함되는지
2. Cursor MCP 누락 시 `category == "mcp"` 인지
3. OpenCode 준비 파일 일부 누락 시 `category == "prepared_tool"` 인지
4. 앵커 관련 이슈가 자동 수정 가능 상태로 내려오는지
5. markdown 렌더러가 새 필드를 반영하는지

### 추가 테스트 포인트

- doctor text output이 새 구조를 반영하는지 검증하는 신규 테스트 파일 생성
- GUI 계약 테스트가 가능하다면 Doctor page가 `issue.severity`를 직접 사용하고 문자열 추론에 의존하지 않는지 검증
- GUI status badge가 `Healthy` 같은 별도 문자열이 아니라 백엔드 status 계약을 그대로 해석하는지 검증
- 캐시 스키마 버전 1 → 2 전환 시 구버전 캐시가 무효화되는지 검증

---

## 후속 연결점: action_planner

`vibelign/action_engine/action_planner.py`의 `_classify_issue()`는 현재 문자열 파싱으로 `action_type`을 결정한다. 이슈에 `category` 필드가 추가되면, 이를 우선 참조하도록 바꾸는 것이 자연스럽다.

다만 이 변경은 **doctor contract 정비가 안정화된 뒤의 Phase 1B 또는 후속 작업**으로 둔다. 이번 Phase 1의 필수 범위에는 넣지 않는다.

```python
# 변경 전
def _classify_issue(issue):
    text = issue.get("found", "")
    if "앵커" in text: return "add_anchor"
    ...
    return "review"

# 변경 후
def _classify_issue(issue):
    category = issue.get("category")
    if category == "anchor": return "add_anchor"
    if category == "mcp": return "fix_mcp"
    if category == "project_map": return "fix_project_map"
    if category == "structure": return "split_file"
    # fallback: 기존 문자열 파싱 (category 없는 레거시 이슈용)
    text = issue.get("found", "")
    ...
    return "review"
```

이렇게 하면 문자열 파싱 의존이 점진적으로 제거된다. 하지만 planner 연동은 doctor 자체 계약이 먼저 고정된 뒤 별도 작업으로 진행하는 편이 안전하다.

---

## 제외 범위

이번 설계에는 포함하지 않는다.

- 완전히 새로운 대규모 진단 카테고리 추가
- 고위험 자동 리팩토링 적용 확대
- 점수 체계 전면 개편
- action engine 구조 재설계

이 단계는 **doctor를 더 똑똑하게 고치는 것보다, 더 신뢰할 수 있는 복구 안내 도구로 만드는 것**에 집중한다.

---

## 성공 기준

다음이 만족되면 이번 개선은 성공으로 본다.

1. CLI와 GUI 모두 severity를 문자열 추론 없이 구조화된 데이터로 사용한다.
2. 주요 doctor 이슈는 설명형 `next_step`를 가지고, 실행 가능한 경우 `recommended_command`를 함께 가진다.
3. 자동 수정 가능한 항목은 `can_auto_fix=True`로 일관되게 표시된다.
4. `--apply`와 실제 복구 가능 범위에 대한 사용자 기대가 더 정확해진다.
5. GUI status badge와 백엔드 status 계약이 일치한다.
6. 테스트가 새 진단 계약을 고정한다.

---

## 다음 단계

이 설계가 승인되면, 다음 구현 계획에서는 아래 순서로 작업한다.

1. `doctor_v2.py` 이슈 계약 확장
2. markdown / json 렌더링 정리
3. GUI Doctor page 구조 반영
4. 테스트 보강
5. 필요 시 소규모 auto-fix 연결 정리
6. 별도 후속 작업으로 planner category 연동 검토
