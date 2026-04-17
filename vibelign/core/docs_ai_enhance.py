# === ANCHOR: DOCS_AI_ENHANCE_START ===
"""단일 markdown 문서에 대해 LLM 을 호출해 구조화된 요약 필드를 돌려준다.

Anthropic Messages API 기반. OpenAI/Gemini 어댑터는 후속 과제.
네트워크 호출은 vibelign.core.http_retry 를 통해 재시도한다.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from . import http_retry as _HTTP_RETRY
from . import keys_store as _KEYS


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
def call_anthropic(source_text: str, *, model: str = "claude-sonnet-4-5") -> dict[str, Any]:
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
# === ANCHOR: DOCS_AI_ENHANCE_END ===
