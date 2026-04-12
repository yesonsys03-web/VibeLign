# === ANCHOR: PATCH_TARGETING_START ===
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.codespeak import CodeSpeakResult
from vibelign.core.patch_suggester import resolve_target_for_role
from vibelign.core.patch_suggester import suggest_patch_for_role
from vibelign.core.patch_suggester import tokenize


# === ANCHOR: PATCH_TARGETING_SUGGESTIONLIKE_START ===
class SuggestionLike(Protocol):
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
# === ANCHOR: PATCH_TARGETING_SUGGESTIONLIKE_END ===


# === ANCHOR: PATCH_TARGETING_RESOLUTIONLIKE_START ===
class ResolutionLike(Protocol):
    # === ANCHOR: PATCH_TARGETING_TO_DICT_START ===
# === ANCHOR: PATCH_TARGETING_RESOLUTIONLIKE_END ===
    def to_dict(self) -> dict[str, object]: ...
    # === ANCHOR: PATCH_TARGETING_TO_DICT_END ===


# === ANCHOR: PATCH_TARGETING_AIEXPLAINLIKE_START ===
class AIExplainLike(Protocol):
    # === ANCHOR: PATCH_TARGETING_HAS_AI_PROVIDER_START ===
# === ANCHOR: PATCH_TARGETING_AIEXPLAINLIKE_END ===
    def has_ai_provider(self) -> bool: ...
    # === ANCHOR: PATCH_TARGETING_HAS_AI_PROVIDER_END ===


# === ANCHOR: PATCH_TARGETING_AICODESPEAKLIKE_START ===
class AICodeSpeakLike(Protocol):
    # === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_WITH_AI_START ===
    def enhance_codespeak_with_ai(
        self,
        request: str,
        rule_result: object,
        quiet: bool = False,
        *,
        target_file: str | None = None,
        target_anchor: str | None = None,
        target_confidence: str | None = None,
        target_rationale: list[str] | None = None,
# === ANCHOR: PATCH_TARGETING_AICODESPEAKLIKE_END ===
    # === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_WITH_AI_END ===
    ) -> object | None: ...


# === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_START ===
def enhance_codespeak(
    request: str,
    codespeak: CodeSpeakResult,
    *,
    use_ai: bool,
    quiet_ai: bool,
    import_module: Callable[[str], object],
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
# === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_END ===
) -> CodeSpeakResult:
    if not use_ai:
        return codespeak
    ai_codespeak = cast(AICodeSpeakLike, import_module("vibelign.core.ai_codespeak"))
    ai_explain = cast(AIExplainLike, import_module("vibelign.core.ai_explain"))
    if not ai_explain.has_ai_provider():
        return codespeak
    try:
        enhanced = ai_codespeak.enhance_codespeak_with_ai(
            request, codespeak, quiet=quiet_ai,
            target_file=target_file,
            target_anchor=target_anchor,
            target_confidence=target_confidence,
            target_rationale=target_rationale,
        )
    except Exception:
        enhanced = None
    return cast(CodeSpeakResult, enhanced) if enhanced is not None else codespeak


# === ANCHOR: PATCH_TARGETING_RESOLVE_PATCH_TARGETING_START ===
def resolve_patch_targeting(
    root: Path,
    request: str,
    codespeak: CodeSpeakResult,
    *,
    use_ai: bool,
    coerce_json_object: Callable[[object], dict[str, object] | None],
# === ANCHOR: PATCH_TARGETING_RESOLVE_PATCH_TARGETING_END ===
) -> dict[str, object]:
    source_text = request
    source_resolution = None
    if codespeak.patch_points.get("operation") == "move":
        extracted_source = str(codespeak.patch_points.get("source", "")).strip()
        if extracted_source:
            source_text = extracted_source
            if len(tokenize(source_text)) < 4:
                source_text = request
    suggestion = suggest_patch_for_role(root, source_text, role="source", use_ai=use_ai)
    source_resolution_obj = cast(
        ResolutionLike | None,
        resolve_target_for_role(root, source_text, role="source", use_ai=use_ai),
    )
    source_resolution = coerce_json_object(
        source_resolution_obj.to_dict() if source_resolution_obj else None
    )
    destination_suggestion = None
    destination_resolution = None
    if codespeak.patch_points.get("operation") == "move":
        destination_text = str(codespeak.patch_points.get("destination", "")).strip()
        if destination_text:
            destination_suggestion = suggest_patch_for_role(
                root, destination_text, use_ai=use_ai, role="destination"
            )
            destination_resolution_obj = cast(
                ResolutionLike | None,
                resolve_target_for_role(
                    root, destination_text, role="destination", use_ai=use_ai
                ),
            )
            destination_resolution = coerce_json_object(
                destination_resolution_obj.to_dict()
                if destination_resolution_obj
                else None
            )
    confidence = suggestion.confidence
    if confidence == "high" and codespeak.confidence != "high":
        confidence = codespeak.confidence
    if (
        codespeak.patch_points.get("operation") == "move"
        and suggestion.target_file != "[소스 파일 없음]"
        and suggestion.target_anchor not in {"[없음]", "[먼저 앵커를 추가하세요]"}
        and destination_suggestion is not None
        and getattr(destination_suggestion, "target_file", "")
        not in {"", "[소스 파일 없음]"}
        and getattr(destination_suggestion, "target_anchor", "")
        not in {
            "",
            "[없음]",
            "[먼저 앵커를 추가하세요]",
        }
        and confidence == "low"
    ):
        confidence = "medium"
    return {
        "suggestion": suggestion,
        "source_resolution": source_resolution,
        "destination_suggestion": destination_suggestion,
        "destination_resolution": destination_resolution,
        "confidence": confidence,
    }
# === ANCHOR: PATCH_TARGETING_END ===
