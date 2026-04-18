# VibeLign 구조 계획 시스템 기획안

> **상태:** 구현 완료 (문서 범위 반영)
> **목적:** AI가 새 기능 추가 또는 편집 전에 코드 배치 위치를 VibeLign으로부터 사전 확정받는 시스템

---

## 1. 문제 정의

### 현재 상황
```
사용자: "OAuth 인증 추가해줘"
AI:     auth.py 열기 → OAuth 코드 전부 거기 추가 → 파일 비대화
```

규칙(AGENTS.md)에 "구조화하라"고 명시되어 있어도 AI는:
- 기존 파일에 추가하는 것이 "안전"하다고 판단 (import 깨질 위험 없음)
- "구조화"의 기준이 모호 → 판단 회피
- 어디에 넣어야 하는지 알 방법이 없음

### 목표 상황
```
사용자: "OAuth 인증 추가해줘"
AI:     vib plan-structure "OAuth 인증 추가" 실행
        → 계획: oauth_provider.py 신규, auth.py ANCHOR:AUTH_HANDLER만 수정
AI:     계획대로 파일 분산 작성 → 구조 유지
```

### 왜 B 방식(사전 구조 계획)인가

**A 방식(줄 수 제한)**의 문제:
파일이 200줄 초과 → 커밋 차단 → AI가 임의의 함수를 새 파일로 빼서 줄 수만 맞춤
→ 구조는 여전히 엉망, 제한만 통과

**B 방식**은 "어디에 넣을지"를 사전에 확정하므로 구조가 근본적으로 유지됨.

---

## 2. 핵심 설계 원칙

- AI가 판단하는 것이 아니라 **VibeLign이 판단하고 AI는 실행**
- 모호한 규칙("구조화해라") 대신 **구체적 지시**("oauth_provider.py에 넣어라")
- 사용자는 처음 요청 하나만 — 나머지는 AI + VibeLign이 처리
- 계획은 파일로 저장 → 세션이 바뀌어도 AI가 참조 가능
- Phase 1에서는 현재 존재하는 메타데이터(`category`, `anchor_index`, `line_count`, 경로 토큰)만 사용하고, 사람 수준의 "책임 추론"은 과장하지 않음

---

## 3. 전체 워크플로

### 사용자 관점 (단순)
```
사용자: "OAuth 인증 추가해줘"  ← 이것만 하면 됨
    ↓
[VibeLign + AI가 자동 처리]
    ↓
사용자: 결과물 확인
```

### 내부 처리 흐름
```
사용자 요청
    ↓
AI: vib plan-structure "OAuth 인증 추가" 실행
    ↓
VibeLign 분석 (백엔드):
  ① 파일 크기 체크 → 기존 파일 한계 초과 여부
  ② project_map(코드맵) 카테고리/앵커/줄 수 조회 → 수정 후보 압축
  ③ 경로/폴더 패턴 매칭 → 도메인 키워드로 위치 확정
  ④ 앵커 가용성 체크 → 앵커 없으면 신규 파일 생성
    ↓
구조 계획 출력 + .vibelign/plans/<timestamp>.json 저장
    ↓
AI: 계획대로만 코딩
    ↓
watch --auto-fix: 앵커 자동 삽입     ← 앵커 집행 시스템 연동
vib guard: 계획 준수 여부 검증
```

> project_map(코드맵)은 watch 엔진이 파일 변경마다 `_refresh_project_map()`으로 갱신할 수 있다.
> 단, **watch가 실제 실행 중이고 `.vibelign/project_map.json`이 이미 존재할 때만** 최신성이 보장된다.

---

## 4. vib plan-structure 명령어 설계

### 입력
```bash
vib plan-structure "OAuth 인증 추가"
vib plan-structure --ai "OAuth 인증 추가"          # LLM 연동 (선택)
vib plan-structure --scope vibelign/core/ "watch 기능 확장"
```

### 출력 (터미널)
```
[VibeLign] 구조 계획 생성 중...

기능: OAuth 인증 추가
분석: vibelign/core/auth.py (현재 187줄, 앵커 3개) → 한계 초과, 분리 필요

📋 구조 계획
─────────────────────────────────────
수정 허용:
  vibelign/core/auth.py → ANCHOR: AUTH_HANDLER 구간만 (최대 20줄)

신규 생성:
  vibelign/core/oauth_provider.py    ← OAuth 공급자 로직
  vibelign/core/oauth_tokens.py      ← 토큰 관리 로직

금지:
  auth.py에 OAuth 구현 코드 직접 추가

계획 저장: .vibelign/plans/20260409T123456_oauth_auth.json
─────────────────────────────────────
이 계획대로 작업하세요. 완료 후 vib guard로 검증.
```

### 저장 형식 (.vibelign/plans/*.json)
```json
{
  "id": "20260409T123456_oauth_auth",
  "schema_version": 1,
  "feature": "OAuth 인증 추가",
  "created_at": "2026-04-09T12:34:56",
  "mode": "rules",
  "evidence": {
    "candidate_files": ["vibelign/core/auth.py"],
    "matched_categories": ["core"],
    "matched_keywords": ["auth", "oauth", "token"],
    "path_signals": ["core", "auth"],
    "requires_planning": true,
    "required_reasons": ["new_production_file", "multi_file_production_edit"]
  },
  "scope": {
    "changed_path_classes": ["production_path"],
    "new_file_paths": [
      "vibelign/core/oauth_provider.py",
      "vibelign/core/oauth_tokens.py"
    ],
    "existing_file_paths": ["vibelign/core/auth.py"]
  },
  "allowed_modifications": [
    {
      "path": "vibelign/core/auth.py",
      "anchor": "AUTH_HANDLER",
      "reason": "OAuth 진입점 연결만",
      "max_lines_added": 20,
      "allowed_change_types": ["edit", "import_wiring"]
    }
  ],
  "required_new_files": [
    {
      "path": "vibelign/core/oauth_provider.py",
      "responsibility": "OAuth 공급자 로직"
    },
    {
      "path": "vibelign/core/oauth_tokens.py",
      "responsibility": "토큰 관리 로직"
    }
  ],
  "forbidden": [
    {
      "type": "path_edit",
      "path": "vibelign/core/auth.py",
      "reason": "OAuth 구현 코드를 auth.py 본문에 직접 추가하면 파일 비대화 위험"
    }
  ],
  "messages": {
    "summary": "OAuth 기능은 신규 모듈 2개로 분리하고 auth.py는 진입점 wiring만 허용",
    "developer_hint": "guard는 allowed_modifications / required_new_files / forbidden 기준으로 실제 변경을 비교한다."
  }
}
```

#### plan JSON schema 상세 규칙 (Phase 1)

- `id`: plan 식별자. `.vibelign/plans/<id>.json` 파일명과 동일해야 함
- `schema_version`: 현재는 `1` 고정
- `mode`: `rules` 또는 `ai` (`--ai` 경로 확장 대비)
- `evidence.required_reasons[]`: guard가 `planning_required`를 설명할 때 그대로 재사용 가능한 이유 코드
- `scope.changed_path_classes[]`: `production_path`, `support_path` 등 path class 기록
- `allowed_modifications[]`:
  - `path` 필수
  - `anchor`는 anchor 기반 수정일 때 필수
  - `max_lines_added`는 선택
  - `allowed_change_types[]`는 `edit`, `import_wiring`, `registration`, `config_touch` 같은 제한 코드
- `required_new_files[]`:
  - guard가 신규 파일 생성을 허용 목록과 비교할 때 사용
- `forbidden[]`:
  - 문자열 배열 대신 객체 배열 사용
  - 최소 필드: `type`, `reason`
  - `path`, `anchor`, `pattern`은 type별 선택 필드
- `messages.summary`:
  - CLI 출력과 guard 요약 메시지의 기본 소스로 사용 가능
- plan이 파손되었거나 필수 필드가 없으면 guard는 `fail` 또는 `plan_missing` 계열 상태로 처리

---

## 5. 위치 결정 알고리즘

### 동작 우선순위
1. **규칙 기반** (API 없음, 기본 동작)
2. **LLM 연동** (선택적, `--ai` 옵션)

### 규칙 기반 4단계

**Step 1: 파일 크기 체크 (기계적)**
```
후보 파일 줄 수 > 150줄  → 신규 파일 생성 필수
후보 파일 앵커 수 > 5개  → 모듈 분리 권고
```

**Step 2: project_map 메타데이터 기반 후보 압축**
```
기능 설명 키워드 추출
    ↓
project_map의 category / anchor_index / line_count 확인
    ↓
후보 파일 압축 / 근거 부족 시 신규 파일 쪽으로 보수적 결정
```

> **project_map 없을 때 폴백**: `.vibelign/project_map.json`이 없거나 watch가 꺼져 있으면 Step 2를 건너뛰고 Step 3(경로/폴더 패턴 매칭)만으로 진행한다. 터미널에 경고를 출력한다:
> ```
> [VibeLign] project_map이 없습니다. 경로 패턴 기반으로만 분석합니다.
> 정확도를 높이려면 `vib watch`를 실행하거나 `vib scan`으로 맵을 생성하세요.
> ```
> project_map 없이도 `vib plan-structure`는 실행되지만 제안 정확도가 낮아질 수 있다.

**Step 3: 폴더 패턴 매칭**
```
"auth", "oauth", "login", "token"  → core/auth* 계열
"cli", "command"                   → commands/
"watch", "monitor", "scan"         → core/watch_*
"mcp", "handler"                   → mcp/
"test"                             → tests/
```
> 초기 버전에서는 이 매핑을 코드에 명시적으로 둔다. 자동 학습은 후속 단계 과제.

**Step 4: 앵커 가용성 체크**
```
수정 후보 파일 선정
    ↓
적합한 앵커 있음 → 그 구간에 추가
앵커 없음 → 신규 파일 생성으로 전환
앵커는 있지만 키워드와 매칭되는 앵커 없음
    → 보수적 결정: 신규 파일 생성 권고
    → (단, category 매칭이 강하면 가장 근접한 앵커 제안 가능)
```

> **앵커 매칭 실패 엣지 케이스**: 파일에 앵커가 존재하더라도 feature 키워드와 의미적으로 연결되는 앵커가 없으면 신규 파일 생성으로 보수적 전환한다. category 매칭(Step 2)이 강한 경우에만 예외적으로 "가장 근접한 앵커 구간 사용"을 제안할 수 있으며, 이 경우 evidence에 근거를 기록한다.

### 규칙 기반 한계 및 LLM 폴백

| 상황 | 규칙 기반 | LLM (--ai) |
|---|---|---|
| 키워드 명확 ("auth", "CLI") | 정확 | 정확 |
| 키워드 모호 ("개선", "수정") | 실패 → 사용자에게 명확화 요청 | 컨텍스트로 판단 |
| 새 도메인 (기존 패턴 없음) | 신규 파일 생성 | 프로젝트 맥락 반영 |

규칙 기반이 위치를 확정 못하면:
```
[VibeLign] 기능 설명이 모호합니다.
더 구체적으로 설명하거나 --ai 옵션을 사용하세요.
예: vib plan-structure --ai "OAuth 인증 추가"
```

---

## 6. vib plan-structure 호출 강제 방법

### 세션 잠금 방식

`vib plan-structure` 실행 시 별도 `session_plan.json`을 만들기보다
기존 `.vibelign/state.json`의 세션 상태와 공존 가능한 형태로 계획 상태를 저장한다.

목표는 "계획 없이 바로 코딩"을 줄이는 것이지, 상태 파일을 이원화하는 것이 아니다.

### Claude Code (진짜 강제)

앵커 집행 시스템과 **동일한 단일 PreToolUse 훅**을 공유한다 (`vib claude-hook`).
훅이 순서대로 두 가지를 검사:

```
AI가 Write/Edit 시도
    ↓
VibeLign PreToolUse 훅 (하나, 앵커 집행 시스템과 공유)
    ① plan-structure 세션 존재? (구조 계획 시스템)
       → 없음: 차단 + "vib plan-structure를 먼저 실행하세요"
    ② 앵커 있는가? (앵커 집행 시스템)
       → 없음: 경고 + 재작성 유도
    ↓
planning은 Claude 컨텍스트에서 strict + enable 상태일 때만 차단,
앵커는 경고를 보여주고 현재 Write를 한 번 막은 뒤 다시 쓰게 유도
```

훅 관리: `vib claude-hook enable / disable / status`
실제 로직은 `hook_setup.py`에, CLI는 `vib_claude_hook_cmd.py`에 분리.

> strict는 전역값 하나가 아니라 **컨텍스트별 계산값**이다. git pre-commit, Claude PreToolUse, 수동 `vib guard`는 서로 독립적으로 strict/non-strict를 해석한다.

**컨텍스트별 집행 강도 (앵커 집행 시스템과 동일 정책):**

| 컨텍스트 | planning 강도 | 앵커 강도 |
|---|---|---|
| Claude Code PreToolUse | gating (차단) | 한 번 막고 다시 쓰게 유도 |
| git pre-commit | strict (차단) | strict (차단) |
| vib guard (수동 실행) | non-strict 기본 (경고) | non-strict 기본 (경고) |

> `vib guard --strict`로 수동 실행 시 수동 guard 컨텍스트도 차단 동작으로 전환 가능.
> Claude Code PreToolUse의 planning이 gating인 이유: Write 도구 호출 전에 개입 가능하므로 사전 차단이 현실적임.

### git 사용자 (커밋 시 강제)

커밋 시 planning 상태 존재 여부 검사:
```
계획 상태 없음 → 커밋 차단 (strict)
"vib plan-structure 없이 작업이 감지됐습니다"
```

> 어떤 변경에 강제를 적용할지는 §7 `vib guard` 판정 규칙 표(Step A-D)를 따른다.
> 요약: 문서/테스트/config 수정 및 소규모 단일 파일 수정은 `planning_exempt`, 신규 production 파일 생성 또는 multi-file 수정은 `planning_required`.

### AI별 강제 수준

| AI | 강제 방법 | 강도 |
|---|---|---|
| Claude Code | PreToolUse 훅 + 세션 잠금 | 진짜 강제 |
| git 사용자 | 기존 pre-commit hook 확장 경로에서 커밋 차단 | 커밋 시 강제 |
| Cursor / Codex / 기타 | AGENTS.md 규칙 | 권고 수준 |

---

## 7. 보조 안전망 (A 방식 병행)

`vib plan-structure`를 안 쓴 경우 최후 방어선:

```
파일 줄 수 > 200줄 AND 앵커 없음 → vib guard 경고
파일 줄 수 > 300줄 → git pre-commit 경고
```

> 차단이 아닌 "경고" → 코알못 사용자 혼란 방지
> 강한 차단은 `--strict` 옵션으로 개발자만

### guard 판정 규칙 표 (Phase 1 초안)

| 변경 유형 | 예시 | planning 상태 없음 | planning 상태 있음 + 준수 | planning 상태 있음 + 이탈 |
|---|---|---|---|---|
| 문서 수정 | `docs/README.md` 편집 | `planning_exempt` | `planning_exempt` | `planning_exempt` |
| 테스트만 수정 | `tests/test_watch_engine.py` 추가/수정 | `planning_exempt` | `planning_exempt` | `planning_exempt` |
| config-only 수정 | `pyproject.toml`, `.claude/settings.json` 수정 | `planning_exempt` | `planning_exempt` | `planning_exempt` |
| 단일 파일 소규모 코드 수정 | 기존 production 파일 1개에서 국소 버그 수정 | `planning_exempt` 또는 warn | 준수로 처리 | 필요 시 warn |
| 기존 production 경로의 multi-file 코드 수정 | `core/`, `service/`, `mcp/`, `commands/` 내 2개 이상 파일 수정 | `planning_required` | 준수로 처리 | `plan_exists_but_deviated` |
| 새 production code file 생성 | `vibelign/core/oauth_provider.py` 신규 생성 | `planning_required` | 준수로 처리 | `plan_exists_but_deviated` |
| 계획이 있는 구조 변경 | plan 파일에 허용된 파일/앵커 범위 내 수정 | 해당 없음 | pass | 해당 없음 |
| 계획을 벗어난 구조 변경 | plan에 없는 파일 생성, 금지 경로 수정, 허용 anchor 이탈 | `planning_required` 또는 fail | 해당 없음 | fail |

**Phase 1 판정 메모:**
- `planning_required`: Claude PreToolUse에서는 사전 차단 후보, git/pre-commit에서는 fail 또는 강한 warn 후보
- `planning_exempt`: plan 없이 진행 가능, 단 일반 guard 규칙(앵커/구조/크기)은 별도 적용
- `plan_exists_but_deviated`: plan은 있었지만 실제 변경이 허용 범위를 벗어난 상태
- "단일 파일 소규모 코드 수정"은 line count만으로 확정하지 않고, path와 새 파일 여부를 함께 본다

### `vib guard` 구현 상세 spec (Phase 1)

#### 1) 목표

`vib guard`는 구조 계획 시스템 관점에서 다음 3가지를 판정해야 한다.

1. 현재 변경이 `plan-structure` 없이 진행 가능한 변경인가?
2. 현재 변경이 `plan-structure`가 필요한 변경인가?
3. plan이 존재한다면 실제 변경이 plan 범위를 준수했는가?

Phase 1에서는 LLM 추론 없이 **규칙 기반 판정**만 사용한다.

#### 2) 입력 데이터

`vib guard`는 최소한 아래 입력을 사용한다.

- **변경 집합**
  - git 환경: staged diff 우선
  - 비 git 환경 또는 staged 없음: working tree 변경 파일
  - 필요 시 `since_minutes` 같은 기존 guard 옵션과 공존 가능
- **파일 메타데이터**
  - 경로
  - 신규 생성 여부
  - 삭제 여부
  - 파일 유형(source / test / docs / config / other)
  - line delta 또는 added lines
- **프로젝트 메타데이터**
  - `.vibelign/project_map.json`이 있으면 `category`, `anchor_index`, `line_count` 참고
  - 없으면 경로 기반 분류로 폴백
  - `.vibelign/config.json`이 있으면 `small_fix_line_threshold` 설정값 참고 (없으면 기본값 30)
- **planning 상태**
  - `.vibelign/state.json` 내부 planning session 상태
  - 현재 활성 plan id
  - 연결된 `.vibelign/plans/*.json` plan 내용

#### 3) 사전 분류 규칙

각 변경 파일은 아래 순서로 분류한다.

1. **문서 파일**: `docs/`, `*.md`, handoff/report 문서
2. **테스트 파일**: `tests/`, `test_*.py`, `*.test.ts`, `*.spec.ts`
3. **config 파일**: `pyproject.toml`, `package.json`, `.claude/settings.json`, `.vibelign/*.json`, `*.yaml`, `*.yml`
4. **source code 파일**: `vibelign/`, 앱 코드, 서비스 코드, 명령/핸들러 코드
5. **other**: 위 어디에도 명확히 속하지 않는 파일

추가로 source code 파일은 경로 기준으로 다음 중 하나로 나눈다.

- `production_path`: `app/`, `core/`, `service/`, `services/`, `mcp/`, `commands/`, 기타 실제 기능 코드 경로
- `support_path`: `docs/`, `tests/`, fixture, example, generated, temp 성격 경로

#### 4) 판정용 집계 값

`vib guard`는 변경 집합에서 다음 값을 계산한다.

- `changed_file_count`
- `changed_source_file_count`
- `changed_production_file_count`
- `new_production_file_count`
- `multi_file_production_edit` (production source file 2개 이상 변경 여부)
- `has_only_docs_changes`
- `has_only_test_changes`
- `has_only_config_changes`
- `has_small_single_file_fix_candidate`

`has_small_single_file_fix_candidate`는 아래를 모두 만족할 때만 `true`다.

- 변경 파일이 정확히 1개
- 그 파일이 기존 production source file
- 신규 파일 생성이 아님
- added lines가 작은 범위(임계값은 `.vibelign/config.json`의 `small_fix_line_threshold` 설정값 사용, 기본값 30줄)
- plan에서 다뤄야 할 구조 변경 신호가 없음

`small_fix_line_threshold`는 프로젝트별 조정 가능하지만, 이 값은 **보조 신호**일 뿐 단독 판정 기준이 아니다.
즉, threshold 초과만으로 곧바로 `planning_required`가 되지 않으며,
threshold 이하만으로 자동으로 `planning_exempt`가 되지도 않는다.

여기서 구조 변경 신호는 예를 들어 아래다.

- 새 파일 생성
- production 파일 2개 이상 변경
- 새로운 import/export wiring 추가가 큰 비중을 차지함
- 금지 경로 또는 새 모듈 경계 생성

#### 5) plan 조회 규칙

`vib guard`는 planning 상태가 있더라도 무조건 pass하지 않는다.

조회 순서는 다음과 같다.

1. `.vibelign/state.json`에서 활성 planning 상태 확인
2. 활성 상태가 가리키는 `plan_id` 확인
3. 해당 `.vibelign/plans/<plan_id>.json` 로드
4. plan이 없거나 파손되었으면 `plan_missing`으로 간주

Phase 1에서 plan은 최소한 아래 필드를 가진다고 가정한다.

- `allowed_modifications[]`
  - `path`
  - `anchor`
  - `max_lines_added` (선택)
- `required_new_files[]`
  - `path`
- `forbidden[]`

#### 6) 최종 판정 순서

`vib guard`의 구조 계획 판정은 아래 순서를 고정한다.

**Step A — 면제 여부 먼저 판정**

아래 중 하나면 우선 `planning_exempt` 후보로 본다.

- 문서만 변경
- 테스트만 변경
- config-only 변경
- `has_small_single_file_fix_candidate == true`

단, 면제 후보라도 기존 일반 guard 규칙(앵커 손실, 구조 위험, 파일 비대화 등)은 별도로 계속 검사한다.

**Step B — 계획 필요 여부 판정**

아래 중 하나면 `planning_required`다.

- `new_production_file_count >= 1`
- `multi_file_production_edit == true`
- production path에서 구조 변경 신호 감지

**Step C — plan 존재 여부 확인**

- `planning_required`인데 활성 plan이 없으면 결과는 `planning_required`
- `planning_required`이고 활성 plan이 있으면 Step D로 진행

**Step D — plan 준수 여부 확인**

각 변경 파일마다 아래를 검사한다.

1. 신규 파일이면 `required_new_files.path` 또는 명시적으로 허용된 신규 생성 대상에 포함되는가?
2. 기존 파일 수정이면 `allowed_modifications.path`에 포함되는가?
3. anchor 정보가 있으면 실제 수정이 허용 anchor 범위 내인가?
4. `max_lines_added`가 있으면 초과했는가?
5. forbidden 규칙과 충돌하는가?

판정 결과:

- 모두 통과 → `pass`
- plan은 있으나 일부 파일/anchor/line 제한 위반 → `plan_exists_but_deviated`
- forbidden 직접 위반 → `fail`

#### 7) 결과 상태 정의

Phase 1에서 구조 계획 관련 상태는 아래 5개를 사용한다.

- `pass`: plan이 필요했고, 활성 plan도 있으며, 실제 변경이 plan을 준수함
- `planning_exempt`: 현재 변경은 plan 없이 진행 가능한 범위임
- `planning_required`: 현재 변경은 plan이 필요하지만 활성 plan이 없음
- `plan_exists_but_deviated`: 활성 plan은 있으나 실제 변경이 허용 범위를 벗어남
- `fail`: 명시 금지 규칙 위반 또는 plan/상태 파손으로 안전하게 진행 불가

#### 8) strict / non-strict 동작

구조 계획 판정은 `strict` 여부에 따라 아래처럼 동작한다.

- **non-strict**
  - `planning_exempt` → pass
  - `planning_required` → warn
  - `plan_exists_but_deviated` → warn
  - `fail` → fail
- **strict**
  - `planning_exempt` → pass
  - `planning_required` → fail
  - `plan_exists_but_deviated` → fail
  - `fail` → fail

**기본값 정책 (사용자 유형별):**

| 사용자 유형 | 기본 strict | 설정 방법 |
|---|---|---|
| 코알못 / 일반 사용자 | **non-strict** (경고만) | 별도 설정 불필요 |
| git 개발자 | **strict** (차단) | 기존 pre-commit hook 확장 경로 설치 시 자동 적용 |
| Claude Code 사용자 | **사용자 선택형** (enable이면 strict / disable이면 non-strict) | VibeLign이 hook 자동 설치 후 on/off로 제어 |

> non-strict를 기본으로 하는 이유: 코알못 사용자가 경고를 보고 학습하며 점진적으로 규칙을 익힐 수 있도록.
> git strict는 의도적으로 **기존 pre-commit hook 확장 경로**를 설치한 사용자에게 적용 — "설치했다는 것"이 곧 강제를 원한다는 동의.
> Claude는 설치와 활성화를 분리한다: 설치는 VibeLign이 자동화하고, strict 진입은 사용자가 기능을 enable 했을 때로 본다.

**컨텍스트별 상태 결정표 (Phase 1 고정):**

| 컨텍스트 | 설치 상태 | 활성 상태 | strict 결과 | 비고 |
|---|---|---|---|---|
| git pre-commit | 기존 pre-commit hook 확장 경로 설치됨 | 해당 없음 | strict | `.git/hooks/pre-commit` 기준 |
| git pre-commit | 설치 안 됨 | 해당 없음 | non-strict 아님 / 미적용 | 이 컨텍스트 자체가 없음 |
| Claude PreToolUse | hook 엔트리 설치됨 | `claude_hook_enabled=true` | strict 후보 | Claude 컨텍스트에서만 의미 있음 |
| Claude PreToolUse | hook 엔트리 설치됨 | `claude_hook_enabled=false` | non-strict | hook은 남고 enforcement만 skip |
| 수동 `vib guard` | 해당 없음 | `--strict` 있음 | strict | CLI 실행 한 번에만 적용 |
| 수동 `vib guard` | 해당 없음 | `--strict` 없음 | non-strict | 기본 경고 중심 |

> 구현 포인트: `strict`는 전역 불리언이 아니라 **컨텍스트별 계산 결과**이며, 다른 컨텍스트의 설치 상태를 덮어쓰지 않는다.

**strict 판정 우선순위:**

1. 명시 설정값이 있으면 그 값을 최우선 적용
2. 명시 설정이 없고 git pre-commit hook 확장 경로가 설치되어 있으면 **git 컨텍스트**에서 strict
3. 명시 설정이 없고 Claude PreToolUse 기능이 enable 상태이면 **Claude 컨텍스트**에서 strict
4. 명시 설정이 없고 Claude PreToolUse 기능이 disable 상태이면 **Claude 컨텍스트**에서 non-strict
5. 위 조건이 모두 없으면 기본값은 non-strict

> 즉, 일반 사용자는 별도 설정 없이 경고만 받고, git 개발자는 hook 설치 시 **git 컨텍스트에서만** 자동 strict, Claude 사용자는 hook은 자동 설치되더라도 기능 on/off를 직접 선택할 수 있다.

**Claude Code hook 운영 원칙:**

- Claude 프로젝트가 감지되면 VibeLign은 project-local `.claude/settings.json`에 필요한 hook 엔트리를 자동 설치/복구할 수 있다
- 자동 설치/복구는 `vib start` 및 관련 setup 명령에서만 수행하고, read-only 명령에서는 수행하지 않는다
- 단, PreToolUse 기능 활성 여부는 별도 상태로 관리한다
- 권장 명령 예시:
  - `vib claude-hook enable`
  - `vib claude-hook disable`
  - `vib claude-hook status`
- enable 상태면 Claude 경로는 strict 후보, disable 상태면 Claude 경로는 non-strict 유지
- `disable`는 hook JSON 엔트리를 제거하는 것이 아니라, 설치된 hook의 enforcement 로직을 비활성화하는 뜻으로 사용한다
- 수동 JSON 편집은 fallback일 뿐 기본 경로가 아니다
- git hook 설치 여부가 Claude enable/disable를 덮어쓰지 않는다. 두 컨텍스트는 독립적으로 판정한다

**planning 상태 스키마 (`.vibelign/state.json`) 초안:**

```json
{
  "planning": {
    "active": true,
    "plan_id": "20260409T123456_oauth_auth",
    "feature": "OAuth 인증 추가",
    "override": false,
    "override_reason": null,
    "created_at": "2026-04-09T12:34:56",
    "updated_at": "2026-04-09T12:34:56"
  }
}
```

- `planning.active=false` 또는 필드 없음 → 활성 plan 없음
- `plan_id`는 `.vibelign/plans/<plan_id>.json`과 반드시 연결되어야 함
- `override=true`면 guard는 현재 세션을 `planning_exempt`로 처리 가능
- `updated_at`은 `vib plan-structure`, `vib plan-override`, 커밋 후 clear 시점에 갱신

#### 9) 출력 계약

기존 guard envelope에 구조 계획 판정 결과를 아래 형태로 추가한다.

```json
{
  "ok": true,
  "data": {
    "status": "warn",
    "planning": {
      "status": "planning_required",
      "strict": false,
      "active_plan_id": null,
      "summary": "새 production code file 생성이 감지되어 plan-structure가 필요합니다.",
      "changed_files": [
        "vibelign/core/oauth_provider.py"
      ],
      "required_reasons": [
        "new_production_file"
      ],
      "deviations": [],
      "exempt_reasons": []
    }
  }
}
```

필수 필드:

- `planning.status`
- `planning.strict`
- `planning.active_plan_id`
- `planning.summary`
- `planning.changed_files[]`
- `planning.required_reasons[]`
- `planning.deviations[]`
- `planning.exempt_reasons[]`

#### 10) 사용자 메시지 규칙

상태별 기본 메시지는 고정한다.

- `planning_exempt`
  - "현재 변경은 plan-structure 없이 진행 가능한 범위입니다."
- `planning_required`
  - "구조 영향 가능성이 높은 변경이 감지되었습니다. 먼저 `vib plan-structure`를 실행하세요."
- `plan_exists_but_deviated`
  - "활성 구조 계획은 존재하지만 실제 변경이 허용 범위를 벗어났습니다."
- `fail`
  - "구조 계획 검증에 실패했습니다. 금지 규칙 위반 또는 plan 상태 이상을 확인하세요."

메시지는 항상 **왜 이렇게 판정됐는지**를 함께 붙여야 한다.

예:

- 새 production file 감지
- 허용되지 않은 파일 수정 감지
- 허용 anchor 범위 밖 수정 감지
- plan 파일 누락

#### 11) Phase 1 비목표

아래는 Phase 1에서 하지 않는다.

- AST 수준의 정밀 semantic diff
- 함수 단위 책임 추론
- LLM 기반 의도 분류
- Codex/Cursor 등 비-Claude 환경에서의 사전 강제 보장

---

## 8. 앵커 집행 시스템과의 관계

이 시스템은 `2026-04-09-anchor-enforcement-system.md`와 함께 동작합니다.

```
역할 분리:
  구조 계획 시스템  → "어느 파일에 넣을 것인가" 결정
  앵커 집행 시스템  → "앵커가 있는가" 보장

함께 동작:
  vib plan-structure → 파일 위치 확정
  AI 코딩
  watch --auto-fix   → 앵커 자동 삽입
  vib guard          → 구조 계획 + 앵커 모두 검증
```

---

## 9. 필요한 변경 파일

| 파일 | 변경 유형 | 내용 |
|---|---|---|
| `vibelign/commands/vib_plan_structure_cmd.py` | 신규 | `vib plan-structure` 명령어 |
| `vibelign/core/structure_planner.py` | 신규 | 위치 결정 알고리즘 (4단계) |
| `vibelign/core/meta_paths.py` | 수정 | plans 경로 및 관련 메타 경로 중앙화 |
| `vibelign/mcp/mcp_state_store.py` 또는 연계 상태 저장 모듈 | 수정 | 기존 session state와 공존 가능한 planning 상태 저장 |
| `vibelign/commands/vib_guard_cmd.py` | 수정 | 구조 계획 준수 여부 검증 추가 |
| `vibelign/cli/vib_cli.py` | 수정 | 새 명령어 등록 |
| `vibelign/core/hook_setup.py` | 수정 | 통합 PreToolUse 훅 로직 (앵커 집행 시스템과 공유) |
| `vibelign/commands/vib_claude_hook_cmd.py` | 신규 (앵커 집행과 공유) | CLI 래퍼: enable/disable/status |
| `AGENTS.md` | 수정 | 구조 계획 필수 규칙 추가 |

---

## 10. 미해결 과제

1. **세션 잠금 만료 기준 — 해결됨**

   Phase 1에서는 **이벤트 기반 만료**를 사용한다. 시간 기반 만료는 사용하지 않는다.

   **만료 트리거:**
   - `git commit` 완료 시 → pre-commit hook이 state에서 `plan_id`를 클리어
   - `vib plan-structure` 재실행 시 → 새 plan이 이전 plan을 대체 (단일 활성 plan 정책)
   - `vib plan-close` 명령 (Phase 1 최소 버전 포함)

   **`vib plan-close` 최소 버전 (Phase 1 포함):**
   - 별도 복잡한 archive/undo 없이 `.vibelign/state.json`의 `planning.active=false`, `plan_id=null` 세팅
   - 이미 inactive 상태면 no-op
   - 목적: 작업 취소 / 잘못 잡은 plan / 중도 종료 시 수동 해제 경로 제공

   **단일 활성 plan 정책 (Phase 1):**
   - 활성 plan은 항상 1개. 새 `vib plan-structure` 실행 시 이전 plan은 archived 상태로 이동.
   - 연속 기능 작업 시 기능마다 새로 실행하는 것이 원칙.

   **기존 session과 공존:**
   - `.vibelign/state.json` 내에 `planning` 필드를 별도 추가해 기존 patch/verification session과 독립적으로 관리한다. 충돌 없음.

2. **계획이 틀렸을 때 — `vib plan-override` 설계**

   AI가 계획보다 더 나은 구조를 판단하거나, 계획 자체가 잘못됐을 때를 위한 탈출구.

   **명령어:**
   ```bash
   vib plan-override "<이유>"
   ```

   **동작:**
   - `.vibelign/state.json`의 `planning` 필드에 `override: true`와 `override_reason`, `overridden_at` 기록
   - guard는 override 플래그가 있으면 현재 세션을 `planning_exempt`로 처리
   - override는 다음 커밋 완료 또는 새 `vib plan-structure` 실행 시 자동 해제

   **제약:**
   - 이유 없이(`""`) override 금지 — guard가 빈 reason을 warn 처리
   - override 사용 횟수는 guard 출력에 기록 (audit trail)

   **Phase 1 구현 범위:** 상태 저장/조회만. guard 연동은 Ticket 6 이후 추가.

3. **Claude Code 외 AI 강제 방법**
   - Cursor, Codex 등에서 plan-structure 호출을 강제할 수단 없음
   - 장기적으로 각 AI 플랫폼의 훅 시스템 지원 필요

4. **강제 적용 대상 변경 유형 기준**
   - `plan-structure`는 모든 수정에 강제하지 않고, **구조에 영향을 줄 가능성이 높은 변경**에만 요구해야 함
   - Phase 1 기본 원칙:
     - 새 **production code file** 생성 → 계획 필요
     - 기존 **app/core/service/mcp/commands** 계열에 대한 multi-file 코드 수정 → 계획 필요
     - 단일 파일의 소규모 버그 수정, 문서 수정, 테스트 추가/수정, config-only 수정 → 기본 면제
   - 강제 여부 판단은 최소한 아래 신호를 함께 보아야 함:
     - 파일 유형: source code / test / docs / config
     - 파일 수: single-file / multi-file
     - 새 파일 여부: 기존 파일 수정인지 신규 생성인지
     - 경로 성격: production path인지 보조 path인지
   - line count는 보조 신호로만 사용하고, 단독 기준으로 쓰지 않음
   - guard와 hook은 최종적으로 다음 세 상태 중 하나를 판정해야 함:
     - `planning_required`
     - `planning_exempt`
     - `plan_exists_but_deviated`
   - 문서에 예시를 함께 고정해야 함:
     - `docs/README.md` 수정 → 면제
     - `tests/test_watch_engine.py` 테스트 추가 → 면제
     - `vibelign/core/auth.py` + `vibelign/core/oauth_provider.py` 동시 수정/생성 → 계획 필요
     - `vibelign/mcp/mcp_patch_handlers.py` 한 파일에서 3줄 버그 수정 → 기본 면제

5. **project_map 최신성 → 해결됨**
   - watch 엔진이 `_refresh_project_map()` 자동 호출 가능
   - 단, watch가 꺼져 있거나 project_map이 아직 없으면 별도 생성/갱신 필요

---

## 11. 구현 순서 (implementation plan)

> **진행 현황 업데이트 (2026-04-10):**
> - **Phase 1 / Ticket 1-3:** 구현 완료
>   - `vib plan-structure` 추가
>   - `.vibelign/plans/*.json` 저장
>   - `.vibelign/state.json` planning 상태 저장
> - **Phase 2 / Ticket 4:** 구현 완료
>   - `structure_planner.py` 규칙 엔진 1차 고도화 완료
>   - representative case(`OAuth 인증 추가`, `watch 기능 확장`, `mcp handler 수정`)와 candidate narrowing / `anchor_index` 기반 viability / evidence 보강 테스트 반영 완료
> - **Phase 3 / Ticket 5-7:** 구현 완료
>   - `vib guard` planning 섹션, staged 우선 수집, active plan 비교, strict/non-strict 병합 구현 완료
>   - `allowed_change_types`, config threshold, Step A exemption ordering, mixed change-set deviation, reason-bearing exempt summary까지 Oracle sign-off 완료
> - **Phase 4 / Ticket 8 + Claude PreToolUse 1차:** 구현 완료
>   - git pre-commit 경로에서 `vib guard --strict`를 실제 차단 경로로 연결 완료 (Oracle sign-off 완료)
>   - Claude `.claude/settings.json` PreToolUse hook 자동 설치/복구, `vib claude-hook enable|disable|status`, `vib start` 자동 설치 plumbing 완료 (Oracle sign-off 완료)
>   - `vib pre-check`의 narrowed gating slice 완료: stdin JSON 파싱, disabled/non-source skip, `0`/`2` 계약, planning-required / plan-deviated / malformed-plan 차단, anchor-missing soft-block (Oracle sign-off 완료)
>   - 단, 이 단계는 **full `vib guard` parity 아님**. diff-aware multi-file 판단, anchor-range/max-lines/change-type 완전 동일성은 후속 강화 과제로 남음
> - **Phase 5:** 문서 범위 기준 완료
>   - regression-hardening slice 1 완료: multi-file production 수정 / strict escalation / forbidden hard fail 직접 고정
>   - regression-hardening slice 2 완료: `Claude hook disabled`, `git hook only` matrix row 직접 고정
>   - regression-hardening slice 3 완료: `test only`, `config only`, `단일 파일 소규모 수정` row 직접 고정
>   - regression-hardening slice 4 완료: `활성 plan + 허용 경로만 수정`, `활성 plan + 허용 범위 이탈`, `broken plan 파일` row 직접 고정
>   - regression-hardening slice 5 완료: guard broken-plan payload shape 검증을 precheck 수준에 가깝게 보강하고, `required_new_files` malformed branch까지 직접 고정
>   - regression-hardening slice 6 완료: `allowed_change_types`의 `import_wiring` / `registration` / `config_touch` pass branch 직접 고정
>   - regression-hardening slice 7 완료: `anchor_outside_allowed_range` / `max_lines_added_exceeded` direct parity branch 직접 고정
>   - regression-hardening slice 8 완료: guard/precheck state-error branch(`missing_plan_file`, `invalid_state`) exact contract 직접 고정
>   - regression-hardening slice 9 완료: `disallowed_change_type` 및 일부 singleton deviation assertion-strength 강화
>   - 현재 남은 것은 문서 범위 밖의 선택적 assertion-strength/parity 미세 강화 수준이며, 핵심 matrix row와 주요 runtime 분기는 직접 회귀 고정 완료

### Phase 1 — plan JSON 생성 경로 추가

**목표:** `vib plan-structure`가 rules 기반 계획 파일을 생성하고 state에 활성 plan을 기록한다.

**대상 파일**
- 신규: `vibelign/commands/vib_plan_structure_cmd.py`
- 신규: `vibelign/core/structure_planner.py`
- 수정: `vibelign/core/meta_paths.py`
- 수정: `vibelign/cli/vib_cli.py`
- 수정: `vibelign/mcp/mcp_state_store.py` 또는 planning 상태 저장 모듈

**구현 항목**
- `MetaPaths`에 plans 디렉터리 경로 추가
- `vib plan-structure` 명령 추가
- feature 문자열 입력 → 규칙 기반 위치 제안 생성
- 본 문서의 Phase 1 schema대로 `.vibelign/plans/<id>.json` 저장
- `.vibelign/state.json`에 활성 planning session 상태 저장

**완료 조건**
- 단일 명령으로 plan 파일 생성 가능
- 생성된 JSON이 schema 필수 필드를 모두 가짐
- state에서 활성 `plan_id` 조회 가능

### Phase 2 — planner 규칙 엔진 고도화

**목표:** path/category/anchor/line_count 기반으로 allowed_modifications, required_new_files, forbidden을 안정적으로 산출한다.

**대상 파일**
- `vibelign/core/structure_planner.py`
- 필요 시 `vibelign/core/project_map.py`, `vibelign/core/project_scan.py`

**구현 항목**
- feature 텍스트에서 keyword 추출
- path signal / category / anchor availability 조합으로 후보 파일 압축
- 신규 파일 생성 필요 여부 판단
- forbidden 규칙 객체 생성
- `messages.summary` 및 evidence 필드 생성

**완료 조건**
- `OAuth 인증 추가`, `watch 기능 확장`, `mcp handler 수정` 같은 대표 케이스에서 일관된 plan 산출
- 근거 부족 시 보수적으로 신규 파일 생성 쪽으로 기울어짐

### Phase 3 — `vib guard` planning 판정 추가

> **현재 상태:** 완료. Oracle 최종 리뷰 기준으로 Phase 3 guard slice는 구현 및 검증이 끝났음.

**목표:** guard가 plan 필요 여부와 plan 준수 여부를 판정한다.

**대상 파일**
- 수정: `vibelign/commands/vib_guard_cmd.py`
- 필요 시 수정: guard envelope 생성 관련 코어 모듈

**구현 항목**
- 변경 집합 수집 (staged 우선, working tree 폴백)
- 파일 유형 / path class 분류
- `planning_required`, `planning_exempt`, `plan_exists_but_deviated`, `pass`, `fail` 상태 판정
- plan 파일 로드 및 준수 비교
- JSON/text 결과에 planning 섹션 추가

**완료 조건**
- 본 문서의 guard spec 예시와 같은 envelope 출력
- strict / non-strict 동작 차이 반영
- plan 없는 구조 변경은 감지 가능

### Phase 4 — Claude / git enforcement 연결

> **현재 상태:** 완료 (현재 범위 기준, Oracle sign-off 완료).
> - git pre-commit enforcement slice 완료
> - Claude hook plumbing slice 완료
> - `vib pre-check` narrowed gating slice 완료
> - 남은 것은 Phase 4의 필수 범위가 아니라, Claude 경로를 git guard 수준으로 더 가깝게 만드는 후속 강화 작업임

**목표:** Claude와 git 경로에서 planning 판정을 실제 차단/경고로 연결한다.

**대상 파일**
- 수정: `vibelign/core/git_hooks.py`
- 수정 또는 연계: `vibelign/core/hook_setup.py`
- 필요 시 수정: 관련 CLI install/setup 진입점
- 신규/수정: Claude hook enable/disable/status 진입점

**구현 항목**
- git pre-commit 경로에서 `vib guard --strict` 결과 반영
- Claude 프로젝트 감지 시 hook 자동 설치/복구
- Claude PreToolUse에서 planning 상태 확인 후 사전 차단 또는 경고
- Claude hook enable/disable/status 상태 관리
- 기존 anchor enforcement 흐름과 충돌하지 않도록 통합

**완료 조건**
- git 사용자: 구조 계획 누락/이탈 시 커밋 차단 가능
- Claude 사용자: hook은 수동 JSON 편집 없이 사용 가능
- Claude 사용자: plan 없는 구조 변경에 대해 on/off 상태에 맞는 동작 수행 가능

### Phase 5 — 테스트 및 회귀 고정

**목표:** planner/guard/enforcement 규칙이 회귀 없이 유지되도록 테스트를 추가한다.

**대상 파일**
- 신규 테스트: `tests/test_structure_planner.py`
- 신규 테스트: `tests/test_guard_planning.py`
- 필요 시 기존 `tests/test_mcp_patch_session.py`, `tests/test_watch_engine.py` 보강

**구현 항목**
- exempt 케이스 테스트
- planning_required 케이스 테스트
- plan_exists_but_deviated 케이스 테스트
- strict/non-strict 차이 테스트
- plan 파일 누락/파손 테스트

**완료 조건**
- 대표 경로별 판정이 테스트로 고정됨
- plan/state 파손 시 안전 실패 동작 검증됨

### 구현 전 테스트 매트릭스 (우선 고정)

| 케이스 | 입력 상태 | 기대 결과 |
|---|---|---|
| docs only 수정 | `docs/README.md` 수정 | `planning_exempt` |
| test only 수정 | `tests/test_watch_engine.py` 수정 | `planning_exempt` |
| config only 수정 | `.claude/settings.json` 수정 | `planning_exempt` |
| 단일 파일 소규모 수정 | production 파일 1개, threshold 이하, 새 파일 아님 | `planning_exempt` 또는 warn |
| 신규 production 파일 생성 | `vibelign/core/foo.py` 신규 | `planning_required` |
| multi-file production 수정 | `core/` 2개 이상 수정 | `planning_required` |
| 활성 plan + 허용 경로만 수정 | `allowed_modifications` 범위 내 | `pass` |
| 활성 plan + 허용 범위 이탈 | 허용되지 않은 파일/anchor 수정 | `plan_exists_but_deviated` |
| forbidden 위반 | 금지 경로 수정 | `fail` |
| broken plan 파일 | JSON 파손 또는 필수 필드 누락 | `fail` |
| Claude hook disabled | hook 설치됨 + `claude_hook_enabled=false` | Claude 컨텍스트 non-strict |
| git hook only | pre-commit hook 설치됨, Claude disabled | git strict / Claude non-strict |

> 구현 시작 전에 이 표를 테스트 케이스 이름으로 바로 옮기면, 단계별 구현에서 방향이 흔들리지 않는다.

### 개발 착수용 작업 티켓 분해

#### Ticket 1 — planning state / meta path 뼈대 추가

**목표**
- `.vibelign/plans/` 경로와 planning state 저장소를 만든다.

**핵심 작업**
- `MetaPaths`에 plans 경로 추가
- `.vibelign/state.json`에 `plan_id`, planning session 메타 저장/조회 헬퍼 추가

**완료 조건**
- state에서 활성 `plan_id`를 읽고 쓸 수 있다
- plans 디렉터리를 안전하게 생성할 수 있다

#### Ticket 2 — `vib plan-structure` CLI 추가

**목표**
- 사용자가 feature 문자열로 구조 계획을 생성할 수 있게 한다.

**핵심 작업**
- `vib_plan_structure_cmd.py` 생성
- `vib_cli.py`에 명령 등록
- planner 호출 후 plan JSON 저장

**완료 조건**
- `vib plan-structure "OAuth 인증 추가"` 실행 시 plan 파일이 생성된다

#### Ticket 3 — plan JSON schema 고정

**목표**
- guard가 직접 소비할 수 있는 plan JSON 형식을 확정한다.

**핵심 작업**
- `schema_version`, `mode`, `scope`, `messages` 필드 반영
- `forbidden`을 객체 배열로 저장
- `allowed_change_types`, `required_reasons` 필드 반영

**완료 조건**
- 생성되는 plan이 본 문서 schema 필수 필드를 모두 포함한다

> 구현 순서 메모: planner 구현 전에 schema draft를 먼저 고정해야, Ticket 4에서 JSON 구조를 다시 뜯는 리스크를 줄일 수 있다.

#### Ticket 4 — `structure_planner.py` 1차 규칙 엔진 구현

**목표**
- rules 기반으로 candidate file, allowed modifications, required new files, forbidden 규칙을 생성한다.

**핵심 작업**
- keyword 추출
- category/path/anchor/line_count 기반 후보 압축
- 신규 파일 생성 필요 여부 판단
- `messages.summary`, `evidence.required_reasons` 생성

**완료 조건**
- 대표 입력 3종 이상에서 일관된 plan이 생성된다

#### Ticket 5 — `vib guard`에 planning 판정 추가

**목표**
- guard가 현재 변경이 exempt인지, planning required인지, plan deviation인지 판정한다.

**핵심 작업**
- staged/working tree 변경 수집
- docs/tests/config/source 분류
- `planning_required`, `planning_exempt`, `plan_exists_but_deviated`, `pass`, `fail` 계산

**완료 조건**
- JSON/text 결과에 planning 섹션이 추가된다

#### Ticket 6 — plan 준수 비교 로직 추가

**목표**
- 실제 변경이 plan 범위를 지키는지 비교한다.

**핵심 작업**
- 신규 파일 ↔ `required_new_files` 비교
- 기존 파일 수정 ↔ `allowed_modifications` 비교
- anchor / `max_lines_added` / forbidden 위반 감지

**완료 조건**
- plan deviation과 hard fail을 구분할 수 있다

#### Ticket 7 — strict / non-strict 정책 연결

**목표**
- 같은 planning 결과가 strict 여부에 따라 다르게 동작하게 한다.

**핵심 작업**
- non-strict: warn 중심
- strict: `planning_required`, `plan_exists_but_deviated`를 fail 처리

**완료 조건**
- strict / non-strict 동작 차이가 테스트 가능한 형태로 드러난다

#### Ticket 8 — git pre-commit 연동

**목표**
- git commit 직전 planning 위반을 차단한다.

**핵심 작업**
- 기존 `git_hooks.py` 흐름에 `vib guard --strict` 연동
- anchor enforcement / secrets hook과 충돌 없이 통합

**완료 조건**
- plan 없는 구조 변경이 pre-commit에서 차단된다

#### Ticket 9 — Claude PreToolUse 연동

**목표**
- Claude 환경에서 hook 자동 설치 + on/off 제어 + 사전 차단/경고를 구현한다.

**핵심 작업**
- Claude 프로젝트 감지 시 project-local hook merge-safe 설치
- `enable` / `disable` / `status` 상태 저장 및 조회
- planning state 조회
- PreToolUse 훅에서 `planning_required` 시 on/off 상태에 따라 차단/경고

**완료 조건**
- Claude Write/Edit 전에 planning 상태 기반 판정이 가능하다
- 코알못도 수동 JSON 편집 없이 Claude 보호 기능을 켜고 끌 수 있다

#### Ticket 10 — 테스트 세트 추가

**목표**
- planner / guard / enforcement 규칙을 회귀 테스트로 고정한다.

**핵심 작업**
- exempt 케이스
- planning_required 케이스
- plan_exists_but_deviated 케이스
- strict/non-strict 차이
- plan missing / broken plan 케이스

**완료 조건**
- 핵심 판정이 테스트로 고정되고 회귀가 잡힌다

#### 권장 구현 순서

`Ticket 1 → 2 → 3 → 4 → 5 → 6 → 7 → 10 → 8 → 9`

> 이유: plan/state/schema를 먼저 고정해야 guard를 구현할 수 있고,
> guard 판정이 안정화되어야 hook enforcement를 붙여도 디버깅 비용이 폭증하지 않는다.

---

*이 문서는 현재 구현 완료 상태를 반영한 기록 문서입니다. 남은 항목은 문서 범위 밖의 선택적 고도화입니다.*
