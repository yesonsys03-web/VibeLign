# === ANCHOR: __INIT___START ===
from typing import Union

from vibelign.core.intent_ir import IntentIR

JsonScalar = Union[str, int, float, bool, None]
JsonValue = Union[JsonScalar, list["JsonValue"], dict[str, "JsonValue"]]
JsonObject = dict[str, JsonValue]


__all__ = [
    "IntentIR",
    "JsonObject",
    "JsonScalar",
    "JsonValue",
]
# === ANCHOR: __INIT___END ===
