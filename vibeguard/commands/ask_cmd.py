from pathlib import Path

MAX_LINES = 300  # 너무 긴 파일은 앞부분만 사용


def _build_prompt(rel_path: str, content: str, line_count: int, question: str | None) -> str:
    truncated = line_count > MAX_LINES
    display_content = "\n".join(content.splitlines()[:MAX_LINES])

    specific_q = f"\n특히 이 부분이 궁금합니다: {question}\n" if question else ""
    truncate_note = f"\n(파일이 길어서 앞 {MAX_LINES}줄만 포함했습니다. 전체 줄 수: {line_count}줄)\n" if truncated else ""

    suffix = Path(rel_path).suffix.lstrip(".") or "text"

    return f"""\
다음 파일을 코딩을 전혀 모르는 사람도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.
{specific_q}
파일명: {rel_path}
줄 수: {line_count}줄{truncate_note}
내용:
```{suffix}
{display_content}
```

다음 항목으로 설명해주세요:

1. 이 파일이 하는 일은 무엇인가요? (한 줄로 요약)
2. 주요 기능을 쉬운 말로 설명해주세요. (코드를 모르는 사람 기준)
3. 다른 파일과 어떻게 연결되나요?
4. AI가 이 파일을 수정할 때 주의해야 할 점이 있나요?
"""


def run_ask(args):
    root = Path.cwd()
    target_input = args.file

    # 파일 경로 확인
    target_path = Path(target_input)
    if not target_path.is_absolute():
        target_path = root / target_path

    if not target_path.exists():
        print(f"파일을 찾을 수 없습니다: {target_input}")
        print("파일명과 경로를 다시 확인하세요.")
        return

    try:
        rel = str(target_path.relative_to(root))
    except ValueError:
        rel = target_input

    # 파일 읽기
    try:
        content = target_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"파일 읽기 실패: {e}")
        return

    line_count = len(content.splitlines())
    question = " ".join(args.question) if args.question else None

    prompt = _build_prompt(rel, content, line_count, question)

    # --write: 파일로 저장
    if args.write:
        out = root / "VIBEGUARD_ASK.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        out.write_text(prompt, encoding="utf-8")
        print(f"{out.name}에 저장했습니다.")
        print()
        print("이 파일 내용을 복사해서 AI 툴(OpenCode, Claude 등)에 붙여넣으세요.")
    else:
        print("=" * 60)
        print("  아래 내용을 복사해서 AI 툴에 붙여넣으세요")
        print("=" * 60)
        print()
        print(prompt)
        print()
        print("파일로 저장하려면: vibeguard ask " + target_input + " --write")
