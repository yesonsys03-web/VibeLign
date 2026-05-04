# === ANCHOR: SCHEMA_CONTRACTS_START ===
from __future__ import annotations

import json
from importlib import resources
from typing import cast


class SchemaContractError(ValueError):
    pass


def validate_memory_state_payload(payload: dict[str, object]) -> None:
    _validate_payload(payload, _load_schema("vibelign.core.memory", "memory_state.schema.json"), "$")


def validate_recovery_plan_payload(payload: dict[str, object]) -> None:
    _validate_payload(payload, _load_schema("vibelign.core.recovery", "recovery_plan.schema.json"), "$")


def _load_schema(package: str, filename: str) -> dict[str, object]:
    text = resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    return cast(dict[str, object], json.loads(text))


def _validate_payload(value: object, schema: dict[str, object], path: str, root: dict[str, object] | None = None) -> None:
    schema_root = root or schema
    ref = schema.get("$ref")
    if isinstance(ref, str):
        _validate_payload(value, _resolve_ref(schema_root, ref), path, schema_root)
        return

    if "const" in schema and value != schema["const"]:
        raise SchemaContractError(f"{path} must equal {schema['const']!r}")
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        raise SchemaContractError(f"{path} must be one of {enum!r}")

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        raise SchemaContractError(f"{path} has invalid type")

    if isinstance(value, dict):
        object_value = cast(dict[str, object], value)
        for required in cast(list[str], schema.get("required", [])):
            if required not in object_value:
                raise SchemaContractError(f"{path}.{required} is required")
        properties = cast(dict[str, object], schema.get("properties", {}))
        if schema.get("additionalProperties") is False:
            extra = sorted(set(object_value).difference(properties))
            if extra:
                raise SchemaContractError(f"{path} has unknown fields: {', '.join(extra)}")
        for key, child in properties.items():
            if key in object_value and isinstance(child, dict):
                _validate_payload(object_value[key], cast(dict[str, object], child), f"{path}.{key}", schema_root)

    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, item in enumerate(value):
                _validate_payload(item, cast(dict[str, object], items), f"{path}[{index}]", schema_root)

    minimum = schema.get("minimum")
    if isinstance(minimum, int | float) and isinstance(value, int | float) and value < minimum:
        raise SchemaContractError(f"{path} must be >= {minimum}")


def _resolve_ref(root: dict[str, object], ref: str) -> dict[str, object]:
    if not ref.startswith("#/"):
        raise SchemaContractError(f"unsupported schema ref: {ref}")
    current: object = root
    for part in ref[2:].split("/"):
        if not isinstance(current, dict):
            raise SchemaContractError(f"invalid schema ref: {ref}")
        current = cast(dict[str, object], current)[part]
    return cast(dict[str, object], current)


def _matches_type(value: object, expected_type: object) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(value, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True
# === ANCHOR: SCHEMA_CONTRACTS_END ===
