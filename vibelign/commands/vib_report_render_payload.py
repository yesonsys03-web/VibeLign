# === ANCHOR: VIB_REPORT_RENDER_PAYLOAD_START ===
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from vibelign.core.reporting_cli.model_json import model_from_dict
from vibelign.core.reporting_cli.models import ReportModel

RENDER_PAYLOAD_PATH_ENV = "VIBELIGN_REPORT_RENDER_PAYLOAD_PATH"
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class RenderPayloadFormatError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class RenderPayloadModels:
    key: str
    base: ReportModel
    polished: ReportModel


def load_render_payload_models_from_env(polish_key: str | None) -> RenderPayloadModels | None:
    payload_path = os.environ.get(RENDER_PAYLOAD_PATH_ENV, "").strip()
    if not payload_path:
        return None
    return _load_render_payload_models(payload_path, polish_key)


def _load_render_payload_models(payload_path: str, polish_key: str | None) -> RenderPayloadModels:
    payload: JsonValue = json.loads(Path(payload_path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RenderPayloadFormatError("payload status is not ok")
    try:
        key = _require_payload_key(payload, polish_key)
        _require_string_title(payload["base"], "base")
        _require_string_title(payload["polished"], "polished")
        return RenderPayloadModels(
            key=key,
            base=model_from_dict(payload["base"]),
            polished=model_from_dict(payload["polished"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderPayloadFormatError(str(exc)) from exc


def _require_string_title(raw_model: JsonValue, label: str) -> None:
    if not isinstance(raw_model, dict):
        raise RenderPayloadFormatError(f"{label} model must be an object")
    if not isinstance(raw_model.get("title"), str):
        raise RenderPayloadFormatError(f"{label}.title must be a string")


def _require_payload_key(payload: dict[str, JsonValue], polish_key: str | None) -> str:
    if not polish_key:
        raise RenderPayloadFormatError("polish-key 가 필요해요(emit 응답의 key 값).")
    payload_key = payload.get("key")
    if not isinstance(payload_key, str) or not payload_key:
        raise RenderPayloadFormatError("payload.key must be a non-empty string")
    if payload_key != polish_key:
        raise RenderPayloadFormatError("payload.key does not match polish-key")
    return payload_key
# === ANCHOR: VIB_REPORT_RENDER_PAYLOAD_END ===
