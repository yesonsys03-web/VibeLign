# PR 3 Spec: 기획 엔진 골격 + `vib plan --template-only` + 입력 바 → 기획방 정적 전환

작성일: 2026-06-02
브랜치: `feat/vibelign-product-renew`
상위 문서: `VibeLign-코알못UX-통합기획안.md` §12 PR 3, `VibeLign-멀티AI-기획CLI-설계안.md` §4·§6·§8

## 목적

자연어 아이디어 → **결정론적 템플릿 기획안(`plans/{slug}.md`)** 까지의 엔진 골격을 만들고, GUI 입력 바에 텍스트를 입력해 전송하면 **기획방 화면으로 정적 전환**되어 사용자 메시지 + VibeLign 템플릿 응답이 보이게 한다.

PR 3의 GUI 경로는 다중 질문 UI를 만들지 않는다. `questions.py`는 엔진의 데이터 모델과 CLI/후속 채팅 흐름을 위한 골격으로 두고, GUI PR 3은 사용자의 첫 입력만으로 템플릿 기획안을 만들며 부족한 정보는 "아직 결정이 필요한 질문"에 남긴다.

이 PR은 **LLM을 0회 호출한다.** 페르소나 실제 응답은 PR 4/5다. 엔진 흐름 버그와 LLM 응답 변동성을 분리 디버깅하기 위함(통합기획안 §11).

## 상위 결정

- `vib plan` CLI는 **사용자 마케팅 면이 아니라 엔진 검증 진입점**이다(멀티AI §1). 1차 표면은 GUI 기획방.
- 최종 기획안은 **프로젝트 루트의 `plans/{slug}.md`** 에 쓴다. 이는 `vib plan-structure`가 쓰는 `.vibelign/plans/{id}.json`(= `MetaPaths.plans_dir`)과 **다른 경로**다. 혼동 주의.
- 세션 메타데이터는 `.vibelign/planning/{session_id}/`에 둔다(멀티AI §4).
- `plan-structure`는 기획방/초보 UI에 노출하지 않는다. 기존 구현은 건드리지 않는다(멀티AI §1).
- 약관 표면 없음: 이 PR은 공식 CLI를 호출하지 않으므로 §13(약관) 리스크 표면이 0이다.

## 범위

### 포함 (Python 엔진)

새 디렉터리 `vibelign/core/planning_cli/`:

| 파일 | 책임 (PR 3 범위) |
|---|---|
| `models.py` | `PlanningInput`, `PlanningResult` dataclass |
| `questions.py` | 초보자 질문 3~5개 생성 + 답변 정규화. 아이디어 짧으면 5개, 충분하면 3개. 빈 답변 허용 |
| `markdown_writer.py` | 9개 필수 섹션 Markdown 생성(아래) |
| `storage.py` | `plans/{slug}.md` 저장(루트), slug 생성, 충돌 시 `-2`/`-3`, `.vibelign/planning/{session_id}/session.json` 저장 |

새 command `vibelign/commands/vib_plan_cmd.py`:
- `run_vib_plan(args: object) -> None` (기존 패턴: `cast(Protocol, args)`, `getattr(args, "json", False)`, `clack_*`/`json.dumps`)
- 옵션(PR 3 부분집합): `[idea...]`, `--template-only`, `--output`, `--force`, `--language`, `--json`
- `--template-only`만 PR 3에서 실제 동작. 비-template 경로는 PR 4/5.

CLI 등록 `vibelign/cli/cli_command_groups.py`:
- `register_extended_commands()` 안에 `plan` 서브파서 추가
- `lazy_command("vibelign.commands.vib_plan_cmd", "run_vib_plan")`
- help 문구: "기획안 만들기"(plan-structure를 비교 대상/다음 단계로 노출 금지)

### 포함 (GUI)

- `App.tsx` `Page` 타입에 `"planning"` 추가, 조건부 렌더 + 새 `pages/PlanningRoom.tsx`
- 입력 바 전송 → App 상위에서 projectDir/prompt를 보관 → backend 계약(`create_planning_template`) 호출 → `PlanningRoom`을 첫 메시지로 진입
- 기획방 골격: 사용자 메시지 1개 + `VibeLign 정리` 템플릿 응답 1개 + `[기획안 보기]` 액션
- `기획안 보기` → backend 응답의 Markdown content를 기존 `MarkdownPane`(`components/docs/MarkdownPane.tsx`)로 렌더

### GUI → backend 계약

PR 3은 새 Tauri command `create_planning_template`을 추가한다. GUI가 Python 내부 모듈을 직접 알지 않게 하고, command는 `vib plan --template-only --json`과 같은 엔진 경로를 호출한다.

요청:

```json
{
  "projectDir": "/abs/project",
  "prompt": "예약 앱 만들고 싶어",
  "language": "auto"
}
```

성공 응답:

```json
{
  "ok": true,
  "outputPath": "plans/reservation-app.md",
  "absoluteOutputPath": "/abs/project/plans/reservation-app.md",
  "markdown": "# 예약 앱\n...",
  "fallbackReason": "template_only",
  "sessionId": "plan_20260602_abc123"
}
```

실패 응답:

```json
{
  "ok": false,
  "errorCode": "PLANNING_TEMPLATE_FAILED",
  "message": "기획안을 만들지 못했어요.",
  "details": "developer-only detail"
}
```

계약:

- `projectDir`은 절대 경로여야 한다.
- `outputPath`는 사용자 표시용 project-relative path다.
- `markdown`은 `[기획안 보기]`에서 바로 렌더할 수 있는 최종 content다.
- raw stdout/stderr는 기본 UI에 노출하지 않고 실패 상세 영역에만 둔다.
- command가 실패해도 LLM 호출 fallback을 시도하지 않는다. PR 3은 template-only다.
- **PR 4/5는 이 command를 확장한다**(`cli`/`adapter`/`personaId`/`llmStatus` 필드 추가). 새 병렬 GUI 경로(raw `run_vib(["plan",...])` 직접 호출)를 만들지 않는다.
- `fallbackReason` 어휘는 PR 3/4/5가 공유한다: `template_only`(template-only 요청) · `cli_unavailable_template_only`(CLI 시도 실패→fallback) · `null`(LLM 성공, PR 4+).

### 제외

- LLM CLI adapter / 페르소나 실제 응답 (PR 4/5)
- `@클로이`·`@지오`·`@미나` mention 라우팅 (PR 5)
- 페르소나 아바타 (PR 5/9)
- `--review-only`, `--save-transcript`, `--rounds`, `--agents`, `--cli` (PR 4/5)
- Home 재구성 (PR 6)

## 최종 Markdown 필수 섹션 (9개)

```markdown
# {프로젝트 또는 기능 이름}
## 한 줄 목표
## 만들고 싶은 이유
## 대상 사용자
## 핵심 기능
## 화면 또는 사용 흐름
## 제외할 것
## 아직 결정이 필요한 질문
## 구현 전에 AI가 알아야 할 맥락
## 다음 단계
```

빈 답변/모르는 항목은 만들어내지 말고 "아직 결정이 필요한 질문"으로 남긴다(멀티AI §7).

## 생성 파일 계약

```text
plans/{slug}.md                                  # 프로젝트 루트 (vib plan-structure와 구분!)
.vibelign/planning/{session_id}/session.json     # 세션 메타데이터
```

- slug: 아이디어에서 생성. `--output` 없고 동일 slug 존재 시 `plans/{slug}-2.md`. `--output` 지정 + 존재 시 실패, `--force`면 덮어쓰기(멀티AI §4).
- 생성 문서에 `CodeSpeak`, `patch`, `target_anchor`가 들어가면 실패(멀티AI §9, §12-7).

## 현재 코드 기준 (구현 근거)

| 사실 | 위치 |
|---|---|
| 서브커맨드 등록 패턴 `p.set_defaults(func=lazy_command("mod","fn"))` | `cli_command_groups.py:717-720`(plan-structure 예시) |
| `register_extended_commands(sub, ...)` 호출 | `cli/vib_cli.py:88` |
| `lazy_command(module, func)` 구현 | `cli/cli_base.py:85-94` |
| 기존 run 함수 패턴(`args: object` cast, `getattr(args,"json")`, `clack_*`/`json.dumps`) | `vib_plan_structure_cmd.py:40-92` / `vib_checkpoint_cmd.py:96-100` |
| `resolve_project_root(start)` | `core/project_root.py:21-26` |
| `MetaPaths(root)`, `ensure_vibelign_dirs()`; `plans_dir = .vibelign/plans/`(plan-structure용) | `core/meta_paths.py:11-12,39-40,100-106` |
| GUI 라우팅: 상태 기반 `page` useState + 조건부 렌더(react-router 없음) | `App.tsx:60,65,150-202` |
| Onboarding 완료 콜백 `onComplete(dir, key)` | `Onboarding.tsx:56-60`, `App.tsx:143` |
| 마크다운 렌더 재사용 `<MarkdownPane content containerRef />` | `components/docs/MarkdownPane.tsx:7-10` |

> **주의**: `MetaPaths.plans_dir`은 `.vibelign/plans/`(plan-structure 전용). `vib plan`은 `resolve_project_root(...)/"plans"`(루트)에 쓴다. `storage.py`가 이 경로를 직접 계산한다.

## 동작 / 시나리오

| 상황 | PR 3 동작 |
|---|---|
| 입력 바에 "예약 앱" 입력 후 전송 | `create_planning_template` 호출 → 기획방으로 정적 전환, 사용자 메시지 + 템플릿 응답 표시 |
| `vib plan "예약 앱" --template-only` | `plans/{slug}.md` 생성, 9개 섹션 포함, LLM 0회 |
| 준비된 CLI 없음 | template로 정상 완료(실패 아님) |
| `--output` 기존 파일 | 실패. `--force`면 덮어쓰기 |
| 부족한 정보가 많음 | 실패 없이 "아직 결정이 필요한 질문"으로 수집 |
| `--json` | `ok`, `output_path`, `fallback_reason` 출력 |

## 상태와 에러

- `vib plan`은 `.vibelign/plans/*.json`(plan-structure state)에 의존하지 않는다(멀티AI §9).
- CLI 미설치/미로그인은 PR 3에서 무관(LLM 호출 없음). template 경로만.
- 기획방 UI에 Markdown 원문은 기본 노출하지 않고 `[기획안 보기]` 뒤에 둔다(멀티AI §2).
- **프롬프트 정규화**: 전송 텍스트는 trim하고, 공백만이면 전송 비활성(PR 1과 동일), 길이 상한(예: 4000자) 초과 시 잘라내고 안내한다. 빈/공백 프롬프트가 엔진으로 넘어가지 않는다.
- **slug 파일명 안전성(Windows/Mac)**: slug는 Windows 금지문자(`<>:"/\|?*`)·예약어(CON/PRN/AUX/NUL)·후행 점/공백을 제거하고, 결과가 비면 `plan`으로 폴백한다. 기존 `core/docs_visualizer._slugify`를 재사용하되 `codespeak._ko_to_slug`(PR 7 deprecate 대상)에는 결합하지 않는다.
- **경로**: 프로젝트 경로에 공백·유니코드가 있어도 `Path`로 처리한다. Windows 긴 경로(260자) 한계를 인지한다.
- **GUI 재진입**: 기획방에서 뒤로 갔다 다시 전송하면 이전 세션 상태를 초기화한다(중복 세션/메시지 잔존 금지).
- **동시 전송 잠금**: 생성 중에는 추가 전송을 잠그거나 큐잉해 slug `-2`/`-3` race와 세션 경합을 막는다.

## 구현 메모

- `storage.py`: `root = resolve_project_root(Path.cwd())`; `plans = root / "plans"`; `plans.mkdir(parents=True, exist_ok=True)`. 세션 메타는 `MetaPaths(root).vibelign_dir / "planning" / session_id`.
- `vib_plan_cmd.py`: plan-structure cmd(`:40-92`) 구조 미러 — args cast, 디렉터리 준비, questions → markdown_writer → storage, `clack_*` 출력, `--json` 분기.
- CLI 등록: `cli_command_groups.py`의 plan-structure 블록(`:691-721`) 바로 위/아래에 동일 패턴으로 `plan` 추가. help는 "기획안 만들기".
- GUI 전환: `App.tsx:60` `Page`에 `"planning"` 추가. 입력 바 전송 핸들러가 prompt 텍스트와 projectDir을 App state로 올리고 `create_planning_template`을 호출한 뒤 `setPage("planning")`. `PlanningRoom`은 prompt와 backend 응답을 받아 사용자 버블 + 템플릿 응답을 렌더. `기획안 보기`는 응답의 `markdown`을 `MarkdownPane`으로 렌더.
- Rust/Tauri command: `create_planning_template`은 projectDir에서 `vib plan --template-only --json` 동등 경로를 실행하고 stdout JSON을 파싱한다. response shape는 위 계약을 따른다.
- **새 파일은 명시된 것만 생성**(CLAUDE.md 규칙). `App.tsx`·`cli_command_groups.py`는 최소 추가만, 전체 재작성 금지.

## 자동 테스트

Python:

```text
tests/core/planning_cli/test_markdown_writer.py
tests/core/planning_cli/test_storage.py
tests/core/planning_cli/test_questions.py
tests/cli/test_vib_plan_cmd.py
```

1. 준비된 CLI 없이 `plans/{slug}.md` 생성, 9개 섹션 모두 존재.
2. slug 충돌 시 `-2`/`-3` 생성. `--output` 존재 시 실패, `--force` 시 덮어쓰기.
3. 아이디어 길이에 따라 질문 3개/5개. 빈 답변 허용.
4. `vib plan "예약 앱" --template-only`가 dispatch되어 파일 생성.
5. `--json` 출력에 `ok`/`output_path`/`fallback_reason` 포함.
6. 생성 문서에 `CodeSpeak`/`patch`/`target_anchor` 없음.
7. `vib plan`이 `.vibelign/plans/*.json`/active planning state에 의존하지 않음.
8. `create_planning_template` 성공 응답이 `ok`, `outputPath`, `absoluteOutputPath`, `markdown`, `fallbackReason`, `sessionId`를 반환.
9. `create_planning_template` 실패 응답이 `ok=false`, `errorCode`, 사용자용 `message`, 개발자용 `details`를 반환.

GUI(vitest):

```text
vibelign-gui/src/pages/__tests__/PlanningRoom.static.test.tsx
```

10. 입력 텍스트 전송 → `create_planning_template` 호출 → 기획방 렌더, 사용자 메시지 + 템플릿 응답 표시.
11. `기획안 보기` 클릭 → backend 응답의 Markdown content를 MarkdownPane로 렌더.
12. 기본 화면에 모델 선택 드롭다운/Markdown 원문 미노출.
13. 기획방에 `plan-structure` 노출 안 됨.

## 수동 QA

```text
tmpdir=$(mktemp -d); cd "$tmpdir"; git init
python -m vibelign.cli.vib_cli plan "동네 카페 예약 앱을 만들고 싶어" --template-only
ls plans            # plans/*.md 존재(루트), .vibelign/plans/ 아님
sed -n '1,160p' plans/*.md
```

통과 기준: Markdown 문법 입력 요구 없음 · `plans/*.md` 생성(루트) · 9개 섹션 · CLI 없어도 실패 안 함 · `patch`/`CodeSpeak`/`target_anchor` 없음.

GUI: dev 실행 → 입력 바 "예약 앱 만들고 싶어" 전송 → `create_planning_template` 성공 → 기획방 전환 → 템플릿 응답 + `[기획안 보기]`.

## 완료 정의

1. `vib plan --template-only`가 준비된 CLI 없이 `plans/{slug}.md`(루트)를 만들고 9개 섹션을 채운다.
2. GUI 입력 바 전송 시 `create_planning_template`을 통해 실제 `plans/{slug}.md`가 생성된다.
3. 기획방으로 정적 전환되어 사용자 메시지 + VibeLign 템플릿 응답이 보인다.
4. `기획안 보기`가 backend 응답의 Markdown content를 기존 MarkdownPane로 렌더한다.
5. LLM은 0회 호출된다. mention/페르소나 응답/아바타는 없다(PR 4/5 분리).
6. 생성 문서에 CodeSpeak/patch/target_anchor가 없고, `plan-structure` state에 의존하지 않는다.
7. `plans/{slug}.md`(루트)와 `.vibelign/plans/`(plan-structure)가 명확히 구분된다.
