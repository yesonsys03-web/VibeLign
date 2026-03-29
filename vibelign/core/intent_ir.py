# === ANCHOR: INTENT_IR_START ===
from dataclasses import dataclass, field, asdict


@dataclass
# === ANCHOR: INTENT_IR_INTENTIR_START ===
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

    # === ANCHOR: INTENT_IR_TO_PATCH_POINTS_START ===
    def to_patch_points(self) -> dict[str, str]:
        return {
            "operation": self.operation,
            "source": self.source,
            "destination": self.destination,
            "object": self.source,
            "behavior_constraint": self.behavior_constraint,
        }
    # === ANCHOR: INTENT_IR_TO_PATCH_POINTS_END ===

# === ANCHOR: INTENT_IR_INTENTIR_END ===
    # === ANCHOR: INTENT_IR_TO_DICT_START ===
    def to_dict(self) -> dict[str, object]:
        return asdict(self)
    # === ANCHOR: INTENT_IR_TO_DICT_END ===
# === ANCHOR: INTENT_IR_END ===
