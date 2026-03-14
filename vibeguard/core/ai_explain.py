import json
import importlib
import os
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, cast

from vibeguard.commands.ask_cmd import _SYSTEM_PROMPT, _format_gemini_error
from vibeguard.terminal_render import print_attempted_providers, print_provider_status


def has_ai_provider() -> bool:
    return any(
        os.environ.get(key)
        for key in [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "GLM_API_KEY",
            "MOONSHOT_API_KEY",
        ]
    )


def build_explain_ai_prompt(data: Dict[str, Any]) -> str:
    what_changed = "\n".join(f"- {item}" for item in data.get("what_changed", []))
    why_it_matters = "\n".join(f"- {item}" for item in data.get("why_it_matters", []))
    file_lines = []
    for item in data.get("files", []):
        if not isinstance(item, dict):
            continue
        path = item.get("path") or "unknown"
        status = item.get("status") or "unknown"
        kind = item.get("kind") or "unknown"
        file_lines.append(f"- {path} ({status}, {kind})")
    files = "\n".join(file_lines)
    return f"""다음 변경 요약을 바탕으로 코딩을 모르는 사람도 이해할 수 있게 한국어로 다시 설명해주세요.
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


def _call_openai_compatible(
    api_key: str, base_url: str, model: str, prompt: str
) -> str:
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
        return result["choices"][0]["message"]["content"]


def _try_anthropic(
    prompt: str, attempted: List[str], quiet: bool = False
) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    model = "claude-haiku-4-5"
    try:
        anthropic_module = cast(Any, importlib.import_module("anthropic"))
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
        return "".join(
            block.text
            for block in message.content
            if getattr(block, "type", "") == "text"
        )
    except Exception as exc:
        if not quiet:
            print(f"Anthropic API 호출 실패: {exc}\n")
        return None


def _try_openai(
    prompt: str, attempted: List[str], quiet: bool = False
) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY")
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
            print(f"OpenAI API 호출 실패: {exc}\n")
        return None


def _try_gemini(
    prompt: str, attempted: List[str], quiet: bool = False
) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    model = (os.environ.get("GEMINI_MODEL") or "").strip() or "gemini-3-flash-preview"
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
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        if not quiet:
            print(_format_gemini_error(exc, model) + "\n")
        return None


def _try_glm(prompt: str, attempted: List[str], quiet: bool = False) -> Optional[str]:
    api_key = os.environ.get("GLM_API_KEY")
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
            print(f"GLM API 호출 실패: {exc}\n")
        return None


def _try_kimi(prompt: str, attempted: List[str], quiet: bool = False) -> Optional[str]:
    api_key = os.environ.get("MOONSHOT_API_KEY")
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
            print(f"Kimi API 호출 실패: {exc}\n")
        return None


def explain_with_ai(data: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    prompt = build_explain_ai_prompt(data)
    return generate_text_with_ai(prompt)


def generate_text_with_ai(
    prompt: str, quiet: bool = False
) -> Tuple[Optional[str], List[str]]:
    attempted: List[str] = []
    text = (
        _try_anthropic(prompt, attempted, quiet=quiet)
        or _try_openai(prompt, attempted, quiet=quiet)
        or _try_gemini(prompt, attempted, quiet=quiet)
        or _try_glm(prompt, attempted, quiet=quiet)
        or _try_kimi(prompt, attempted, quiet=quiet)
    )
    if text is None and not quiet:
        print_attempted_providers(attempted)
    return text, attempted
