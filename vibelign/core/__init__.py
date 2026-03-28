from dataclasses import dataclass, asdict, field
from collections.abc import Mapping
from typing import Protocol, cast

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


class SuggestionLike(Protocol):
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]


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
        suggestion: SuggestionLike,
        source_text: str = "",
        destination_text: str = "",
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
            rationale=rationale,
            source_text=source_text,
            destination_text=destination_text,
        )


@dataclass
class PatchPlan:
    schema_version: int
    request: str
    interpretation: str
    target_file: str
    target_anchor: str
    source_resolution: JsonObject | None = None
    destination_target_file: str | None = None
    destination_target_anchor: str | None = None
    destination_resolution: JsonObject | None = None
    codespeak: str = ""
    intent_ir: JsonObject | None = None
    patch_points: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    confidence: str = "low"
    preview_available: bool = True
    clarifying_questions: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    destination_rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class PatchContract:
    status: str
    contract_version: str
    intent: str
    codespeak_contract_version: int
    codespeak_parts: dict[str, str]
    patch_points: dict[str, str]
    scope: JsonObject
    allowed_ops: list[str]
    preconditions: list[str]
    expected_result: str
    assumptions: list[str]
    verification: JsonObject
    actionable: bool
    clarifying_questions: list[str]
    user_status: dict[str, str]
    user_guidance: list[str]
    move_summary: dict[str, str]
    intent_ir: JsonObject | None = None

    def to_dict(self) -> JsonObject:
        return asdict(self)

    @classmethod
    def from_context(
        cls,
        *,
        status: str,
        patch_plan: Mapping[str, object],
        codespeak_parts: dict[str, str],
        file_status: str,
        anchor_status: str,
        anchor_name: str,
        destination_file_status: str,
        destination_anchor_status: str,
        destination_file: str,
        destination_anchor: str,
        allowed_ops: list[str],
        preconditions: list[str],
        assumptions: list[str],
        clarifying_questions: list[str],
        user_status: dict[str, str],
        user_guidance: list[str],
    ) -> "PatchContract":
        patch_points_raw = patch_plan.get("patch_points")
        patch_points_data = (
            cast(dict[object, object], patch_points_raw)
            if isinstance(patch_points_raw, dict)
            else {}
        )
        patch_points = {
            str(key): str(value)
            for key, value in patch_points_data.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        intent_ir_raw = patch_plan.get("intent_ir")
        intent_ir = (
            cast(JsonObject, intent_ir_raw) if isinstance(intent_ir_raw, dict) else None
        )
        operation = str(patch_points.get("operation", "update"))
        if (
            status == "NEEDS_CLARIFICATION"
            and operation == "move"
            and (destination_file_status != "ok" or destination_anchor_status != "ok")
        ):
            assumptions = list(assumptions) + [
                "이동 대상 위치가 아직 충분히 분명하지 않습니다."
            ]
        return cls(
            status=status,
            contract_version="0.1",
            intent=str(patch_plan["interpretation"]),
            codespeak_contract_version=0,
            codespeak_parts=codespeak_parts,
            patch_points=patch_points,
            scope={
                "allowed_files": [
                    item
                    for item in [str(patch_plan["target_file"]), destination_file]
                    if item and item != "[소스 파일 없음]" and item != "None"
                ],
                "target_file_status": file_status,
                "target_anchor_status": anchor_status,
                "target_anchor_name": anchor_name,
                "destination_file_status": destination_file_status,
                "destination_anchor_status": destination_anchor_status,
                "destination_target_file": destination_file or None,
                "destination_target_anchor": destination_anchor or None,
            },
            allowed_ops=allowed_ops,
            preconditions=preconditions,
            expected_result=str(patch_plan["interpretation"]),
            assumptions=assumptions,
            verification={"commands": ["vib patch --preview", "vib guard --json"]},
            actionable=status == "READY",
            clarifying_questions=clarifying_questions,
            user_status=user_status,
            user_guidance=user_guidance,
            move_summary={
                "operation": operation,
                "source": str(patch_points.get("source", "")),
                "destination": destination_file
                or str(patch_points.get("destination", "")),
            },
            intent_ir=intent_ir,
        )
