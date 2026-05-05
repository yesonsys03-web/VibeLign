# === ANCHOR: MEMORY_MODELS_START ===
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


MEMORY_SCHEMA_VERSION = 1

MemorySource = Literal["explicit", "observed", "legacy", "system", "llm_proposed"]


@dataclass(frozen=True)
class MemoryTextField:
    text: str
    last_updated: str = ""
    updated_by: str = "legacy_work_memory"
    source: MemorySource = "legacy"
    stale: bool = False
    proposed: bool = False
    from_previous_intent: bool = False
    accepted_by: str = ""
    accepted_at: str = ""


@dataclass(frozen=True)
class MemoryRelevantFile:
    path: str
    why: str
    source: Literal["explicit", "observed", "llm_proposed"] = "observed"
    last_updated: str = ""
    updated_by: str = "legacy_work_memory"
    stale: bool = False
    from_previous_intent: bool = False
    accepted_by: str = ""
    accepted_at: str = ""


@dataclass(frozen=True)
class MemoryVerification:
    command: str
    result: str = ""
    last_updated: str = ""
    updated_by: str = "legacy_work_memory"
    related_files: list[str] = field(default_factory=list)
    stale: bool = False
    scope_unknown: bool = False


@dataclass(frozen=True)
class MemoryObservedContext:
    kind: str
    summary: str
    path: str = ""
    timestamp: str = ""
    source_tool: str = "legacy_work_memory"


@dataclass(frozen=True)
class MemoryState:
    schema_version: int = MEMORY_SCHEMA_VERSION
    active_intent: MemoryTextField | None = None
    decisions: list[MemoryTextField] = field(default_factory=list)
    relevant_files: list[MemoryRelevantFile] = field(default_factory=list)
    verification: list[MemoryVerification] = field(default_factory=list)
    risks: list[MemoryTextField] = field(default_factory=list)
    next_action: MemoryTextField | None = None
    observed_context: list[MemoryObservedContext] = field(default_factory=list)
    archived_decisions: list[MemoryTextField] = field(default_factory=list)
    unknown_fields: dict[str, object] = field(default_factory=dict)
    read_only: bool = False
    downgrade_warning: str = ""
# === ANCHOR: MEMORY_MODELS_END ===
