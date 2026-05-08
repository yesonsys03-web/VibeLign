# === ANCHOR: CONFIG_LOADER_START ===
from __future__ import annotations

from pathlib import Path

from vibelign.core.meta_paths import MetaPaths


def is_local_error_log_enabled(root: Path) -> bool:
    config_path = MetaPaths(root).config_path
    try:
        lines = config_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return True
    try:
        value = _nested_scalar(lines, "error_reporting", "local_log")
    except ValueError:
        return True
    if value is None:
        return True
    normalized = value.strip().strip('"\'').lower()
    if normalized in {"false", "no", "0", "off"}:
        return False
    if normalized in {"true", "yes", "1", "on"}:
        return True
    return True


def _nested_scalar(lines: list[str], section: str, key: str) -> str | None:
    in_section = False
    section_indent = 0
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if not in_section:
            if stripped == f"{section}:":
                in_section = True
                section_indent = indent
            continue
        if indent <= section_indent:
            return None
        if stripped.startswith(f"{key}:"):
            return stripped.split(":", 1)[1].strip()
    return None
# === ANCHOR: CONFIG_LOADER_END ===
