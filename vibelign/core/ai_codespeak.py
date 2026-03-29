# === ANCHOR: AI_CODESPEAK_START ===
import importlib
import json
from typing import Protocol, cast

from vibelign.core.codespeak import CodeSpeakResult, build_codespeak_result

_AI_PATCH_POINT_KEYS = (
    "operation",
    "source",
    "destination",
    "object",
    "behavior_constraint",
)


def _coerce_ai_patch_points(raw: object) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    data = cast(dict[str, object], raw)
    out: dict[str, str] = {}
    for key in _AI_PATCH_POINT_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out or None


class AIExplainModule(Protocol):
    def generate_text_with_ai(
        self, prompt: str, quiet: bool = False
    ) -> tuple[str, list[str]]: ...


# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_START ===
def build_codespeak_ai_prompt(request: str, rule_result: CodeSpeakResult) -> str:
    return f"""다음 사용자 요청을 CodeSpeak로 해석해주세요.
# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_END ===

규칙:
- JSON만 출력하세요.
- 형식은 다음 키를 반드시 포함하세요:
  codespeak, interpretation, confidence, clarifying_questions
- 선택 키 patch_points: 객체이며 문자열 필드만 사용합니다.
  (operation, source, destination, object, behavior_constraint)
  규칙 추출이 비어 있을 때만 채워 넣으세요. 확실하지 않으면 생략합니다.
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
def _parse_codespeak_text(text: str) -> dict[str, object] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed_obj = cast(object, json.loads(text[start : end + 1]))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed_obj, dict):
        return None
    parsed = cast(dict[str, object], parsed_obj)
    codespeak = parsed.get("codespeak")
    interpretation = parsed.get("interpretation")
    confidence = parsed.get("confidence")
    clarifying_raw = parsed.get("clarifying_questions", [])
    if not isinstance(codespeak, str) or not isinstance(interpretation, str):
        return None
    if not isinstance(confidence, str):
        return None
    clarifying_questions = (
        [item for item in cast(list[object], clarifying_raw) if isinstance(item, str)]
        if isinstance(clarifying_raw, list)
        else []
    )
    out: dict[str, object] = {
        "codespeak": codespeak,
        "interpretation": interpretation,
        "confidence": confidence,
        "clarifying_questions": clarifying_questions,
    }
    pp = _coerce_ai_patch_points(parsed.get("patch_points"))
    if pp:
        out["patch_points"] = pp
    return out


# === ANCHOR: AI_CODESPEAK__PARSE_CODESPEAK_TEXT_END ===


# === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_START ===
def enhance_codespeak_with_ai(
    request: str,
    rule_result: CodeSpeakResult,
    quiet: bool = False,
    # === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_END ===
) -> CodeSpeakResult | None:
    prompt = build_codespeak_ai_prompt(request, rule_result)
    ai_explain = cast(
        AIExplainModule,
        cast(object, importlib.import_module("vibelign.core.ai_explain")),
    )
    text, _attempted = ai_explain.generate_text_with_ai(prompt, quiet=quiet)
    if not text:
        return None
    parsed = _parse_codespeak_text(text)
    if not parsed:
        return None
    codespeak = cast(str, parsed["codespeak"])
    interpretation = cast(str, parsed["interpretation"])
    confidence = cast(str, parsed["confidence"])
    clarifying_questions = cast(list[str], parsed["clarifying_questions"])
    if confidence not in {"high", "medium", "low"}:
        return None
    pp_override = cast(dict[str, str] | None, parsed.get("patch_points"))
    return build_codespeak_result(
        request,
        codespeak=codespeak,
        interpretation=interpretation,
        confidence=confidence,
        clarifying_questions=clarifying_questions,
        target_file=getattr(rule_result, "target_file", None),
        target_anchor=getattr(rule_result, "target_anchor", None),
        patch_points_override=pp_override,
    )


# === ANCHOR: AI_CODESPEAK_END ===
