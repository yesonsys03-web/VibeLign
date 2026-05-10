# === ANCHOR: DOCS_ACCESS_PY_START ===
from __future__ import annotations

from pathlib import PurePosixPath


CANVAS_ALLOWED_HIDDEN_PREFIXES: frozenset[str] = frozenset(
    {".omc/plans"}
)
CANVAS_EXCLUDED_PREFIXES: frozenset[str] = frozenset({"promo"})
CANVAS_EXCLUDED_FILES: frozenset[str] = frozenset(
    {".mcp.json", ".omc/project-memory.json", ".omc/last-tool-error.json", ".omc/subagent-tracking.json"}
)


def normalize_docs_relative_path(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/").strip().strip("/")
    return PurePosixPath(normalized).as_posix() if normalized else ""


def is_canvas_eligible_path(rel_path: str) -> bool:
    """Return whether a docs path may have generated Canvas artifacts.

    Canvas artifacts are heavier, derived views. Runtime state, MCP config, and
    promo production assets are excluded even if they are readable as source docs.
    Human-authored plan carve-outs remain eligible.
    """

    normalized = normalize_docs_relative_path(rel_path)
    if not normalized or ".." in normalized.split("/"):
        return False
    if normalized in CANVAS_EXCLUDED_FILES:
        return False
    if any(normalized == prefix or normalized.startswith(f"{prefix}/") for prefix in CANVAS_EXCLUDED_PREFIXES):
        return False
    if normalized.startswith(".omc/"):
        return any(
            normalized == prefix or normalized.startswith(f"{prefix}/")
            for prefix in CANVAS_ALLOWED_HIDDEN_PREFIXES
        )
    return True


def canvas_ineligible_reason(rel_path: str) -> str:
    normalized = normalize_docs_relative_path(rel_path) or rel_path
    return f"Canvas visualization is unsupported for excluded docs path: {normalized}"
# === ANCHOR: DOCS_ACCESS_PY_END ===
