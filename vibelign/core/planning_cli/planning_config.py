# vibelign/core/planning_cli/planning_config.py
# === ANCHOR: PLANNING_CONFIG_START ===
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PersonaConfig:
    enabled: bool
    provider: str | None


def _config_path() -> Path:
    return Path.home() / ".vibelign" / "gui_config.json"


def load_persona_config() -> dict[str, PersonaConfig]:
    """전역 gui_config.json 의 planning_personas 섹션을 읽는다.

    파일/섹션 부재·손상 시 빈 dict 를 반환한다(호출자가 기본값을 채운다).
    """
    path = _config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    section = data.get("planning_personas") if isinstance(data, dict) else None
    personas = section.get("personas") if isinstance(section, dict) else None
    if not isinstance(personas, dict):
        return {}
    out: dict[str, PersonaConfig] = {}
    for persona_id, entry in personas.items():
        if not isinstance(entry, dict):
            continue
        # Rust 측(as_bool().unwrap_or(true))과 동일하게 명시적 boolean False 일 때만 비활성.
        # null/0/"" 같은 비-boolean 값은 두 경로 모두 활성(true)으로 본다(파리티 보장).
        raw_enabled = entry.get("enabled", True)
        enabled = raw_enabled if isinstance(raw_enabled, bool) else True
        provider = entry.get("provider")
        out[str(persona_id)] = PersonaConfig(
            enabled=enabled,
            provider=str(provider) if isinstance(provider, str) and provider else None,
        )
    return out
# === ANCHOR: PLANNING_CONFIG_END ===
