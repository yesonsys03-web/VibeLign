from dataclasses import asdict, dataclass, field

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass
class PatchPlan:
    schema_version: int
    request: str
    interpretation: str
    target_file: str
    target_anchor: str
    source_resolution: dict[str, JsonValue] | None = None
    destination_target_file: str | None = None
    destination_target_anchor: str | None = None
    destination_resolution: dict[str, JsonValue] | None = None
    codespeak: str = ""
    intent_ir: dict[str, JsonValue] | None = None
    patch_points: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    confidence: str = "low"
    preview_available: bool = True
    clarifying_questions: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    destination_rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, JsonValue]:
        return asdict(self)
