from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TargetResolution:
    role: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
    source_text: str = ""
    destination_text: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_suggestion(
        cls,
        role: str,
        suggestion: object,
        source_text: str = "",
        destination_text: str = "",
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
            rationale=[str(item) for item in rationale if isinstance(item, str)],
            source_text=source_text,
            destination_text=destination_text,
        )
