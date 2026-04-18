# === ANCHOR: AI_EXPLAIN_START ===
import json
import importlib
import os
import urllib.error
import urllib.request
from typing import Protocol, TypedDict, cast

from vibelign.core.http_retry import urlopen_read_with_retry, _SSL_CTX
from vibelign.terminal_render import print_attempted_providers, print_provider_status


from vibelign.terminal_render import cli_print

print = cli_print

_SYSTEM_PROMPT = (
    "당신은 코딩을 전혀 모르는 사람도 이해할 수 있게 설명하는 선생님입니다. "
    "중학생도 이해할 수 있는 쉬운 말로, 비유와 예시를 들어 설명해주세요. "
    "전문 용어는 반드시 쉬운 말로 풀어서 설명하세요. 한국어로 답변하세요."
)


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
                "클라이언트에서 지수 백오프로 자동 재시도한 뒤에도 실패한 경우입니다.",
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


class ExplainFileEntry(TypedDict, total=False):
    path: str
    status: str
    kind: str


class ExplainPromptData(TypedDict, total=False):
    source: str
    risk_level: str
    summary: str
    what_changed: list[str]
    why_it_matters: list[str]
    what_to_do_next: str
    files: list[object]


class ChatMessage(TypedDict):
    role: str
    content: str


class OpenAICompatibleRequest(TypedDict):
    model: str
    messages: list[ChatMessage]
    max_tokens: int


class UrlopenResponse(Protocol):
    def read(self) -> bytes: ...

    def __enter__(self) -> "UrlopenResponse": ...

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None: ...


class AnthropicTextBlock(Protocol):
    type: str
    text: str


class AnthropicMessageResponse(Protocol):
    content: object


class AnthropicMessages(Protocol):
    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[ChatMessage],
    ) -> AnthropicMessageResponse: ...


class AnthropicClient(Protocol):
    messages: AnthropicMessages


class AnthropicModule(Protocol):
    def Anthropic(self, *, api_key: str) -> AnthropicClient: ...


def _load_json_object(raw: bytes) -> dict[str, object] | None:
    parsed = cast(object, json.loads(raw))
    if not isinstance(parsed, dict):
        return None
    source = cast(dict[object, object], parsed)
    normalized: dict[str, object] = {}
    for key, value in source.items():
        normalized[str(key)] = value
    return normalized


def _normalize_object_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    source = cast(dict[object, object], value)
    normalized: dict[str, object] = {}
    for key, item in source.items():
        normalized[str(key)] = item
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


# === ANCHOR: AI_EXPLAIN__FRIENDLY_ERROR_START ===
def _friendly_error(provider: str, exc: Exception) -> str:
    """AI API 에러를 코알못이 이해할 수 있는 메시지로 변환."""
    msg = str(exc)
    if "401" in msg or "403" in msg or "Unauthorized" in msg:
        return (
            f"{provider} API 키가 맞지 않아요. vib config 에서 키를 다시 확인해보세요."
        )
    if "429" in msg or "rate" in msg.lower():
        return f"{provider} AI가 지금 너무 바빠서 응답하지 못했어요. 잠시 후 다시 시도하세요."
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return f"{provider} AI가 응답하는 데 너무 오래 걸렸어요. 인터넷 연결을 확인하고 다시 시도하세요."
    if (
        "connection" in msg.lower()
        or "network" in msg.lower()
        or "urlopen" in msg.lower()
    ):
        return f"{provider} AI에 연결할 수 없어요. 인터넷 연결을 확인해보세요."
    return f"{provider} AI 호출에 문제가 생겼어요. (기술 코드: {msg})"


# === ANCHOR: AI_EXPLAIN__FRIENDLY_ERROR_END ===


# === ANCHOR: AI_EXPLAIN_HAS_AI_PROVIDER_START ===
def has_ai_provider() -> bool:
    from vibelign.core.keys_store import has_any_ai_key
    return has_any_ai_key()


# === ANCHOR: AI_EXPLAIN_HAS_AI_PROVIDER_END ===


# === ANCHOR: AI_EXPLAIN_BUILD_EXPLAIN_AI_PROMPT_START ===
def build_explain_ai_prompt(data: ExplainPromptData) -> str:
    what_changed = "\n".join(f"- {item}" for item in data.get("what_changed", []))
    why_it_matters = "\n".join(f"- {item}" for item in data.get("why_it_matters", []))
    file_lines: list[str] = []
    for item in data.get("files", []):
        entry = _normalize_object_dict(item)
        if entry is None:
            continue
        path = entry.get("path") if isinstance(entry.get("path"), str) else "unknown"
        status = (
            entry.get("status") if isinstance(entry.get("status"), str) else "unknown"
        )
        kind = entry.get("kind") if isinstance(entry.get("kind"), str) else "unknown"
        file_lines.append(f"- {path} ({status}, {kind})")
    files = "\n".join(file_lines)
    return f"""다음 변경 요약을 바탕으로 코딩을 모르는 사람도 이해할 수 있게 한국어로 다시 설명해주세요.
# === ANCHOR: AI_EXPLAIN_BUILD_EXPLAIN_AI_PROMPT_END ===
형식은 반드시 아래 4개 섹션을 유지하세요.

## 1. 한 줄 요약
## 2. 변경된 내용
## 3. 왜 중요한가
## 4. 다음 할 일

조건:
- 중학생도 이해할 수 있는 쉬운 말
- 전문 용어는 쉬운 말로 풀기
- 과한 서론 없이 바로 본문 시작
- 각 섹션은 짧은 bullet 또는 짧은 문단 1~3개

현재 요약 데이터:
- source: {data.get("source")}
- risk_level: {data.get("risk_level")}
- summary: {data.get("summary")}

what_changed:
{what_changed or "- 없음"}

why_it_matters:
{why_it_matters or "- 없음"}

what_to_do_next:
{data.get("what_to_do_next")}

files:
{files or "- 없음"}
"""


# === ANCHOR: AI_EXPLAIN__CALL_OPENAI_COMPATIBLE_START ===
def _call_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    # === ANCHOR: AI_EXPLAIN__CALL_OPENAI_COMPATIBLE_END ===
) -> str:
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
    with cast(UrlopenResponse, urllib.request.urlopen(req, timeout=60, context=_SSL_CTX)) as response:
        result = _load_json_object(response.read())
        text = _extract_openai_text(result or {})
        if text is None:
            raise RuntimeError("OpenAI 호환 응답에서 내용을 찾지 못했습니다.")
        return text


# === ANCHOR: AI_EXPLAIN__TRY_ANTHROPIC_START ===
def _try_anthropic(
    prompt: str,
    attempted: list[str],
    quiet: bool = False,
    # === ANCHOR: AI_EXPLAIN__TRY_ANTHROPIC_END ===
) -> str | None:
    from vibelign.core.keys_store import get_key
    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    model = "claude-haiku-4-5"
    try:
        anthropic_raw = cast(object, importlib.import_module("anthropic"))
        anthropic_module = cast(AnthropicModule, anthropic_raw)
    except ImportError:
        return None
    try:
        attempted.append(f"Anthropic ({model})")
        if not quiet:
            print_provider_status("Anthropic", model)
        client = anthropic_module.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        content_blocks = cast(list[object], message.content)
        texts: list[str] = []
        for block_obj in content_blocks:
            block = cast(AnthropicTextBlock, block_obj)
            if getattr(block, "type", "") == "text":
                text = getattr(block, "text", "")
                if isinstance(text, str):
                    texts.append(text)
        return "".join(texts)
    except Exception as exc:
        if not quiet:
            print(_friendly_error("Anthropic", exc) + "\n")
        return None


# === ANCHOR: AI_EXPLAIN__TRY_OPENAI_START ===
def _try_openai(
    prompt: str,
    attempted: list[str],
    quiet: bool = False,
    # === ANCHOR: AI_EXPLAIN__TRY_OPENAI_END ===
) -> str | None:
    from vibelign.core.keys_store import get_key
    api_key = get_key("OPENAI_API_KEY")
    if not api_key:
        return None
    model = "gpt-4o-mini"
    try:
        attempted.append(f"OpenAI ({model})")
        if not quiet:
            print_provider_status("OpenAI", model)
        return _call_openai_compatible(
            api_key, "https://api.openai.com/v1", model, prompt
        )
    except Exception as exc:
        if not quiet:
            print(_friendly_error("OpenAI", exc) + "\n")
        return None


# === ANCHOR: AI_EXPLAIN__TRY_GEMINI_START ===
def _try_gemini(
    prompt: str,
    attempted: list[str],
    quiet: bool = False,
    # === ANCHOR: AI_EXPLAIN__TRY_GEMINI_END ===
) -> str | None:
    from vibelign.core.keys_store import get_key
    api_key = get_key("GEMINI_API_KEY")
    if not api_key:
        return None
    model = (get_key("GEMINI_MODEL") or "").strip() or "gemini-3-flash-preview"
    try:
        attempted.append(f"Gemini ({model})")
        if not quiet:
            print_provider_status("Gemini", model)
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
        raw = urlopen_read_with_retry(req, timeout=60)
        result = _load_json_object(raw)
        text = _extract_gemini_text(result or {})
        if text is None:
            raise RuntimeError("Gemini 응답에서 내용을 찾지 못했습니다.")
        return text
    except Exception as exc:
        if not quiet:
            print(_format_gemini_error(exc, model) + "\n")
        return None


# === ANCHOR: AI_EXPLAIN__TRY_GLM_START ===
def _try_glm(prompt: str, attempted: list[str], quiet: bool = False) -> str | None:
    from vibelign.core.keys_store import get_key
    api_key = get_key("GLM_API_KEY")
    if not api_key:
        return None
    model = "glm-4-flash"
    try:
        attempted.append(f"GLM ({model})")
        if not quiet:
            print_provider_status("GLM", model)
        return _call_openai_compatible(
            api_key, "https://open.bigmodel.cn/api/paas/v4", model, prompt
        )
    except Exception as exc:
        if not quiet:
            print(_friendly_error("GLM", exc) + "\n")
        return None


# === ANCHOR: AI_EXPLAIN__TRY_GLM_END ===


# === ANCHOR: AI_EXPLAIN__TRY_KIMI_START ===
def _try_kimi(prompt: str, attempted: list[str], quiet: bool = False) -> str | None:
    from vibelign.core.keys_store import get_key
    api_key = get_key("MOONSHOT_API_KEY")
    if not api_key:
        return None
    model = "moonshot-v1-8k"
    try:
        attempted.append(f"Kimi ({model})")
        if not quiet:
            print_provider_status("Kimi", model)
        return _call_openai_compatible(
            api_key, "https://api.moonshot.cn/v1", model, prompt
        )
    except Exception as exc:
        if not quiet:
            print(_friendly_error("Kimi", exc) + "\n")
        return None


# === ANCHOR: AI_EXPLAIN__TRY_KIMI_END ===


# === ANCHOR: AI_EXPLAIN_EXPLAIN_WITH_AI_START ===
def explain_with_ai(data: ExplainPromptData) -> tuple[str | None, list[str]]:
    prompt = build_explain_ai_prompt(data)
    return generate_text_with_ai(prompt)


# === ANCHOR: AI_EXPLAIN_EXPLAIN_WITH_AI_END ===


# === ANCHOR: AI_EXPLAIN_GENERATE_TEXT_WITH_AI_START ===
def generate_text_with_ai(
    prompt: str,
    quiet: bool = False,
    # === ANCHOR: AI_EXPLAIN_GENERATE_TEXT_WITH_AI_END ===
) -> tuple[str | None, list[str]]:
    attempted: list[str] = []
    text = _try_anthropic(prompt, attempted, quiet=quiet)
    if text is None:
        text = _try_openai(prompt, attempted, quiet=quiet)
    if text is None:
        text = _try_gemini(prompt, attempted, quiet=quiet)
    if text is None:
        text = _try_glm(prompt, attempted, quiet=quiet)
    if text is None:
        text = _try_kimi(prompt, attempted, quiet=quiet)
    if text is None and not quiet:
        print_attempted_providers(attempted)
    return text, attempted


# === ANCHOR: AI_EXPLAIN_END ===
