from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from vibelign.core.reporting_cli.models import Block, ReportModel, Section

_SCHEMA = 1


def polish_cache_key(model: ReportModel, *, provider: str) -> str:
    """모델 내용 + provider 의 안정 해시. 내용/ provider 가 바뀌면 키가 바뀐다."""
    h = sha256()
    h.update(provider.encode("utf-8"))
    h.update(b"\x1e")
    h.update(f"{model.title}\x1f{model.report_type}\x1f{model.date}".encode("utf-8"))
    for s in model.sections:
        h.update(b"\x1e")
        h.update(s.heading.encode("utf-8"))
        for b in s.blocks:
            h.update(b"\x1f")
            h.update(f"{b.kind}:{b.text}:{'|'.join(b.items)}".encode("utf-8"))
    return h.hexdigest()


def _cache_path(root: Path, slug: str) -> Path:
    return root / ".vibelign" / "reports" / f"{slug}-polish.json"


def save_polish_cache(root: Path, slug: str, *, key: str, model: ReportModel) -> Path:
    dest = _cache_path(root, slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": _SCHEMA, "key": key, "model": asdict(model)}
    dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return dest


def load_polish_cache(root: Path, slug: str, *, key: str) -> ReportModel | None:
    path = _cache_path(root, slug)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("schema_version") != _SCHEMA or data.get("key") != key:
        return None
    m = data["model"]
    sections = [
        Section(heading=s["heading"], blocks=[Block(**b) for b in s["blocks"]])
        for s in m["sections"]
    ]
    return ReportModel(
        title=m["title"], report_type=m["report_type"], date=m["date"],
        source_plan_path=m.get("source_plan_path", ""), sections=sections,
    )
