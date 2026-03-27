# === ANCHOR: AI_CODESPEAK_START ===
import importlib
import json
from typing import Any, Dict, List, Optional, cast

from vibelign.core.codespeak import CodeSpeakResult, parse_codespeak_v0


# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_START ===
def build_codespeak_ai_prompt(request: str, rule_result: CodeSpeakResult) -> str:
    return f"""다음 사용자 요청을 CodeSpeak로 해석해주세요.
# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_END ===

규칙:
- JSON만 출력하세요.
- 형식은 다음 키를 반드시 포함하세요:
  codespeak, interpretation, confidence, clarifying_questions
- `codespeak`는 layer.target.subject.action 형식만 허용합니다.
- confidence 는 high, medium, low 중 하나입니다.
- clarifying_questions 는 문자열 배열입니다.
- 한국어 interpretation 을 작성하세요.

사용자 요청:
{request}

현재 규칙 기반 해석:
- codespeak: {rule_result.codespeak}
- interpretation: {rule_result.interpretation}
- confidence: {rule_result.confidence}

출력 예시:
{{
  "codespeak": "ui.component.progress_bar.add",
  "interpretation": "진행 상태를 보여주는 progress bar를 UI에 추가하는 요청으로 해석했습니다.",
  "confidence": "high",
  "clarifying_questions": []
}}
"""


# === ANCHOR: AI_CODESPEAK__PARSE_CODESPEAK_TEXT_START ===
def _parse_codespeak_text(text: str) -> Optional[Dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(Dict[str, Any], parsed)


# === ANCHOR: AI_CODESPEAK__PARSE_CODESPEAK_TEXT_END ===


# === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_START ===
def enhance_codespeak_with_ai(
    request: str,
    rule_result: CodeSpeakResult,
    quiet: bool = False,
    # === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_END ===
) -> Optional[CodeSpeakResult]:
    prompt = build_codespeak_ai_prompt(request, rule_result)
    ai_explain = importlib.import_module("vibelign.core.ai_explain")
    text, _attempted = ai_explain.generate_text_with_ai(prompt, quiet=quiet)
    if not text:
        return None
    parsed = _parse_codespeak_text(text)
    if not parsed:
        return None
    codespeak = parsed.get("codespeak")
    interpretation = parsed.get("interpretation")
    confidence = parsed.get("confidence")
    clarifying_questions = parsed.get("clarifying_questions", [])
    if not isinstance(codespeak, str) or not isinstance(interpretation, str):
        return None
    if not isinstance(confidence, str) or confidence not in {"high", "medium", "low"}:
        return None
    if not isinstance(clarifying_questions, list):
        clarifying_questions = []
    parts = parse_codespeak_v0(codespeak)
    if parts is None:
        return None
    return CodeSpeakResult(
        codespeak=codespeak,
        layer=parts["layer"],
        target=parts["target"],
        subject=parts["subject"],
        action=parts["action"],
        confidence=confidence,
        interpretation=interpretation,
        clarifying_questions=[
            str(item) for item in clarifying_questions if isinstance(item, str)
        ],
        patch_points=dict(getattr(rule_result, "patch_points", {})),
    )


# === ANCHOR: AI_CODESPEAK_END ===
