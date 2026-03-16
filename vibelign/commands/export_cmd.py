from pathlib import Path
from vibelign.core.ai_dev_system import AI_DEV_SYSTEM_CONTENT


from vibelign.terminal_render import cli_print
print = cli_print

AGENTS_MD_CONTENT = """\
# AGENTS.md

This file is automatically read by OpenCode, Claude Code, and other AI coding tools that support AGENTS.md.

**Before making any changes to this project, read and follow `AI_DEV_SYSTEM_SINGLE_FILE.md`.**

## Core Rules

- Apply the smallest safe patch possible
- Do not rewrite entire files unless explicitly requested
- Edit only the file that is actually relevant
- Do not modify unrelated modules
- Respect anchor boundaries (`ANCHOR: NAME_START` / `ANCHOR: NAME_END`)
- Keep entry files (main.py, index.js, etc.) small and focused

## Required Workflow

```bash
vib doctor --strict
vib anchor
vib patch "<your request>"
# apply the AI edit
vib explain --write-report
vib guard --strict --write-report
```

## Project Map

Before modifying any file, read `.vibelign/project_map.json` to understand:
- File categories (entry, ui, service, core)
- Anchor locations per file (`anchor_index`)
- File dependencies via `.vibelign/anchor_meta.json` (`@CONNECTS`)

## Full Rules

See `AI_DEV_SYSTEM_SINGLE_FILE.md` for the complete ruleset.
"""

_RULES = """\
# VibeLign 규칙 요약

> 전체 규칙은 프로젝트 루트의 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 읽으세요.

## 핵심 원칙

1. **가능한 가장 작은 패치를 적용하세요**
2. **요청한 파일만 수정하세요** — 연관 없는 파일은 절대 건드리지 마세요
3. **파일 전체를 재작성하지 마세요** — 명시적 요청이 없는 한 금지
4. **앵커 경계를 지키세요** — `ANCHOR: NAME_START` ~ `ANCHOR: NAME_END` 사이만 수정
5. **진입 파일을 작게 유지하세요** — main.py, index.js 등에 비즈니스 로직을 넣지 마세요
6. **새 파일을 임의로 생성하지 마세요** — 명시적 요청이 있을 때만 생성
7. **임포트 구조를 바꾸지 마세요** — 명시적 허락 없이 변경 금지
8. **코드맵을 먼저 읽으세요** — `.vibelign/project_map.json`에서 파일 구조와 앵커 위치를 확인
"""

_SETUP = """\
# VibeLign 작업 흐름

## AI 작업 전 (순서대로 실행)

**1단계 — 상태 확인**
```
vib doctor --strict
```
문제가 있으면 먼저 해결하세요.

**2단계 — 안전 구역 설정**
```
vib anchor
```
앵커가 없는 파일에 앵커를 자동으로 삽입합니다.

**3단계 — 현재 상태 저장 (세이브 포인트)**
```
vib checkpoint "작업 설명"
```
예: `vib checkpoint "로그인 기능 추가 전"`

**4단계 — 패치 요청 준비**
```
vib patch "원하는 변경사항"
```
AI에게 전달할 안전한 프롬프트가 VIBELIGN_PATCH_REQUEST.md에 생성됩니다.

---

## AI 작업 후 (반드시 확인)

**5단계 — 변경사항 확인**
```
vib explain --write-report
```

**6단계 — 위험도 체크**
```
vib guard --strict
```

**문제 없으면** → 저장
```
vib checkpoint "완료: 작업 설명"
```

**문제 있으면** → 되돌리기
```
vib undo
```
"""

_PROMPT_TEMPLATE = """\
# AI 요청 템플릿

아래 내용을 AI 툴에 복사해서 붙여넣고, [ ] 안의 내용을 채운 뒤 전송하세요.

---

`AI_DEV_SYSTEM_SINGLE_FILE.md`의 규칙을 모두 따르세요.

## 요청 내용

[여기에 원하는 변경사항을 구체적으로 적으세요]

예시:
- "login.py 파일의 오류 메시지를 한국어로 바꿔주세요"
- "signup 함수에 이메일 형식 검사를 추가해주세요"

## 수정할 파일

[파일 경로]
예: src/auth/login.py

## 수정할 앵커 (있으면)

[앵커 이름]
예: LOGIN_VALIDATOR

## 반드시 지킬 규칙

- 위에 지정한 파일과 앵커만 수정하세요
- 다른 파일은 절대 건드리지 마세요
- 파일 전체를 다시 쓰지 마세요
- ANCHOR 마커(ANCHOR: NAME_START / NAME_END)를 삭제하지 마세요
- 임포트 구조를 바꾸지 마세요

## 예상 결과

[수정 후 어떻게 동작해야 하는지 적으세요]
예: "로그인 실패 시 '비밀번호가 틀렸습니다'라는 메시지가 나와야 합니다"
"""

_CURSOR_RULES = """\
# VibeLign 규칙 요약 (Cursor용)

> 이 내용을 `.cursorrules` 파일에 복사하거나
> Cursor → Settings → Rules for AI 항목에 붙여넣으면
> 매번 입력하지 않아도 자동으로 적용됩니다.

> 전체 규칙은 프로젝트 루트의 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 읽으세요.

## 핵심 원칙

1. **가능한 가장 작은 패치를 적용하세요**
2. **요청한 파일만 수정하세요** — 연관 없는 파일은 절대 건드리지 마세요
3. **파일 전체를 재작성하지 마세요** — 명시적 요청이 없는 한 금지
4. **앵커 경계를 지키세요** — `ANCHOR: NAME_START` ~ `ANCHOR: NAME_END` 사이만 수정
5. **진입 파일을 작게 유지하세요** — main.py, index.js 등에 비즈니스 로직을 넣지 마세요
6. **새 파일을 임의로 생성하지 마세요** — 명시적 요청이 있을 때만 생성
7. **임포트 구조를 바꾸지 마세요** — 명시적 허락 없이 변경 금지
8. **코드맵을 먼저 읽으세요** — `.vibelign/project_map.json`에서 파일 구조와 앵커 위치를 확인
"""

_ANTIGRAVITY_TASK = """\
# 작업 요청서

> AI에게 요청할 때 이 파일을 채워서 전달하세요.

## 작업 내용

[AI에게 요청할 변경사항을 한 문장으로 적으세요]

## 수정 대상 파일

[파일 경로]

## 수정 대상 앵커

[앵커 이름 — 없으면 수정할 함수/섹션 이름을 적으세요]

## 제약 조건

- 이 파일과 앵커만 수정
- 파일 전체 재작성 금지
- 다른 파일 수정 금지
- 임포트 구조 유지
- ANCHOR 마커 삭제 금지

## 완료 기준

[어떻게 되어야 작업이 완료된 건지 적으세요]
"""

_ANTIGRAVITY_CHECKLIST = """\
# AI 작업 완료 체크리스트

AI가 코드를 수정한 뒤 반드시 아래 항목을 확인하세요.

## 파일 범위 확인
- [ ] 요청한 파일만 수정되었나요?
- [ ] 요청하지 않은 파일이 변경되지 않았나요?
- [ ] 파일 전체가 재작성되지 않았나요? (줄 수가 크게 늘었으면 의심)

## 앵커 확인
- [ ] ANCHOR: NAME_START / NAME_END 마커가 그대로 있나요?
- [ ] 앵커 안의 내용만 수정되었나요?

## 구조 확인
- [ ] 진입 파일(main.py, index.js 등)이 크게 늘지 않았나요?
- [ ] 새 파일이 무단으로 생성되지 않았나요?
- [ ] 임포트 구조가 바뀌지 않았나요?

## 최종
- [ ] `vib guard --strict` 실행 → 이상 없음 확인
- [ ] 이상 있으면: `vib undo` 로 되돌리기
- [ ] 이상 없으면: `vib checkpoint "완료: 작업 설명"`
"""

_ANTIGRAVITY_SETUP = """\
# VibeLign + Antigravity 작업 흐름

**1단계 — 상태 확인**
```
vib doctor --strict
```

**2단계 — 안전 구역 설정**
```
vib anchor
```

**3단계 — 현재 상태 저장**
```
vib checkpoint "작업 설명"
```

**4단계 — 작업 요청서 작성**
TASK_ARTIFACT.md를 채워서 AI에게 전달하세요.

**5단계 — 작업 완료 후 체크**
VERIFICATION_CHECKLIST.md 항목을 순서대로 확인하세요.

**6단계 — vib로 최종 검증**
```
vib explain --write-report
vib guard --strict
```

**문제 없으면** → `vib checkpoint "완료"`
**문제 있으면** → `vib undo`
"""

_VIBELIGN_CURSOR_MARKER = "# --- VibeLign Rules (vibelign export cursor) ---"


def _write_cursorrules(root) -> str:
    """.cursorrules 파일에 VibeLign 규칙을 씁니다.
    반환값: 'created' | 'appended' | 'skipped'
    """
    cursorrules_path = root / ".cursorrules"
    if cursorrules_path.exists():
        existing = cursorrules_path.read_text(encoding="utf-8")
        if _VIBELIGN_CURSOR_MARKER in existing:
            return "skipped"
        append_content = f"\n\n{_VIBELIGN_CURSOR_MARKER}\n{_CURSOR_RULES}\n"
        cursorrules_path.write_text(existing + append_content, encoding="utf-8")
        return "appended"
    else:
        cursorrules_path.write_text(
            f"{_VIBELIGN_CURSOR_MARKER}\n{_CURSOR_RULES}\n", encoding="utf-8"
        )
        return "created"


TEMPLATES = {
    "claude": {
        "RULES.md": _RULES,
        "SETUP.md": _SETUP,
        "PROMPT_TEMPLATE.md": _PROMPT_TEMPLATE,
    },
    "opencode": {
        "RULES.md": _RULES,
        "SETUP.md": _SETUP,
        "PROMPT_TEMPLATE.md": _PROMPT_TEMPLATE,
    },
    "cursor": {
        "RULES.md": _CURSOR_RULES,
        "SETUP.md": _SETUP,
        "PROMPT_TEMPLATE.md": _PROMPT_TEMPLATE,
    },
    "antigravity": {
        "TASK_ARTIFACT.md": _ANTIGRAVITY_TASK,
        "VERIFICATION_CHECKLIST.md": _ANTIGRAVITY_CHECKLIST,
        "SETUP.md": _ANTIGRAVITY_SETUP,
    },
}


def run_export(args):
    root = Path.cwd()

    ai_dev_path = root / "AI_DEV_SYSTEM_SINGLE_FILE.md"
    if ai_dev_path.exists():
        print(f"경고: 기존 {ai_dev_path.name} 파일을 덮어씁니다")
    ai_dev_path.write_text(AI_DEV_SYSTEM_CONTENT, encoding="utf-8")
    print(f"{ai_dev_path.name} 생성 완료")

    agents_path = root / "AGENTS.md"
    if agents_path.exists():
        print(f"경고: 기존 {agents_path.name} 파일을 덮어씁니다")
    agents_path.write_text(AGENTS_MD_CONTENT, encoding="utf-8")
    print(f"{agents_path.name} 생성 완료")

    export_root = root / "vibelign_exports" / args.tool
    already_exists = export_root.exists()
    export_root.mkdir(parents=True, exist_ok=True)
    if already_exists:
        print(f"경고: {export_root.relative_to(root)}의 기존 파일을 덮어씁니다")
    for name, content in TEMPLATES[args.tool].items():
        (export_root / name).write_text(content, encoding="utf-8")
    (export_root / "README.md").write_text(
        f"# VibeLign 내보내기: {args.tool}\n\n프로젝트 루트의 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 주요 규칙 파일로 유지하세요.\n",
        encoding="utf-8",
    )
    print(f"{export_root} 생성 완료")

    if args.tool == "cursor":
        result = _write_cursorrules(root)
        if result == "created":
            print(".cursorrules 생성 완료")
        elif result == "appended":
            print("경고: 기존 .cursorrules 파일이 있습니다.")
            print("      덮어쓰지 않고 VibeLign 규칙을 뒤에 추가했습니다.")
        else:
            print("참고: .cursorrules에 이미 VibeLign 규칙이 있습니다 (건너뜀)")
