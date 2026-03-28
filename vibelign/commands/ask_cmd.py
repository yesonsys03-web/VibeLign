# === ANCHOR: ASK_CMD_START ===
from collections.abc import Iterable
import os
import json
import importlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol, TypedDict, cast

from vibelign.terminal_render import (
    print_ai_response,
    print_attempted_providers,
    print_provider_status,
    should_use_rich,
)

from vibelign.terminal_render import cli_print

print = cli_print


class AskArgs(Protocol):
    file: str
    question: list[str] | None
    write: bool


class ChatMessage(TypedDict):
    role: str
    content: str


class OpenAICompatibleRequest(TypedDict):
    model: str
    messages: list[ChatMessage]
    max_tokens: int


class OpenAIMessage(TypedDict):
    content: str


class OpenAIChoice(TypedDict):
    message: OpenAIMessage


class OpenAIResponse(TypedDict):
    choices: list[OpenAIChoice]


class GeminiPart(TypedDict):
    text: str


class GeminiContent(TypedDict):
    parts: list[GeminiPart]


class GeminiCandidate(TypedDict):
    content: GeminiContent


class GeminiResponse(TypedDict):
    candidates: list[GeminiCandidate]


class AnthropicTextStream(Protocol):
    text_stream: object

    def __enter__(self) -> "AnthropicTextStream": ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None: ...


class AnthropicMessages(Protocol):
    def stream(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[ChatMessage],
    ) -> AnthropicTextStream: ...


class AnthropicClient(Protocol):
    messages: AnthropicMessages


class AnthropicModule(Protocol):
    def Anthropic(self, *, api_key: str) -> AnthropicClient: ...


class UrlopenResponse(Protocol):
    def read(self) -> bytes: ...

    def __enter__(self) -> "UrlopenResponse": ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None: ...


def _load_json_object(raw: bytes) -> dict[str, object] | None:
    parsed = cast(object, json.loads(raw))
    if not isinstance(parsed, dict):
        return None
    source = cast(dict[object, object], parsed)
    normalized: dict[str, object] = {}
    for key, value in source.items():
        normalized[str(key)] = value
    return normalized


def _extract_openai_text(result: dict[str, object]) -> str | None:
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = cast(object, choices[0])
    if not isinstance(first, dict):
        return None
    message = cast(dict[object, object], first).get("message")
    if not isinstance(message, dict):
        return None
    content = cast(dict[object, object], message).get("content")
    return content if isinstance(content, str) else None


def _extract_gemini_text(result: dict[str, object]) -> str | None:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    first = cast(object, candidates[0])
    if not isinstance(first, dict):
        return None
    content = cast(dict[object, object], first).get("content")
    if not isinstance(content, dict):
        return None
    parts = cast(dict[object, object], content).get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    first_part = cast(object, parts[0])
    if not isinstance(first_part, dict):
        return None
    text = cast(dict[object, object], first_part).get("text")
    return text if isinstance(text, str) else None


MAX_LINES = 300  # 너무 긴 파일은 앞부분만 사용
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"


# === ANCHOR: ASK_CMD__FORMAT_GEMINI_ERROR_START ===
def _format_gemini_error(error: Exception, model: str) -> str:
    if isinstance(error, urllib.error.HTTPError):
        try:
            detail = error.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            detail = ""
        if len(detail) > 500:
            detail = detail[:500] + "..."
        if error.code == 429:
            message = [
                f"Gemini API 호출 실패: HTTP 429 Too Many Requests (model={model})",
                "잠시 후 다시 시도하거나, 다른 Gemini 모델을 쓰려면 `GEMINI_MODEL` 환경변수를 설정하세요.",
                "계속 반복되면 Google AI Studio에서 rate limit / quota / billing 상태를 확인하세요.",
            ]
            if detail:
                message.append(f"응답 본문: {detail}")
            return "\n".join(message)
        if error.code in (502, 503, 504):
            status_text = {
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout",
            }.get(error.code, str(error.code))
            message = [
                f"Gemini API 호출 실패: HTTP {error.code} {status_text} (model={model})",
                "Gemini 서버나 해당 모델이 일시적으로 요청을 처리하지 못하는 상태일 수 있습니다.",
                "잠시 후 다시 시도하거나, 다른 Gemini 모델을 쓰려면 `GEMINI_MODEL` 환경변수를 설정하세요.",
            ]
            if detail:
                message.append(f"응답 본문: {detail}")
            return "\n".join(message)
    return f"Gemini API 호출 실패: {error}"


# === ANCHOR: ASK_CMD__FORMAT_GEMINI_ERROR_END ===


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

_SECTION_SPECS = [
    ("## 1. 한 줄 요약", "이 파일이 하는 일을 한두 문장으로만 요약해주세요."),
    (
        "## 2. 주요 기능을 쉬운 말로 설명",
        "핵심 기능을 코드 비유나 쉬운 예시로 설명해주세요.",
    ),
    (
        "## 3. 다른 파일과 연결",
        "이 파일이 어떤 파일/기능과 이어지는지 간단한 목록으로 설명해주세요.",
    ),
    (
        "## 4. 수정할 때 주의할 점",
        "AI나 사람이 수정할 때 조심해야 할 포인트를 짧은 목록으로 정리해주세요.",
    ),
]


# === ANCHOR: ASK_CMD__BUILD_RESPONSE_FORMAT_START ===
def _build_response_format(selected: list[int], question: str | None = None) -> str:
    sections: list[str] = []
    for index in selected:
        title, guide = _SECTION_SPECS[index]
        sections.append(f"{title}\n- {guide}")
    if question:
        sections.append(
            "## 5. 추가 질문 답변\n- 사용자가 따로 묻는 질문에 직접 답해주세요."
        )
    return "\n\n".join(sections)


# === ANCHOR: ASK_CMD__BUILD_RESPONSE_FORMAT_END ===


# === ANCHOR: ASK_CMD__HAS_API_KEY_START ===
def _has_api_key() -> bool:
    return any(
        os.environ.get(k)
        for k in [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "GLM_API_KEY",
            "MOONSHOT_API_KEY",
        ]
    )


# === ANCHOR: ASK_CMD__HAS_API_KEY_END ===


# === ANCHOR: ASK_CMD__BUILD_FILE_HEADER_START ===
def _build_file_header(rel_path: str, content: str, line_count: int) -> str:
    truncated = line_count > MAX_LINES
    display_content = "\n".join(content.splitlines()[:MAX_LINES])
    truncate_note = (
        f"\n(파일이 길어서 앞 {MAX_LINES}줄만 포함했습니다. 전체 줄 수: {line_count}줄)\n"
        if truncated
        else ""
    )
    suffix = Path(rel_path).suffix.lstrip(".") or "text"
    return f"""\
# === ANCHOR: ASK_CMD__BUILD_FILE_HEADER_END ===
파일명: {rel_path}
줄 수: {line_count}줄{truncate_note}
내용:
```{suffix}
{display_content}
```"""


# === ANCHOR: ASK_CMD__BUILD_FOCUSED_PROMPT_START ===
def _build_focused_prompt(
    rel_path: str,
    content: str,
    line_count: int,
    selected: list[int],
    # === ANCHOR: ASK_CMD__BUILD_FOCUSED_PROMPT_END ===
) -> str:
    header = _build_file_header(rel_path, content, line_count)
    section_format = _build_response_format(selected)
    return f"""\
다음 파일을 코딩을 전혀 모르는 사람도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.
불필요한 인사말이나 서론 없이 바로 본문부터 시작하세요.
각 섹션 제목은 아래 형식을 정확히 유지하고, 섹션마다 1~3개의 짧은 문단 또는 bullet 목록만 사용하세요.
과한 마크다운 장식은 쓰지 말고, 코드/함수/파일명만 `backtick`으로 감싸세요.

{header}

반드시 아래 형식으로 답해주세요:

{section_format}
"""


# === ANCHOR: ASK_CMD__BUILD_PROMPT_START ===
def _build_prompt(
    rel_path: str,
    content: str,
    line_count: int,
    question: str | None,
    # === ANCHOR: ASK_CMD__BUILD_PROMPT_END ===
) -> str:
    header = _build_file_header(rel_path, content, line_count)
    specific_q = f"\n특히 이 부분이 궁금합니다: {question}\n" if question else ""
    section_format = _build_response_format(list(range(len(_MENU_ITEMS))), question)
    return f"""\
다음 파일을 코딩을 전혀 모르는 사람도 이해할 수 있도록 한국어로 쉽게 설명해주세요.
전문 용어는 최대한 피하고, 비유나 예시를 들어 설명해주세요.
불필요한 인사말이나 서론 없이 바로 본문부터 시작하세요.
각 섹션 제목은 아래 형식을 정확히 유지하고, 섹션마다 1~3개의 짧은 문단 또는 bullet 목록만 사용하세요.
과한 마크다운 장식은 쓰지 말고, 코드/함수/파일명만 `backtick`으로 감싸세요.
{specific_q}
{header}

반드시 아래 형식으로 답해주세요:

{section_format}
"""


# === ANCHOR: ASK_CMD__CALL_OPENAI_COMPATIBLE_START ===
def _call_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    # === ANCHOR: ASK_CMD__CALL_OPENAI_COMPATIBLE_END ===
) -> bool:
    """OpenAI 호환 API 공통 호출 (OpenAI / GLM / Kimi)"""
    data: OpenAICompatibleRequest = {
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
    with cast(UrlopenResponse, urllib.request.urlopen(req, timeout=60)) as response:
        raw = response.read()
        result = _load_json_object(raw)
        text = _extract_openai_text(result or {})
        if text is None:
            raise RuntimeError("OpenAI 호환 응답에서 내용을 찾지 못했습니다.")
        print_ai_response(text)
    return True


# === ANCHOR: ASK_CMD__TRY_ANTHROPIC_START ===
def _try_anthropic(prompt: str, attempted: list[str]) -> bool:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False
    model = "claude-haiku-4-5"
    try:
        anthropic_raw = cast(object, importlib.import_module("anthropic"))
        anthropic_module = cast(AnthropicModule, anthropic_raw)
    except ImportError:
        return False
    try:
        client = anthropic_module.Anthropic(api_key=api_key)
        attempted.append(f"Anthropic ({model})")
        print_provider_status("Anthropic", model)
        print("AI가 파일을 분석하고 있습니다...\n")
        rich_output = should_use_rich()
        chunks: list[str] = []
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            iterator = cast(Iterable[object], stream.text_stream)
            for text in iterator:
                if not isinstance(text, str):
                    continue
                if rich_output:
                    chunks.append(text)
                else:
                    print(text, end="", flush=True)
        if rich_output:
            print_ai_response("".join(chunks), use_rich=True)
            print()
        else:
            print("\n")
        return True
    except Exception as e:
        print(f"Anthropic API 호출 실패: {e}\n")
        return False


# === ANCHOR: ASK_CMD__TRY_ANTHROPIC_END ===


# === ANCHOR: ASK_CMD__TRY_OPENAI_START ===
def _try_openai(prompt: str, attempted: list[str]) -> bool:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False
    model = "gpt-4o-mini"
    try:
        attempted.append(f"OpenAI ({model})")
        print_provider_status("OpenAI", model)
        print("AI가 파일을 분석하고 있습니다...\n")
        _ = _call_openai_compatible(
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            model=model,
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"OpenAI API 호출 실패: {e}\n")
        return False


# === ANCHOR: ASK_CMD__TRY_OPENAI_END ===


# === ANCHOR: ASK_CMD__TRY_GEMINI_START ===
def _try_gemini(prompt: str, attempted: list[str]) -> bool:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    model = (os.environ.get("GEMINI_MODEL") or "").strip() or DEFAULT_GEMINI_MODEL
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
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
        attempted.append(f"Gemini ({model})")
        print_provider_status("Gemini", model)
        print("AI가 파일을 분석하고 있습니다...\n")
        with cast(UrlopenResponse, urllib.request.urlopen(req, timeout=60)) as response:
            raw = response.read()
            result = _load_json_object(raw)
            text = _extract_gemini_text(result or {})
            if text is None:
                raise RuntimeError("Gemini 응답에서 내용을 찾지 못했습니다.")
            print_ai_response(text)
        print()
        return True
    except Exception as e:
        print(_format_gemini_error(e, model) + "\n")
        return False


# === ANCHOR: ASK_CMD__TRY_GEMINI_END ===


# === ANCHOR: ASK_CMD__TRY_GLM_START ===
def _try_glm(prompt: str, attempted: list[str]) -> bool:
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        return False
    model = "glm-4-flash"
    try:
        attempted.append(f"GLM ({model})")
        print_provider_status("GLM", model)
        print("AI가 파일을 분석하고 있습니다...\n")
        _ = _call_openai_compatible(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4",
            model=model,
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"GLM API 호출 실패: {e}\n")
        return False


# === ANCHOR: ASK_CMD__TRY_GLM_END ===


# === ANCHOR: ASK_CMD__TRY_KIMI_START ===
def _try_kimi(prompt: str, attempted: list[str]) -> bool:
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        return False
    model = "moonshot-v1-8k"
    try:
        attempted.append(f"Kimi ({model})")
        print_provider_status("Kimi", model)
        print("AI가 파일을 분석하고 있습니다...\n")
        _ = _call_openai_compatible(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            model=model,
            prompt=prompt,
        )
        print()
        return True
    except Exception as e:
        print(f"Kimi API 호출 실패: {e}\n")
        return False


# === ANCHOR: ASK_CMD__TRY_KIMI_END ===


# === ANCHOR: ASK_CMD_RUN_ASK_START ===
def run_ask(args: AskArgs) -> None:
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
        attempted: list[str] = []
        if (
            _try_anthropic(prompt, attempted)
            or _try_openai(prompt, attempted)
            or _try_gemini(prompt, attempted)
            or _try_glm(prompt, attempted)
            or _try_kimi(prompt, attempted)
        ):
            return
        print_attempted_providers(attempted)
        if used_menu:
            print("잠시 후 다시 시도하거나, 프롬프트를 저장하려면:")
            print(f"  vib ask {target_input} --write")
            return

    # --write 또는 API 키 없을 때: 프롬프트 출력
    if args.write:
        out = root / "VIBELIGN_ASK.md"
        if out.exists():
            print(f"경고: 기존 {out.name} 파일을 덮어씁니다")
        _ = out.write_text(prompt, encoding="utf-8")
        print(f"{out.name}에 저장했습니다.")
        print()
        print("이 파일 내용을 복사해서 AI 툴(OpenCode, Claude 등)에 붙여넣으세요.")
    else:
        print("=" * 60)
        print("  아래 내용을 복사해서 AI 툴에 붙여넣으세요")
        print("  (API 키 설정: vib config)")
        print("=" * 60)
        print()
        print(prompt)
        print()
        print("파일로 저장하려면: vib ask " + target_input + " --write")


# === ANCHOR: ASK_CMD_RUN_ASK_END ===
# === ANCHOR: ASK_CMD_END ===
