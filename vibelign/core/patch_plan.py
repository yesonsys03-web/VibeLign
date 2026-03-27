from dataclasses import dataclass, asdict, field
from typing import Any, Optional


@dataclass
class PatchPlan:
    schema_version: int
    request: str
    interpretation: str
    target_file: str
    target_anchor: str
    source_resolution: Optional[dict[str, Any]] = None
    destination_target_file: Optional[str] = None
    destination_target_anchor: Optional[str] = None
    destination_resolution: Optional[dict[str, Any]] = None
    codespeak: str = ""
    intent_ir: Optional[dict[str, Any]] = None
    patch_points: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    confidence: str = "low"
    preview_available: bool = True
    clarifying_questions: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    destination_rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
