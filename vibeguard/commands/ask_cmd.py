import os
import json
import urllib.request
from pathlib import Path

MAX_LINES = 300  # 너무 긴 파일은 앞부분만 사용

_SYSTEM_PROMPT = (
    "당신은 코딩을 전혀 모르는 사람도 이해할 수 있게 설명하는 선생님입니다. "
    "중학생도 이해할 수 있는 쉬운 말로, 비유와 예시를 들어 설명해주세요. "
    "전문 용어는 반드시 쉬운 말로 풀어서 설명하세요. 한국어로 답변하세요."
)

_MENU_ITEMS = [
    "이 파일이 하는 일은 무엇인가요? (한 줄로 요약)",
    "주요 기능을 쉬운 말로 설명해주세요. (코드를 모르는 사람 기준)",
    "다른 파일과 어떻게 연결되나요?",
    "AI가 이 파일을 수정할 때 주의해야 할 점이 있나요?",
]


def _has_api_key() -> bool:
    return any(os.environ.get(k) for k in [
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
        "GLM_API_KEY", "MOONSHOT_API_KEY",
    ])


def _build_file_header(rel_path: str, content: str, line_count: int) -> str:
    truncated = line_count > MAX_LINES
    display_content = "\n".join(content.splitlines()[:MAX_LINES])
    truncate_note = f"\n(파일이 길어서 앞 {MAX_LINES}줄만 포함했습니다. 전체 줄 수: {line_count}줄)\n" if truncated else ""
    suffix = Path(rel_path).suffix.lstrip(".") or "text"
    return f"""\
파일명: {rel_path}
줄 수: {line_count}줄{truncate_note}
내용:
```{suffix}
{display_content}
```"""


def _build_focused_prompt(rel_path: str, content: str, line_count: int, selected: list[int]) -> str:
    header = _build_file_header(rel_path, content, line_count)
    if len(selected) == len(_MENU_ITEMS):
        questions = "\n".join(f"{i+1}. {q}" for i, q in enumerate(_MENU_ITEMS))
        return f"""\
다음 파일을 코딩을 전혀 모르는 사람도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.

{header}

다음 항목으로 설명해주세요:

{questions}
"""
    else:
        questions = "\n".join(f"{i+1}. {_MENU_ITEMS[i]}" for i in selected)
        return f"""\
다음 파일에 대해 코딩을 전혀 모르는 중학생도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.

{header}

아래 질문에 답해주세요:

{questions}
"""


def _build_prompt(rel_path: str, content: str, line_count: int, question: str | None) -> str:
    header = _build_file_header(rel_path, content, line_count)
    specific_q = f"\n특히 이 부분이 궁금합니다: {question}\n" if question else ""
    return f"""\
다음 파일을 코딩을 전혀 모르는 사람도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.
{specific_q}
{header}

다음 항목으로 설명해주세요:

1. 이 파일이 하는 일은 무엇인가요? (한 줄로 요약)
2. 주요 기능을 쉬운 말로 설명해주세요. (코드를 모르는 사람 기준)
3. 다른 파일과 어떻게 연결되나요?
4. AI가 이 파일을 수정할 때 주의해야 할 점이 있나요?
"""


def _call_openai_compatible(api_key: str, base_url: str, model: str, prompt: str) -> bool:
    """OpenAI 호환 API 공통 호출 (OpenAI / GLM / Kimi)"""
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read())
        text = result["choices"][0]["message"]["content"]
        print(text)
    return True


def _try_anthropic(prompt: str) -> bool:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False
    try:
        import anthropic
    except ImportError:
        return False
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("AI가 파일을 분석하고 있습니다...\n")
        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
        print("\n")
        return True
    except Exception as e:
        print(f"Anthropic API 호출 실패: {e}\n")
        return False


def _try_openai(prompt: str) -> bool:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False
    try:
        print("AI가 파일을 분석하고 있습니다...\n")
        _call_openai_compatible(
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}\n")
        return False


def _try_gemini(prompt: str) -> bool:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        print("AI가 파일을 분석하고 있습니다...\n")
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(text)
        print()
        return True
    except Exception as e:
        print(f"Gemini API 호출 실패: {e}\n")
        return False


def _try_glm(prompt: str) -> bool:
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        return False
    try:
        print("AI가 파일을 분석하고 있습니다...\n")
        _call_openai_compatible(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4",
            model="glm-4-flash",
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"GLM API 호출 실패: {e}\n")
        return False


def _try_kimi(prompt: str) -> bool:
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        return False
    try:
        print("AI가 파일을 분석하고 있습니다...\n")
        _call_openai_compatible(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            model="moonshot-v1-8k",
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"Kimi API 호출 실패: {e}\n")
        return False


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

    # API 키가 있으면 항목 선택 메뉴 표시
    used_menu = False
    if not args.write and _has_api_key() and not question:
        used_menu = True
        print(f"\n파일: {rel} ({line_count}줄)\n")
        print("설명할 항목을 선택하세요:")
        print()
        for i, item in enumerate(_MENU_ITEMS, 1):
            print(f"  {i}. {item}")
        print(f"  0. 전체 다 설명해주세요")
        print()

        choice = input("선택 (0-4): ").strip()
        print()

        if choice == "0" or not choice:
            selected = list(range(len(_MENU_ITEMS)))
        elif choice.isdigit() and 1 <= int(choice) <= len(_MENU_ITEMS):
            selected = [int(choice) - 1]
        else:
            print("잘못된 선택입니다.")
            return

        prompt = _build_focused_prompt(rel, content, line_count, selected)
    else:
        prompt = _build_prompt(rel, content, line_count, question)

    # AI API 직접 호출 시도 (설정된 키 순서대로)
    if not args.write:
        if (
            _try_anthropic(prompt)
            or _try_openai(prompt)
            or _try_gemini(prompt)
            or _try_glm(prompt)
            or _try_kimi(prompt)
        ):
            return
        if used_menu:
            print("잠시 후 다시 시도하거나, 프롬프트를 저장하려면:")
            print(f"  vibeguard ask {target_input} --write")
            return

    # --write 또는 API 키 없을 때: 프롬프트 출력
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
        print("  (API 키 설정: vibeguard config)")
        print("=" * 60)
        print()
        print(prompt)
        print()
        print("파일로 저장하려면: vibeguard ask " + target_input + " --write")
