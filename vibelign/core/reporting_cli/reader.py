from __future__ import annotations

import re

from vibelign.core.reporting_cli.models import PlanningData

_FIELD_BY_HEADING = {
    "한 줄 목표": "idea",
    "만들고 싶은 이유": "problem",
    "대상 사용자": "target_users",
    "핵심 문제": "problem",
    "핵심 기능": "features",
    "화면 또는 사용 흐름": "flows",
    "사용자 흐름": "flows",
    "확정된 결정": "decisions",
    "제외할 것": "exclusions",
    "아직 결정이 필요한 질문": "open_questions",
    "구현 전에 AI가 알아야 할 맥락": "context_notes",
}

_LIST_FIELDS = {"features", "flows", "decisions", "exclusions", "open_questions"}


def _strip_placeholder(value: str) -> str:
    return "" if "아직 결정이 필요" in value else value


def _strip_bullet(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("- ") or stripped.startswith("* "):
        return stripped[2:].strip()
    numbered = re.match(r"^\d+[\.)]\s+(?P<item>.+)$", stripped)
    if numbered:
        return numbered.group("item").strip()
    return stripped


def parse_plan_markdown(text: str) -> PlanningData:
    data = PlanningData()
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if current and current not in _LIST_FIELDS:
            joined = " ".join(b.strip() for b in buf if b.strip())
            value = _strip_placeholder(joined)
            if value:
                setattr(data, current, value)
        buf = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            current = None
            data.title = line[2:].strip()
            continue
        if line.startswith("## "):
            flush()
            current = _FIELD_BY_HEADING.get(line[3:].strip())
            continue
        if current is None:
            continue
        if current in _LIST_FIELDS:
            item = _strip_placeholder(_strip_bullet(line))
            if item:
                getattr(data, current).append(item)
        else:
            buf.append(line)

    flush()
    return data
