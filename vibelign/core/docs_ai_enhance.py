# === ANCHOR: DOCS_AI_ENHANCE_START ===
"""단일 markdown 문서에 대해 LLM 을 호출해 구조화된 요약 필드를 돌려준다.

Anthropic/OpenAI/Gemini 중 키스토어에 등록된 첫 번째 provider 를 사용한다.
네트워크 호출은 vibelign.core.http_retry 를 통해 재시도한다.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from . import http_retry as _HTTP_RETRY
from . import keys_store as _KEYS

_PROVIDER_PRIORITY: list[tuple[str, str]] = [
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("gemini", "GEMINI_API_KEY"),
]


def _model_override(provider: str) -> str | None:
    env_name = f"VIBELIGN_DOCS_AI_MODEL_{provider.upper()}"
    value = os.environ.get(env_name, "").strip()
    return value or None


def _format_http_error(provider: str, model: str, error: urllib.error.HTTPError) -> str:
    try:
        detail = error.read().decode("utf-8", errors="ignore").strip()
    except Exception:
        detail = ""
    if len(detail) > 1000:
        detail = detail[:1000] + "..."
    message = f"{provider} API 호출 실패: HTTP {error.code} {error.reason} (model={model})"
    if provider == "Gemini" and "API_KEY_INVALID" in detail:
        message += "\nGemini API 키가 유효하지 않아요. Settings에서 Gemini 키를 삭제한 뒤 아래 링크에서 새 키를 발급해 다시 저장해주세요.\nGoogle AI Studio API 키 발급: https://aistudio.google.com/app/apikey"
    if provider == "Gemini" and error.code == 429:
        message += (
            "\n분당 요청 한도를 초과했어요 (무료 등급은 분당 20회로 제한됩니다)."
            "\n유료 등급으로 전환하면 한도가 크게 올라가서 가장 빠른 해결책이에요: https://aistudio.google.com/app/apikey"
            "\n무료 등급을 유지하려면 환경변수로 자동 재시도를 늘릴 수 있어요:"
            "\n  GEMINI_HTTP_MAX_ATTEMPTS (기본 6) — 재시도 횟수를 늘려 더 오래 버팁니다"
            "\n  GEMINI_HTTP_RETRY_CAP (기본 120) — 한 번 대기할 수 있는 최대 초"
            "\n예: GEMINI_HTTP_MAX_ATTEMPTS=10 GEMINI_HTTP_RETRY_CAP=180 vib docs-enhance ..."
        )
    if detail:
        message += f"\n응답 본문: {detail}"
    return message


PROMPT_TEMPLATE = """You are a precise documentation summarizer for a developer tool.

Read the markdown document below and return a JSON object with these fields:
- tldr_one_liner (string, ≤ 180 chars): one-sentence summary in the document's language
- key_rules (string[], max 6): explicit rules or principles stated in the doc
- success_criteria (string[], max 5): how the reader knows the goal is met
- edge_cases (string[], max 5): failure modes, exceptions, pitfalls
- components (string[], max 6): "name — one-line role" for each major component discussed

Rules:
- Return JSON only — no prose, no markdown fences
- Use the language of the source document (Korean/English as-is)
- If a field has no evidence in the doc, return empty string or empty array — don't fabricate
- Quote or paraphrase from the doc; don't inject generic statements

=== DOCUMENT START ===
{source_text}
=== DOCUMENT END ===
"""


# === ANCHOR: DOCS_AI_ENHANCE_BUILD_PROMPT_START ===
def build_prompt(source_text: str) -> str:
    return PROMPT_TEMPLATE.format(source_text=source_text)
# === ANCHOR: DOCS_AI_ENHANCE_BUILD_PROMPT_END ===


# === ANCHOR: DOCS_AI_ENHANCE_PARSE_ANTHROPIC_RESPONSE_START ===
def parse_anthropic_response(body: dict[str, Any]) -> dict[str, Any]:
    blocks = body.get("content") or []
    text = next(
        (b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"),
        "",
    ).strip()
    if not text:
        raise ValueError("AI 응답이 비어있습니다")
    try:
        fields = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI 응답 JSON 파싱 실패: {exc}") from exc
    usage = body.get("usage") or {}
    return {
        "fields": {
            "tldr_one_liner": str(fields.get("tldr_one_liner", ""))[:180],
            "key_rules": [str(x) for x in (fields.get("key_rules") or [])][:6],
            "success_criteria": [str(x) for x in (fields.get("success_criteria") or [])][:5],
            "edge_cases": [str(x) for x in (fields.get("edge_cases") or [])][:5],
            "components": [str(x) for x in (fields.get("components") or [])][:6],
        },
        "tokens_input": int(usage.get("input_tokens", 0)),
        "tokens_output": int(usage.get("output_tokens", 0)),
    }
# === ANCHOR: DOCS_AI_ENHANCE_PARSE_ANTHROPIC_RESPONSE_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CALL_ANTHROPIC_START ===
def call_anthropic(source_text: str, *, model: str | None = None) -> dict[str, Any]:
    model = model or _model_override("anthropic") or "claude-sonnet-4-5"
    api_key = _KEYS.get_key("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 가 환경변수/키스토어에 없습니다")

    prompt = build_prompt(source_text)
    payload = json.dumps({
        "model": model,
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    raw = _HTTP_RETRY.urlopen_read_with_retry(req, timeout=60.0)
    body = json.loads(raw.decode("utf-8"))
    parsed = parse_anthropic_response(body)
    parsed["model"] = model
    parsed["provider"] = "anthropic"
    # pricing rough estimate (claude sonnet 4.5: $3/MTok in, $15/MTok out)
    parsed["cost_usd"] = round(
        (parsed["tokens_input"] * 3 + parsed["tokens_output"] * 15) / 1_000_000, 6
    )
    return parsed
# === ANCHOR: DOCS_AI_ENHANCE_CALL_ANTHROPIC_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CAP_FIELDS_START ===
def _cap_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "tldr_one_liner": str(fields.get("tldr_one_liner", ""))[:180],
        "key_rules": [str(x) for x in (fields.get("key_rules") or [])][:6],
        "success_criteria": [str(x) for x in (fields.get("success_criteria") or [])][:5],
        "edge_cases": [str(x) for x in (fields.get("edge_cases") or [])][:5],
        "components": [str(x) for x in (fields.get("components") or [])][:6],
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith(("json", "JSON")):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])
# === ANCHOR: DOCS_AI_ENHANCE_CAP_FIELDS_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CALL_OPENAI_START ===
def call_openai(source_text: str, *, model: str | None = None) -> dict[str, Any]:
    model = model or _model_override("openai") or "gpt-4o-mini"
    api_key = _KEYS.get_key("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 가 환경변수/키스토어에 없습니다")

    prompt = build_prompt(source_text)
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
    )
    raw = _HTTP_RETRY.urlopen_read_with_retry(req, timeout=60.0)
    body = json.loads(raw.decode("utf-8"))
    choices = body.get("choices") or []
    text = (
        choices[0].get("message", {}).get("content", "")
        if choices and isinstance(choices[0], dict)
        else ""
    ).strip()
    if not text:
        raise ValueError("AI 응답이 비어있습니다")
    fields = _extract_json_object(text)
    usage = body.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))
    return {
        "fields": _cap_fields(fields),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "model": model,
        "provider": "openai",
        # gpt-4o-mini: $0.15/MTok in, $0.60/MTok out
        "cost_usd": round((tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000, 6),
    }
# === ANCHOR: DOCS_AI_ENHANCE_CALL_OPENAI_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CALL_GEMINI_START ===
def call_gemini(source_text: str, *, model: str | None = None) -> dict[str, Any]:
    model = model or _model_override("gemini") or "gemini-flash-latest"
    api_key = _KEYS.get_key("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 가 환경변수/키스토어에 없습니다")

    prompt = build_prompt(source_text)
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"content-type": "application/json"},
    )
    try:
        raw = _HTTP_RETRY.urlopen_read_with_retry(req, timeout=60.0)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_format_http_error("Gemini", model, exc)) from exc
    body = json.loads(raw.decode("utf-8"))
    candidates = body.get("candidates") or []
    parts = (
        candidates[0].get("content", {}).get("parts", [])
        if candidates and isinstance(candidates[0], dict)
        else []
    )
    text = "".join(
        p.get("text", "") for p in parts if isinstance(p, dict)
    ).strip()
    if not text:
        raise ValueError("AI 응답이 비어있습니다")
    fields = _extract_json_object(text)
    usage = body.get("usageMetadata") or {}
    tokens_in = int(usage.get("promptTokenCount", 0))
    tokens_out = int(usage.get("candidatesTokenCount", 0))
    return {
        "fields": _cap_fields(fields),
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "model": model,
        "provider": "gemini",
        # gemini 2.5 flash: $0.075/MTok in, $0.30/MTok out (approximate)
        "cost_usd": round((tokens_in * 0.075 + tokens_out * 0.30) / 1_000_000, 6),
    }
# === ANCHOR: DOCS_AI_ENHANCE_CALL_GEMINI_END ===


# === ANCHOR: DOCS_AI_ENHANCE_CALL_AUTO_START ===
def call_auto(source_text: str) -> dict[str, Any]:
    """키스토어에 등록된 첫 번째 provider 를 자동 선택해 호출한다."""
    for provider, env_name in _PROVIDER_PRIORITY:
        if _KEYS.get_key(env_name):
            if provider == "anthropic":
                return call_anthropic(source_text)
            if provider == "openai":
                return call_openai(source_text)
            if provider == "gemini":
                return call_gemini(source_text)
    raise RuntimeError(
        "설정 > API 키에 Anthropic/OpenAI/Gemini 중 하나의 키를 먼저 등록해주세요"
    )
# === ANCHOR: DOCS_AI_ENHANCE_CALL_AUTO_END ===
# === ANCHOR: DOCS_AI_ENHANCE_END ===
