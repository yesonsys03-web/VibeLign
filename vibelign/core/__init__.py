# === ANCHOR: __INIT___START ===
from dataclasses import asdict, dataclass
from collections.abc import Mapping
from typing import Protocol, cast

from vibelign.core.intent_ir import IntentIR
from vibelign.core.patch_contract import PatchContract
from vibelign.core.patch_plan import PatchPlan, PatchStep

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


# === ANCHOR: __INIT___SUGGESTIONLIKE_START ===
class SuggestionLike(Protocol):
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
# === ANCHOR: __INIT___SUGGESTIONLIKE_END ===


@dataclass
# === ANCHOR: __INIT___TARGETRESOLUTION_START ===
class TargetResolution:
    role: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
    source_text: str = ""
    destination_text: str = ""

    # === ANCHOR: __INIT___TO_DICT_START ===
    def to_dict(self) -> dict[str, object]:
        return asdict(self)
    # === ANCHOR: __INIT___TO_DICT_END ===

    @classmethod
    # === ANCHOR: __INIT___FROM_SUGGESTION_START ===
    def from_suggestion(
        cls,
        role: str,
        suggestion: SuggestionLike,
        source_text: str = "",
        destination_text: str = "",
    # === ANCHOR: __INIT___FROM_SUGGESTION_END ===
    ) -> "TargetResolution | None":
        target_file = suggestion.target_file
        target_anchor = suggestion.target_anchor
        confidence = suggestion.confidence
        rationale = suggestion.rationale
        return cls(
            role=role,
            target_file=target_file,
            target_anchor=target_anchor,
            confidence=confidence,
# === ANCHOR: __INIT___TARGETRESOLUTION_END ===
            rationale=rationale,
            source_text=source_text,
            destination_text=destination_text,
        )


__all__ = [
    "IntentIR",
    "JsonObject",
    "JsonScalar",
    "JsonValue",
    "PatchContract",
    "PatchPlan",
    "PatchStep",
    "SuggestionLike",
    "TargetResolution",
]
# === ANCHOR: __INIT___END ===
