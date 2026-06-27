# === ANCHOR: MODELS_START ===
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
# === ANCHOR: MODELS_PLANNINGDATA_START ===
class PlanningData:
    """기획안 .md 에서 추출한 정규화 데이터 (포맷·종류 무관)."""

    title: str = ""
    idea: str = ""
    target_users: str = ""
    problem: str = ""
    features: list[str] = field(default_factory=list)
    flows: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    context_notes: str = ""
# === ANCHOR: MODELS_PLANNINGDATA_END ===


@dataclass
# === ANCHOR: MODELS_BLOCK_START ===
class Block:
    """보고서 본문 블록. kind 에 따라 text 또는 items 사용."""

    kind: str  # "paragraph" | "bullets" | "summary"
    text: str = ""
    items: list[str] = field(default_factory=list)
# === ANCHOR: MODELS_BLOCK_END ===


@dataclass
# === ANCHOR: MODELS_SECTION_START ===
class Section:
    heading: str
    blocks: list[Block] = field(default_factory=list)
# === ANCHOR: MODELS_SECTION_END ===


@dataclass
# === ANCHOR: MODELS_REPORTMODEL_START ===
class ReportModel:
    """포맷 독립 보고서 IR. 렌더러가 이걸 받아 PDF/Word/PPT 로 그린다."""

    title: str
    report_type: str
    date: str
    source_plan_path: str = ""
    author: str = ""
    sections: list[Section] = field(default_factory=list)
# === ANCHOR: MODELS_REPORTMODEL_END ===
# === ANCHOR: MODELS_END ===
