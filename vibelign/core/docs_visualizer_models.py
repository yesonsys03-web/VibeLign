# === ANCHOR: DOCS_VISUALIZER_MODELS_START ===
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_VISUALSECTION_START ===
class VisualSection:
    id: str
    title: str
    level: int
    summary: str = ""
    body_preview: list[str] = field(default_factory=list)
# === ANCHOR: DOCS_VISUALIZER_VISUALSECTION_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_GLOSSARYENTRY_START ===
class GlossaryEntry:
    term: str
    definition: str
# === ANCHOR: DOCS_VISUALIZER_GLOSSARYENTRY_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_ACTIONITEM_START ===
class ActionItem:
    text: str
    checked: bool = False
# === ANCHOR: DOCS_VISUALIZER_ACTIONITEM_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMBLOCK_START ===
class DiagramBlock:
    id: str
    kind: str
    title: str = ""
    source: str = ""
    provenance: str = "authored"
    generator: str = ""
    confidence: str = "high"
    warnings: list[str] = field(default_factory=list)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMBLOCK_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_START ===
class HeuristicEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "heuristic"
    generator: str = "heuristic-v3"
    generated_at: str = ""
# === ANCHOR: DOCS_VISUALIZER_HEURISTICFIELDS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_START ===
class AIEnhancedFields:
    tldr_one_liner: str = ""
    key_rules: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    provenance: str = "ai_draft"
    model: str = ""
    provider: str = ""
    generated_at: str = ""
    source_hash: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
# === ANCHOR: DOCS_VISUALIZER_AIFIELDS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_START ===
class DocsVisualArtifact:
    source_path: str
    source_hash: str
    generated_at: str
    generator_version: str
    schema_version: int
    title: str
    summary: str
    sections: list[VisualSection] = field(default_factory=list)
    glossary: list[GlossaryEntry] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    diagram_blocks: list[DiagramBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    heuristic_fields: Optional["HeuristicEnhancedFields"] = None
    ai_fields: Optional["AIEnhancedFields"] = None

    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_START ===
    def to_dict(self) -> dict[str, Any]:
# === ANCHOR: DOCS_VISUALIZER_DOCSVISUALARTIFACT_END ===
        return asdict(self)
    # === ANCHOR: DOCS_VISUALIZER_TO_DICT_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMSIGNALS_START ===
class DiagramSignals:
    title: str
    summary: str
    top_headings: list[str]
    ordered_steps: list[str]
    checklist_steps: list[str]
    decision_lines: list[str]
    file_like_items: list[str]
    table_rows: list[list[str]]
    readme_override: bool = False
    overview_override: bool = False
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMSIGNALS_END ===


@dataclass(frozen=True)
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMCANDIDATE_START ===
class DiagramCandidate:
    name: str
    title: str
    source: str
    generator: str
    confidence: str
    warnings: list[str]
    score: int
    supported: bool = True
# === ANCHOR: DOCS_VISUALIZER_DIAGRAMCANDIDATE_END ===
# === ANCHOR: DOCS_VISUALIZER_MODELS_END ===
