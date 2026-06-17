# === ANCHOR: POLISH_CACHE_START ===
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from vibelign.core.reporting_cli.model_json import model_from_dict, model_to_dict
from vibelign.core.reporting_cli.models import ReportModel

_SCHEMA = 1


# === ANCHOR: POLISH_CACHE_POLISH_CACHE_KEY_START ===
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
# === ANCHOR: POLISH_CACHE_POLISH_CACHE_KEY_END ===


# === ANCHOR: POLISH_CACHE__CACHE_PATH_START ===
def _cache_path(root: Path, slug: str) -> Path:
    return root / ".vibelign" / "reports" / f"{slug}-polish.json"
# === ANCHOR: POLISH_CACHE__CACHE_PATH_END ===


# === ANCHOR: POLISH_CACHE_SAVE_POLISH_CACHE_START ===
def save_polish_cache(root: Path, slug: str, *, key: str, model: ReportModel) -> Path:
    dest = _cache_path(root, slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": _SCHEMA, "key": key, "model": model_to_dict(model)}
    dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return dest
# === ANCHOR: POLISH_CACHE_SAVE_POLISH_CACHE_END ===


# === ANCHOR: POLISH_CACHE_LOAD_POLISH_CACHE_START ===
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
    try:
        return model_from_dict(data["model"])
    except (KeyError, ValueError):
        return None
# === ANCHOR: POLISH_CACHE_LOAD_POLISH_CACHE_END ===
# === ANCHOR: POLISH_CACHE_END ===
