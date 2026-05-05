import json
from pathlib import Path
from typing import cast

from vibelign.commands.vib_memory_cmd import _memory_state_payload
from vibelign.commands.vib_recover_cmd import _plan_payload
from vibelign.core.memory.models import MEMORY_SCHEMA_VERSION
from vibelign.core.memory.models import MemoryState
from vibelign.core.recovery.models import RecoverySignalSet
from vibelign.core.recovery.planner import build_recovery_plan
from vibelign.core.schema_contracts import SchemaContractError
from vibelign.core.schema_contracts import validate_memory_state_payload
from vibelign.core.schema_contracts import validate_recovery_plan_payload
from vibelign.mcp.mcp_recovery_handlers import _plan_to_payload


def test_memory_state_schema_matches_current_schema_version() -> None:
    schema = _schema("vibelign/core/memory/memory_state.schema.json")
    properties = cast(dict[str, object], schema["properties"])
    schema_version = cast(dict[str, object], properties["schema_version"])

    assert schema["title"] == "VibeLign Memory State"
    assert schema_version["const"] == MEMORY_SCHEMA_VERSION
    assert "schema_version" in cast(list[str], schema["required"])
    assert {"decisions", "relevant_files", "verification"}.issubset(properties)


def test_recovery_plan_schema_matches_recovery_model_literals() -> None:
    schema = _schema("vibelign/core/recovery/recovery_plan.schema.json")
    properties = cast(dict[str, object], schema["properties"])
    mode = cast(dict[str, object], properties["mode"])
    circuit_breaker_state = cast(dict[str, object], properties["circuit_breaker_state"])

    assert schema["title"] == "VibeLign Recovery Plan"
    assert mode["enum"] == ["read_only", "apply_preview", "apply"]
    assert circuit_breaker_state["enum"] == ["active", "degraded"]
    assert cast(list[str], schema["required"]) == ["plan_id", "mode", "level", "summary"]


def test_recovery_plan_schema_supports_ranked_candidates() -> None:
    schema = _schema("vibelign/core/recovery/recovery_plan.schema.json")
    properties = cast(dict[str, object], schema["properties"])

    assert "ranked_candidates" in properties
    assert "recommendation_provider" in properties


def test_schema_contracts_are_included_in_pyinstaller_datas() -> None:
    spec_text = (Path(__file__).resolve().parents[1] / "vib.spec").read_text(encoding="utf-8")

    assert "vibelign/core/memory/memory_state.schema.json" in spec_text
    assert "vibelign/core/recovery/recovery_plan.schema.json" in spec_text


def test_real_memory_payload_matches_memory_schema_required_fields() -> None:
    payload = _memory_state_payload(MemoryState())
    schema = _schema("vibelign/core/memory/memory_state.schema.json")

    _assert_required_fields(payload, schema)
    validate_memory_state_payload(payload)
    assert payload["schema_version"] == MEMORY_SCHEMA_VERSION


def test_real_recovery_payloads_match_recovery_schema_required_fields() -> None:
    plan = build_recovery_plan(RecoverySignalSet())
    schema = _schema("vibelign/core/recovery/recovery_plan.schema.json")
    cli_payload = _plan_payload(plan)
    mcp_payload = _plan_to_payload(plan)
    cli_payload["p0_summaries"] = [_valid_p0_summary()]

    _assert_required_fields(cli_payload, schema)
    _assert_required_fields(mcp_payload, schema)
    validate_recovery_plan_payload(cli_payload)
    validate_recovery_plan_payload(mcp_payload)
    assert cli_payload["circuit_breaker_state"] == "active"
    assert mcp_payload["circuit_breaker_state"] == "active"
    assert cli_payload["ranked_candidates"] == []
    assert mcp_payload["ranked_candidates"] == []


def test_runtime_schema_validation_rejects_invalid_real_payloads() -> None:
    memory_payload = _memory_state_payload(MemoryState())
    recovery_payload = _plan_payload(build_recovery_plan(RecoverySignalSet()))
    memory_payload["schema_version"] = 2
    recovery_payload.pop("plan_id")

    try:
        validate_memory_state_payload(memory_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("memory schema validation accepted an invalid schema version")

    try:
        validate_recovery_plan_payload(recovery_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("recovery schema validation accepted a missing plan_id")


def test_runtime_schema_validation_rejects_unknown_fields_and_invalid_payload_extensions() -> None:
    memory_payload = _memory_state_payload(MemoryState())
    recovery_payload = _plan_payload(build_recovery_plan(RecoverySignalSet()))
    memory_payload["unexpected"] = True
    recovery_payload["p0_summaries"] = [{"slo_id": "sandwich_enforcement"}]

    try:
        validate_memory_state_payload(memory_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("memory schema validation accepted an unknown field")

    try:
        validate_recovery_plan_payload(recovery_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("recovery schema validation accepted an invalid p0_summaries item")


def test_runtime_schema_validation_rejects_nested_unknown_fields() -> None:
    memory_payload = _memory_state_payload(MemoryState())
    recovery_payload = _plan_payload(build_recovery_plan(RecoverySignalSet()))
    memory_payload["active_intent"] = {"text": "goal", "unexpected": True}
    nested_p0 = _valid_p0_summary()
    nested_p0["unexpected"] = True
    recovery_payload["p0_summaries"] = [nested_p0]

    try:
        validate_memory_state_payload(memory_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("memory schema validation accepted a nested unknown field")

    try:
        validate_recovery_plan_payload(recovery_payload)
    except SchemaContractError:
        pass
    else:
        raise AssertionError("recovery schema validation accepted a nested unknown field")


def _schema(relative_path: str) -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / relative_path
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _assert_required_fields(payload: dict[str, object], schema: dict[str, object]) -> None:
    required = cast(list[str], schema.get("required", []))
    properties = cast(dict[str, object], schema.get("properties", {}))
    for field in required:
        assert field in payload
    for field in payload:
        if field in properties:
            continue
        assert field.startswith("downgrade_")


def _valid_p0_summary() -> dict[str, object]:
    return {
        "slo_id": "sandwich_enforcement",
        "window_start": "2026-01-01T00:00:00Z",
        "window_end": "2026-01-02T00:00:00Z",
        "occurrences": 0,
        "sample_count": 1,
        "result": "pass",
        "corrupt_rows_count": 0,
        "warning": "",
    }
