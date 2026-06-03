# PR 4 세부 스펙: 첫 CLI 페르소나 스파이크 + 실제 응답

## 1. 목적

PR 4의 목적은 기획방에 **공식 CLI 기반 LLM 응답 1개**를 실제로 붙여서 dogfood 가능한 최소 루프를 여는 것이다.

단, 첫 구현은 "무조건 agy"가 아니라 **스파이크로 첫 어댑터를 확정한 뒤 하나만 구현**한다. 현재 리스크 기준은 다음과 같다.

| 후보 | 페르소나 | 명령 | 판정 |
|---|---|---|---|
| Codex | 지오 | `codex exec` | 가장 안전한 기본 후보. 비대화형 실행과 ChatGPT 로그인 지원이 공식 문서화되어 있다. |
| Claude Code | 클로이 | `claude -p` | 비대화형 실행은 가능하지만 2026-06-15부터 Agent SDK 크레딧 차감 고지가 필요하다. |
| Antigravity | 미나 | `agy -p` | 공식 Antigravity CLI 문서의 비대화형 경로다. 토큰 추출/비공식 backend 접근 없이 공식 바이너리만 실행하는지 검증한다. |

결론: **PR 4 시작 시 실제 로컬 probe를 돌려 Codex를 기본 1순위로 두되, `agy -p`가 로컬에서 안정적으로 확인되고 사용자가 dogfood 우선 결정을 유지하면 미나/agy로 시작할 수 있다.** 어떤 경우에도 PR 4는 한 페르소나만 연결한다.

## 2. PR 4 범위

포함:

- `vibelign/core/planning_cli/cli_adapters.py`
  - CLI runner abstraction
  - candidate probe
  - 첫 adapter 1개
- `vibelign/core/planning_cli/personas.py`
  - PR 4에서 쓰는 단일 persona 정의
- `vibelign/core/planning_cli/engine.py`
  - template-only 결과를 실제 CLI 응답으로 보강
  - CLI 실패 시 template-only fallback 유지
- `vibelign/commands/vib_plan_cmd.py`
  - `vib plan "..." --json`
  - `--cli auto|codex|claude|agy` (단일 CLI 선택; PR 5에서 `--cli a,b` 목록으로 일반화)
  - `--llm-timeout-seconds 300`
- GUI
  - PR 3의 기획방에서 단일 페르소나 응답 상태 표시
  - 실패 시 "기본 기획안으로 저장했어요" fallback 표시
- README/README.ko
  - 실제 LLM relay adapter를 넣는 PR에서 "Third-Party AI CLI 고지"를 추가하거나 기존 고지를 보강한다.

제외:

- 3 페르소나 동시 또는 순차 오케스트레이션
- mention 라우팅
- persona 캐릭터 커스터마이즈
- TUI 자동 조작
- OAuth 토큰/세션 파일 읽기
- API 키 중앙 저장 또는 계정 풀링

## 3. 스파이크 절차

PR 4 구현 첫 커밋 전에 다음 probe를 문서화한다.

1. `shutil.which("codex")`, `shutil.which("claude")`, `shutil.which("agy")`로 설치 여부만 확인한다.
2. 각 CLI의 version/help/probe 명령을 **짧은 timeout**으로 실행한다.
3. 실제 LLM 호출 probe는 명시 opt-in 환경변수 또는 수동 QA에서만 실행한다.
4. TTY가 필요한 후보는 PR 4에서 탈락시킨다.
5. probe 결과를 PR description에 남긴다.
6. 실제 로컬 probe는 PR 작성자가 접근 가능한 OS에서 수행한다. macOS에서 시작해도 되지만, Windows는 fake runner/단위 테스트로 subprocess 계약을 고정하고 release 전 수동 QA 또는 CI 환경에서 별도 확인한다. 특히 `agy -p`의 stdout/stderr, cwd, permission prompt 동작은 OS별로 다를 수 있고(Windows는 WSL 경유 가능성 포함), 한 OS에서 확인한 결과를 모든 OS 보장처럼 문서화하지 않는다.

Probe 결과가 모두 불안정하면 PR 4는 Codex adapter skeleton + fake runner tests까지만 머지하고 실제 호출은 막는다. 이 경우 dogfood 시작점은 다음 PR로 밀린다.

## 4. Adapter Contract

```python
class PlanningCliRunner(Protocol):
    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    ) -> PlanningCliResult: ...
```

```python
@dataclass(frozen=True)
class PlanningCliResult:
    status: Literal[
        "ok",
        "not_installed",
        "not_logged_in",
        "timeout",
        "rate_limited",
        "tty_required",
        "bad_output",
        "terms_blocked",
        "process_error",
    ]
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
```

규칙:

- `subprocess.run(..., input=..., text=True, capture_output=True, timeout=..., encoding="utf-8", errors="replace", creationflags=WINDOWS_SUBPROCESS_FLAGS)` 기반으로 시작한다(아래 크로스플랫폼 필수 계약 참조).
- timeout은 기본 300초, 테스트에서는 1초 이하로 낮춘다.
- stdout/stderr는 내부 결과에는 남기되 GUI 기본 화면에는 원문 전체를 노출하지 않는다.
- status 분류는 stderr 문자열에 과하게 의존하지 말고, exit code + 대표 패턴 + timeout 예외로 보수적으로 판단한다.
- LLM 응답이 비어 있거나 Markdown으로 쓸 수 없으면 `bad_output`으로 처리한다.

### 크로스플랫폼 필수 계약 (Windows/Mac)

- **콘솔 깜빡임 방지(Windows)**: 모든 Python subprocess는 `creationflags=WINDOWS_SUBPROCESS_FLAGS`(`vibelign/core/structure_policy.py`)를 넘긴다. `create_planning_template`이 Rust에서 `vib`/CLI를 spawn할 때는 `CREATE_NO_WINDOW`(0x0800_0000, `vib_path.rs`/`git_status.rs` 등 기존 패턴)를 적용한다. relay는 페르소나마다 프로세스를 띄우므로 미적용 시 콘솔 창 다발 깜빡임(v2.2.24에서 고친 회귀).
- **한글 인코딩**: stdout/stderr 캡처는 `encoding="utf-8", errors="replace"`를 명시한다. Windows 기본 인코딩(cp949)이면 한글 프롬프트/응답이 깨진다.
- **실행 파일 해석(Windows)**: `shutil.which("claude"|"codex"|"agy")`로 **resolve된 절대 경로**를 subprocess에 넘긴다. `["claude", ...]` 직접 호출은 Windows `.cmd`/`.ps1` 셰임 PATHEXT 해석에 실패할 수 있다.
- **timeout 시 프로세스 트리 종료**: timeout 발생 시 자식 프로세스(셰임→실제 프로세스)까지 종료해 Windows에서 좀비가 남지 않게 한다.
- **부분 출력 처리**: 부분 stdout만 받고 timeout/실패하면 `timeout`/`bad_output`으로 분류하고 부분 Markdown을 최종 파일로 저장하지 않는다.

## 5. 명령 매핑

PR 4에서 확정한 첫 adapter만 활성화한다.

Codex 후보:

```bash
codex exec "<prompt>"
```

Claude 후보:

```bash
claude -p "<prompt>"
```

Antigravity 후보:

```bash
agy -p "<prompt>"
```

공식 예시는 `agy -p "..." --cwd $(pwd)` 형태다. Python subprocess는 `cwd=root`를 넘기므로 기본 구현은 `agy -p "<prompt>"`를 사용하고, OS별 cwd 문제가 보이면 `--cwd` 추가를 별도 패치로 검증한다.

## 6. Prompt Contract

입력:

- 사용자 자연어 아이디어
- PR 3 template-only 기획안 초안
- 프로젝트 루트 이름과 간단한 요약

금지:

- 프로젝트 전체 소스 코드 전송
- `.env`, key, token, session file 전송
- CodeSpeak, patch, target_anchor 지시문 생성

LLM에게 요구할 출력:

- 초보자가 읽을 수 있는 기획 보강
- 구현자가 바로 쪼갤 수 있는 요구사항
- 불확실한 내용은 "아직 결정이 필요한 질문"에 남김
- 과한 기능 추가 금지

## 7. CLI/GUI 결과 Contract

`vib plan "..." --json` 성공 예:

```json
{
  "ok": true,
  "session_id": "plan_20260602_abc123",
  "output_path": "plans/reservation-app.md",
  "adapter": "codex",
  "persona_id": "gio",
  "llm_status": "ok",
  "fallback_reason": null
}
```

fallback 성공 예:

```json
{
  "ok": true,
  "session_id": "plan_20260602_abc123",
  "output_path": "plans/reservation-app.md",
  "adapter": "codex",
  "persona_id": "gio",
  "llm_status": "not_logged_in",
  "fallback_reason": "cli_unavailable_template_only"
}
```

CLI 실패가 있어도 Markdown 저장 자체가 성공하면 `ok=true`다. 파일 저장 실패만 `ok=false`로 본다.

위 `vib plan --json` 출력은 **CLI 레이어**(snake_case)다.

**GUI 경로(PR 3 command 확장)**: GUI는 PR 3에서 만든 `create_planning_template` Tauri command을 **그대로 확장해서 쓴다**. 새 병렬 경로(raw `run_vib(["plan",...])` 직접 호출)를 만들지 않는다. PR 4는 이 command에 다음을 추가한다.

- 요청: `cli`(선택, `auto|codex|claude|agy`)
- 성공 응답(camelCase): `adapter`, `personaId`, `llmStatus`, `fallbackReason`

command 내부는 여전히 `vib plan ... --json`(snake_case) 엔진을 호출하고 GUI 노출용 camelCase로 매핑한다.

**`fallback_reason` 어휘(PR 3/4/5 공유 고정)**: `null`(LLM 성공) · `template_only`(`--template-only` 요청) · `cli_unavailable_template_only`(CLI 시도했으나 미설치/미로그인/실패로 template fallback).

## 8. UX Copy

성공:

```text
지오가 기획안을 한 번 검토했어요. plans/reservation-app.md에 저장했어요.
```

fallback:

```text
AI 연결은 아직 준비되지 않았지만, 기본 기획안은 저장했어요.
```

Claude credit 고지:

```text
Claude를 연결하면 Claude 계정의 Agent SDK 크레딧이 사용될 수 있어요.
```

Antigravity 고지:

```text
Antigravity 연결은 공식 `agy -p` CLI를 실행해 응답만 받아와요. VibeLign은 토큰/세션 파일을 읽거나 비공식 backend를 호출하지 않아요.
```

## 9. 테스트

Python:

- `tests/core/planning_cli/test_cli_adapters.py`
  - fake runner `ok`
  - `not_installed`
  - `not_logged_in`
  - `timeout`
  - `tty_required`
  - `bad_output`
  - 토큰/세션 파일 경로를 읽지 않는지 monkeypatch로 검증
- `tests/core/planning_cli/test_plan_engine_pr4.py`
  - CLI 성공 시 Markdown에 persona review 반영
  - CLI 실패 시 template-only fallback 저장
  - `--json` schema 안정성

GUI:

- `vibelign-gui/src/**/*.test.tsx`
  - 단일 페르소나 응답 상태 표시
  - fallback 메시지 표시
  - raw stderr 기본 미노출

수동 QA:

1. CLI 미설치 환경에서 기획안 저장.
2. CLI 설치/미로그인 환경에서 fallback 저장.
3. 준비된 첫 CLI에서 실제 짧은 프롬프트 1회 실행.
4. timeout을 1초로 낮춰 timeout fallback 확인.

## 10. 완료 정의

- PR 4는 한 페르소나만 실제 CLI 응답을 붙인다.
- 첫 adapter 선택 사유가 PR description에 남아 있다.
- official binary subprocess relay만 사용한다.
- 인증/토큰/세션 파일을 읽지 않는다.
- 앞선 페르소나 응답이 다음 페르소나 검토 맥락으로 전달될 수 있음을 고지한다.
- 원문 transcript는 `--save-transcript` opt-in일 때만 저장한다.
- CLI 응답은 사용자의 기획안 생성에만 쓰고 경쟁 모델 학습·fine-tuning·평가 데이터셋으로 재사용하지 않는다.
- 실패해도 `plans/*.md` 저장 루프는 깨지지 않는다.
- README/README.ko의 Third-Party AI CLI 고지가 LLM relay를 커버한다. 아직 없다면 실제 adapter PR에서 추가하고, 이미 있다면 중복 없이 보강한다.
