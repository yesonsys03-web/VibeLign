# === ANCHOR: AI_CODESPEAK_START ===
import importlib
import json
from typing import Protocol, cast

from vibelign.core.codespeak import (
    ACTION_MAP,
    CodeSpeakResult,
    build_codespeak_result,
)

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
def build_codespeak_ai_prompt(
    request: str,
    rule_result: CodeSpeakResult,
    *,
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
) -> str:
    if target_file is not None and target_anchor is not None:
        rationale_lines = "\n".join(
            f"  - {r}" for r in (target_rationale or [])
        )
        context_block = f"""patch_suggester가 찾은 수정 위치:
- 파일: {target_file}
- 앵커: {target_anchor}
- confidence: {target_confidence or 'unknown'}
- 근거:
{rationale_lines}

이 정보를 바탕으로 앵커 이름에서 layer, subject를 추론하고,
요청 문맥에서 action을 판단하세요."""
    else:
        context_block = f"""현재 규칙 기반 해석:
- codespeak: {rule_result.codespeak}
- interpretation: {rule_result.interpretation}
- confidence: {rule_result.confidence}"""
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
- `action`은 다음 어휘 중 하나만 사용하세요: add, remove, update, move, fix, apply, split.
  (예: persistence_enable, enable, disable 같은 임의 동사는 금지)
- `move`는 코드 블록을 다른 파일/위치로 실제 이동할 때만 사용하세요.
  사용자가 화면 이동이나 네비게이션을 설명하는 문맥("이동하면", "돌아가면", "넘어가면")에서는
  move가 아니라 fix 또는 update를 선택하세요.
- `subject`는 한글 없이 영문 snake_case 만 허용합니다.
- confidence 는 high, medium, low 중 하나입니다.
- clarifying_questions 는 문자열 배열입니다.
- 한국어 interpretation 을 작성하세요.

사용자 요청:
{request}

{context_block}

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
    *,
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
    # === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_END ===
) -> CodeSpeakResult | None:
    prompt = build_codespeak_ai_prompt(
        request,
        rule_result,
        target_file=target_file,
        target_anchor=target_anchor,
        target_confidence=target_confidence,
        target_rationale=target_rationale,
    )
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
    cs_parts = codespeak.split(".")
    if len(cs_parts) == 4 and cs_parts[3] not in ACTION_MAP:
        # 규칙 기반 fallback: AI가 ACTION_MAP 밖의 자유 동사를 만들면 무시한다.
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
