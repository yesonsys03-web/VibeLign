# PR 5 세부 스펙: 3 페르소나 라우팅 + Best-Effort 오케스트레이션

## 1. 목적

PR 5의 목적은 PR 4의 단일 CLI 페르소나를 확장해 **클로이·지오·미나 3 페르소나 기획방**을 제품의 핵심 경험으로 만드는 것이다.

사용자는 모델명이나 CLI 명령을 몰라도 된다. 화면에서는 페르소나 이름으로 부르고, 내부에서만 공식 CLI로 relay한다.

## 2. 범위

포함:

- `vibelign/core/planning_cli/cli_adapters.py`
  - `claude`, `codex`, `agy` adapter registry
  - 설치/로그인/timeout/status 분류 공통화
- `vibelign/core/planning_cli/personas.py`
  - `chloe`, `gio`, `mina` 기본 persona
- `vibelign/core/planning_cli/mentions.py`
  - `@클로이`, `@지오`, `@미나`, `@모두` parser
  - `@chloe`, `@gio`, `@mina`, `@all` alias
- `vibelign/core/planning_cli/orchestrator.py`
  - persona 순서 결정
  - best-effort 실행
  - 최종 Markdown synthesis
- GUI
  - 3 페르소나 상태 표시
  - mention 입력
  - persona별 응답/실패 요약
  - `Instant ⌄` 모드 선택과 persona mapping
- 정적 persona avatar 3종

제외:

- 사용자 제작 persona asset
- persona별 커스텀 시스템 프롬프트 편집
- 실시간 스트리밍
- background long-running daemon
- 자동 코드 수정 연결

## 3. Persona Mapping

| persona_id | 화면 이름 | 기본 역할 | CLI |
|---|---|---|---|
| `chloe` | 설계자 클로이 | 흐릿한 아이디어를 제품 기획안으로 구조화 | `claude` |
| `gio` | 검토자 지오 | 빠진 요구사항, 모순, 테스트 기준 검토 | `codex` |
| `mina` | 탐색자 미나 | MVP 축소안, 대안 흐름, 범위 조절 | `agy` |

PR 4에서 선택한 첫 adapter가 이 표의 어느 항목이든, PR 5에서는 나머지 두 adapter를 추가한다.

## 4. Mention Routing

규칙:

- mention이 없으면 준비된 persona 전체를 기본 순서대로 실행한다.
- `@클로이`, `@지오`, `@미나`는 해당 persona만 실행한다.
- `@모두`는 준비된 persona 전체를 실행한다.
- 여러 mention이 있으면 입력 순서가 아니라 고정 persona order `chloe -> gio -> mina`를 따른다.
- 설치되지 않았거나 로그인되지 않은 CLI는 건너뛰고 결과에 status를 남긴다.
- 전부 실패해도 template-only fallback으로 Markdown을 저장한다.

예:

| 입력 | 실행 |
|---|---|
| `예약 앱 만들고 싶어` | 준비된 persona 전체 |
| `@지오 빠진 테스트 봐줘` | 지오만 |
| `@클로이 @미나 MVP로 줄여줘` | 클로이, 미나 |
| `@모두 다시 검토해줘` | 준비된 persona 전체 |

## 5. Orchestration

PR 5는 안정성을 위해 **순차 실행**으로 시작한다.

기본 순서:

1. 클로이: 초안 구조화
2. 지오: 요구사항/테스트 검토
3. 미나: 범위 축소와 리스크 검토
4. VibeLign deterministic synthesis: 최종 Markdown 저장

이유:

- 어떤 CLI가 실패했는지 사용자와 테스트가 쉽게 이해할 수 있다.
- timeout/cancel 처리가 단순하다.
- 각 persona가 앞선 persona의 요약만 받아 과도한 토큰 사용을 줄인다.

동시 실행은 PR 5에서 하지 않는다. 필요하면 PR 8 이후 성능 개선으로 분리한다.

## 6. Transcript/Storage

기본 저장:

```text
plans/{slug}.md
.vibelign/planning/{session_id}/session.json
```

`session.json`에는 원문 전문 대신 상태와 요약만 저장한다.

```json
{
  "session_id": "plan_20260602_abc123",
  "agents_requested": ["chloe", "gio", "mina"],
  "agents_used": ["chloe", "gio"],
  "runs": [
    {
      "run_id": "run_chloe_001",
      "turn_id": "turn_001",
      "persona_id": "chloe",
      "cli_id": "claude",
      "status": "ok",
      "summary": "예약 생성/조회/취소 플로우를 정리함"
    }
  ]
}
```

`--save-transcript` 또는 GUI 고급 옵션을 켠 경우에만 원문을 저장한다.

```text
.vibelign/planning/{session_id}/turns/turn_001_claude.md
.vibelign/planning/{session_id}/turns/turn_002_codex.md
.vibelign/planning/{session_id}/turns/turn_003_agy.md
```

## 7. CLI Contract

```bash
vib plan "예약 앱 만들고 싶어"
vib plan "@지오 빠진 테스트 봐줘"
vib plan "예약 앱 만들고 싶어" --agents chloe,gio
vib plan "예약 앱 만들고 싶어" --cli claude,codex
vib plan "예약 앱 만들고 싶어" --save-transcript
vib plan "예약 앱 만들고 싶어" --json
```

`--agents`는 persona 기준이고, `--cli`는 내부 디버그/고급 옵션이다. GUI 기본 화면에는 `--cli` 개념을 노출하지 않는다.

JSON 성공 예:

```json
{
  "ok": true,
  "session_id": "plan_20260602_abc123",
  "output_path": "plans/reservation-app.md",
  "agents_requested": ["chloe", "gio", "mina"],
  "agents_used": ["chloe", "gio"],
  "agent_statuses": {
    "chloe": "ok",
    "gio": "ok",
    "mina": "not_installed"
  },
  "fallback_reason": null
}
```

## 8. GUI Contract

기획방 기본 화면:

- 입력 바
- persona chips: 클로이, 지오, 미나, 모두
- persona별 상태: 준비됨, 연결 필요, 검토 중, 완료, 건너뜀
- 최종 기획안 미리보기
- 저장된 파일 열기 버튼

GUI는 PR 3/4의 `create_planning_template` Tauri command을 확장해서 쓴다(요청에 `agents`/mention, 응답에 `agentStatuses` 추가). 새 병렬 경로(raw `run_vib(["plan",...])` 직접 호출)를 만들지 않는다.

raw stdout/stderr는 기본 화면에 노출하지 않는다. 고급 상세에서만 접을 수 있는 형태로 보여준다.

## 9. Safety/Terms Guardrails

필수:

- official CLI binary subprocess relay만 사용한다.
- VibeLign은 OAuth token, session file, cookie, keychain을 읽지 않는다.
- 계정 풀링, 중앙 credential 저장, 재판매형 proxy를 만들지 않는다.
- 각 adapter 실행 전에 사용자의 로컬 CLI 설정을 그대로 사용한다.
- Claude는 Agent SDK credit 사용 가능성을 고지한다.
- Antigravity는 제3자 relay 회색지대 고지를 유지한다.

금지:

- `.claude`, `.codex`, `.gemini`, `.config` credential 파일 직접 파싱
- TUI 화면 자동 입력
- 비공식 backend endpoint 호출
- 모델 응답 원문을 기본 저장

## 10. Failure Handling

| 상황 | 처리 |
|---|---|
| 일부 persona 실패 | 해당 persona만 건너뛰고 최종 Markdown 저장 |
| 전체 persona 실패 | template-only fallback 저장 |
| timeout | persona status `timeout`, 다음 persona 진행 |
| rate limit | persona status `rate_limited`, 사용자에게 쉬운 문장으로 표시 |
| TTY 필요 | persona status `tty_required`, 로그인/터미널 안내 |
| bad output | persona status `bad_output`, raw detail은 고급에만 |

최종 synthesis는 LLM에 다시 맡기지 않고 deterministic merge로 시작한다. AI 응답 품질이 낮아도 파일 구조는 안정적으로 유지해야 한다.

추가 계약:

- **동시 전송 잠금**: 한 세션 실행 중 추가 전송은 잠그거나 큐잉한다(slug `-2`/`-3` race·세션 경합 방지).
- **크레딧 소진(Claude, 2026-06-15+)**: Agent SDK 크레딧 소진은 `rate_limited` status로 분류하고 "AI 사용량이 한도에 도달했어요"처럼 쉬운 문장으로 표시한다.
- **크로스플랫폼**: 모든 adapter는 PR 4 §4 "크로스플랫폼 필수 계약"(creationflags/utf-8 인코딩/which-resolve/프로세스 트리 종료)을 그대로 따른다. 페르소나 3개 relay는 Windows 콘솔 깜빡임 표면이 PR 4보다 크다.

## 11. 테스트

Python:

- `tests/core/planning_cli/test_mentions.py`
  - Korean mention
  - English alias
  - multiple mentions
  - unknown mention ignored or user-facing warning
- `tests/core/planning_cli/test_orchestrator.py`
  - 3 persona all ok
  - 1 persona fail + 2 persona ok
  - all fail fallback
  - 순차 실행 order
  - `--save-transcript` on/off
- `tests/core/planning_cli/test_plan_json_contract.py`
  - JSON schema
  - `agents_requested`, `agents_used`, `agent_statuses`

GUI:

- mention chip 클릭 시 입력에 mention 반영
- persona status badges
- 실패 persona가 있어도 final preview 표시
- raw stderr 기본 미노출

수동 QA:

1. fake adapter 3개로 all-ok 실행.
2. fake adapter 중 mina만 timeout.
3. 실제 준비된 CLI 1개 + 나머지 미설치 상태.
4. `@지오` 단독 호출.
5. `@모두` 호출 후 최종 `plans/*.md` 확인.

## 12. 완료 정의

- 사용자는 `@클로이`, `@지오`, `@미나`, `@모두`로 persona를 부를 수 있다.
- 준비된 CLI만 best-effort로 참여한다.
- 한 CLI 실패가 전체 기획 저장 실패로 번지지 않는다.
- 원문 transcript는 opt-in일 때만 저장된다.
- GUI 기본 화면에는 모델명/CLI명보다 persona 이름이 먼저 보인다.
- CodeSpeak/patch/plan-structure 용어가 기획방 기본 화면에 나오지 않는다.
