from dataclasses import dataclass, field, asdict


@dataclass
class IntentIR:
    raw_request: str
    operation: str
    source: str = ""
    destination: str = ""
    behavior_constraint: str = ""
    layer: str = ""
    target: str = ""
    subject: str = ""
    action: str = ""
    confidence: str = "low"
    clarifying_questions: list[str] = field(default_factory=list)

    def to_patch_points(self) -> dict[str, str]:
        return {
            "operation": self.operation,
            "source": self.source,
            "destination": self.destination,
            "object": self.source,
            "behavior_constraint": self.behavior_constraint,
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
