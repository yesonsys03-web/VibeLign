# === ANCHOR: PATCH_PLAN_START ===
from dataclasses import asdict, dataclass, field

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass
# === ANCHOR: PATCH_PLAN_PATCHSTEP_START ===
class PatchStep:
    ordinal: int
    intent_text: str
    codespeak: str | None = None
    target_file: str = ""
    target_anchor: str = ""
    context_snippet: str | None = None
    allowed_ops: list[str] = field(default_factory=list)
    depends_on: int | list[int] | None = None
    status: str = "NEEDS_CLARIFICATION"
    search_fingerprint: str | None = None
# === ANCHOR: PATCH_PLAN_PATCHSTEP_END ===


@dataclass
# === ANCHOR: PATCH_PLAN_PATCHPLAN_START ===
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
    sub_intents: list[str] | None = None
    pending_sub_intents: list[str] | None = None
    constraints: list[str] = field(default_factory=list)
    confidence: str = "low"
    preview_available: bool = True
    clarifying_questions: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    destination_rationale: list[str] = field(default_factory=list)
    related_files: list[dict[str, JsonValue]] = field(default_factory=list)
    steps: list[PatchStep] | None = None

    # === ANCHOR: PATCH_PLAN_TO_DICT_START ===
    def to_dict(self) -> dict[str, JsonValue]:
# === ANCHOR: PATCH_PLAN_PATCHPLAN_END ===
        return asdict(self)
    # === ANCHOR: PATCH_PLAN_TO_DICT_END ===
# === ANCHOR: PATCH_PLAN_END ===
