# === ANCHOR: TARGET_RESOLUTION_START ===
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
# === ANCHOR: TARGET_RESOLUTION_TARGETRESOLUTION_START ===
class TargetResolution:
    role: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
    source_text: str = ""
    destination_text: str = ""

    # === ANCHOR: TARGET_RESOLUTION_TO_DICT_START ===
    def to_dict(self) -> dict[str, object]:
        return asdict(self)
    # === ANCHOR: TARGET_RESOLUTION_TO_DICT_END ===

    @classmethod
    # === ANCHOR: TARGET_RESOLUTION_FROM_SUGGESTION_START ===
    def from_suggestion(
        cls,
        role: str,
        suggestion: object,
        source_text: str = "",
        destination_text: str = "",
    # === ANCHOR: TARGET_RESOLUTION_FROM_SUGGESTION_END ===
    ) -> Optional["TargetResolution"]:
        target_file = getattr(suggestion, "target_file", None)
        target_anchor = getattr(suggestion, "target_anchor", None)
        confidence = getattr(suggestion, "confidence", None)
        rationale = getattr(suggestion, "rationale", None)
        if not isinstance(target_file, str) or not isinstance(target_anchor, str):
            return None
        if not isinstance(confidence, str):
            confidence = "low"
        if not isinstance(rationale, list):
            rationale = []
        return cls(
            role=role,
            target_file=target_file,
            target_anchor=target_anchor,
            confidence=confidence,
# === ANCHOR: TARGET_RESOLUTION_TARGETRESOLUTION_END ===
            rationale=[str(item) for item in rationale if isinstance(item, str)],
            source_text=source_text,
            destination_text=destination_text,
        )
# === ANCHOR: TARGET_RESOLUTION_END ===
