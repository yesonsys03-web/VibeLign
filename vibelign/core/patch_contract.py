# === ANCHOR: PATCH_CONTRACT_START ===
"""Patch 계약 모델 — `vib patch` / MCP가 공유하는 구조화된 계약."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import cast

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


@dataclass
# === ANCHOR: PATCH_CONTRACT_PATCHCONTRACT_START ===
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

    # === ANCHOR: PATCH_CONTRACT_TO_DICT_START ===
    def to_dict(self) -> JsonObject:
        return asdict(self)
    # === ANCHOR: PATCH_CONTRACT_TO_DICT_END ===

    @classmethod
    # === ANCHOR: PATCH_CONTRACT_FROM_CONTEXT_START ===
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
    # === ANCHOR: PATCH_CONTRACT_FROM_CONTEXT_END ===
    ) -> PatchContract:
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
# === ANCHOR: PATCH_CONTRACT_PATCHCONTRACT_END ===
                or str(patch_points.get("destination", "")),
            },
            intent_ir=intent_ir,
        )
# === ANCHOR: PATCH_CONTRACT_END ===
