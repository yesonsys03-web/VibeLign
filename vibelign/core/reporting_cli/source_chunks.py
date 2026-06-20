# === ANCHOR: SOURCE_CHUNKS_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, TypedDict

from vibelign.core.reporting_cli.report_quality import ReportQualityFinding

LONG_SOURCE_CHAR_THRESHOLD: Final = 40_000
LONG_SOURCE_LINE_THRESHOLD: Final = 600
CHUNK_TARGET_LINES: Final = 180
CHUNK_MIN_LINES: Final = 120
CHUNK_MAX_LINES: Final = 220

_HEADING_RE: Final = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")
_KEYWORD_RE: Final = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣_-]{1,}")
_METRIC_RE: Final = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|퍼센트|건|명|분|시간|일|원|회|배|점|개|주)")
_SIGNAL_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "evidence": ("근거", "지표", "데이터", "측정", "파일럿", "감소", "증가", "평균", "분석"),
    "risk": ("리스크", "위험", "우려", "혼선", "누락", "지연", "대응", "완화"),
    "action": ("다음 액션", "후속", "담당", "마감", "까지", "배포", "실행", "일정"),
    "audience": ("대상", "독자", "사용자", "고객", "수신자", "팀장"),
    "objective": ("목표", "목적", "개선", "달성", "줄이고"),
    "decision": ("결정", "권고", "추천", "제안", "도입", "출시", "우선"),
    "question": ("?", "？", "질문", "미결", "결정 필요"),
}
_SIGNALS_BY_FINDING: Final[dict[str, tuple[str, ...]]] = {
    "missing_audience": ("audience",),
    "missing_objective": ("objective",),
    "missing_evidence": ("evidence", "number"),
    "missing_decision_or_recommendation": ("decision",),
    "missing_risk": ("risk",),
    "missing_next_action": ("action", "date"),
    "unresolved_questions": ("question",),
    "parser_confidence": ("evidence", "risk", "action", "decision"),
}


class SourceChunkDict(TypedDict):
    chunk_id: str
    heading_path: list[str]
    start_line: int
    end_line: int
    text: str
    signals: list[str]


class SourceIndexEntryDict(TypedDict):
    chunk_id: str
    title: str
    heading_path: list[str]
    signals: list[str]
    keywords: list[str]
    start_line: int
    end_line: int


class SourceIndexDict(TypedDict):
    title: str
    is_long_source: bool
    line_count: int
    char_count: int
    outline: list[str]
    chunks: list[SourceChunkDict]
    entries: list[SourceIndexEntryDict]


@dataclass(frozen=True)
class ChunkSlice:
    lines: list[str]
    heading_paths: list[list[str]]
    start: int
    end: int


def build_source_index(text: str) -> SourceIndexDict:
    lines = text.splitlines()
    heading_paths = _heading_paths(lines)
    boundaries = _chunk_boundaries(lines)
    chunks = [
        _chunk(ChunkSlice(lines=lines, heading_paths=heading_paths, start=start, end=end), number)
        for number, (start, end) in enumerate(boundaries, start=1)
    ]
    title = _title(lines)
    return {
        "title": title,
        "is_long_source": _is_long_source(text, lines),
        "line_count": len(lines),
        "char_count": len(text),
        "outline": _outline(lines),
        "chunks": chunks,
        "entries": [_entry(chunk, title) for chunk in chunks],
    }


def retrieve_relevant_chunks(index: SourceIndexDict, finding: ReportQualityFinding) -> list[SourceChunkDict]:
    wanted = _SIGNALS_BY_FINDING.get(finding.code, ())
    scored = [(_chunk_score(chunk, wanted), chunk) for chunk in index["chunks"]]
    ranked = sorted((item for item in scored if item[0] > 0), key=lambda item: (-item[0], item[1]["start_line"]))
    if not ranked:
        ranked = sorted(scored, key=lambda item: item[1]["start_line"])[:1]
    return [chunk for _score, chunk in ranked[:5]]


def _is_long_source(text: str, lines: list[str]) -> bool:
    return len(lines) > LONG_SOURCE_LINE_THRESHOLD or len(text) > LONG_SOURCE_CHAR_THRESHOLD


def _chunk_boundaries(lines: list[str]) -> list[tuple[int, int]]:
    if not _is_long_source("\n".join(lines), lines):
        return [(0, len(lines))] if lines else []
    boundaries: list[tuple[int, int]] = []
    start = 0
    while start < len(lines):
        end = _choose_end(lines, start)
        boundaries.append((start, end))
        start = end
    return boundaries


def _choose_end(lines: list[str], start: int) -> int:
    if start + CHUNK_MAX_LINES >= len(lines):
        return len(lines)
    safe = _safe_boundaries(lines)
    min_end = min(start + CHUNK_MIN_LINES, len(lines))
    target_end = min(start + CHUNK_TARGET_LINES, len(lines))
    max_end = min(start + CHUNK_MAX_LINES, len(lines))
    for end in range(max_end, min_end - 1, -1):
        previous = lines[end - 1].strip()
        if safe[end] and (not previous or _HEADING_RE.match(previous)):
            return end
    for end in range(target_end, min_end - 1, -1):
        if safe[end]:
            return end
    return max_end


def _safe_boundaries(lines: list[str]) -> list[bool]:
    safe = [True] * (len(lines) + 1)
    in_fence = False
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
        next_line = lines[index].strip() if index < len(lines) else ""
        table_edge = stripped.startswith("|") or next_line.startswith("|")
        safe[index] = not in_fence and not table_edge
    return safe


def _heading_paths(lines: list[str]) -> list[list[str]]:
    stack: list[str] = []
    paths: list[list[str]] = []
    for line in lines:
        match = _HEADING_RE.match(line.strip())
        if match:
            level = len(match.group(1))
            stack = stack[: level - 1]
            stack.append(match.group("title").strip())
        paths.append(list(stack))
    return paths


def _chunk(source_slice: ChunkSlice, number: int) -> SourceChunkDict:
    text = "\n".join(source_slice.lines[source_slice.start : source_slice.end])
    heading_path = _first_heading_path(source_slice.heading_paths[source_slice.start : source_slice.end])
    return {
        "chunk_id": f"chunk-{number:04d}",
        "heading_path": heading_path,
        "start_line": source_slice.start + 1,
        "end_line": source_slice.end,
        "text": text,
        "signals": _signals(text),
    }


def _first_heading_path(paths: list[list[str]]) -> list[str]:
    for path in paths:
        if path:
            return path
    return []


def _entry(chunk: SourceChunkDict, title: str) -> SourceIndexEntryDict:
    return {
        "chunk_id": chunk["chunk_id"],
        "title": title,
        "heading_path": chunk["heading_path"],
        "signals": chunk["signals"],
        "keywords": _keywords(chunk["text"]),
        "start_line": chunk["start_line"],
        "end_line": chunk["end_line"],
    }


def _title(lines: list[str]) -> str:
    for line in lines:
        match = _HEADING_RE.match(line.strip())
        if match and len(match.group(1)) == 1:
            return match.group("title").strip()
    return ""


def _outline(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if _HEADING_RE.match(line.strip())]


def _signals(text: str) -> list[str]:
    found = [name for name, words in _SIGNAL_WORDS.items() if any(word in text for word in words)]
    if _METRIC_RE.search(text):
        found.append("number")
    if re.search(r"\d{4}-\d{2}-\d{2}", text):
        found.append("date")
    return sorted(set(found))


def _keywords(text: str) -> list[str]:
    return sorted(set(_KEYWORD_RE.findall(text)))[:24]


def _chunk_score(chunk: SourceChunkDict, wanted: tuple[str, ...]) -> int:
    signals = set(chunk["signals"])
    score = sum(10 for signal in wanted if signal in signals)
    score += min(len(signals), 4)
    score += _heading_relevance(chunk, wanted)
    return score


def _heading_relevance(chunk: SourceChunkDict, wanted: tuple[str, ...]) -> int:
    heading_text = " ".join(chunk["heading_path"])
    heading_signals = set(_signals(heading_text))
    return sum(2 for signal in wanted if signal in heading_signals)
# === ANCHOR: SOURCE_CHUNKS_END ===
