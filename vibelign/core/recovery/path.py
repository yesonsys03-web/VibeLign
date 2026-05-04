# === ANCHOR: RECOVERY_PATH_START ===
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .models import NormalizedPath


_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:")
_WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
_EXCLUDED_SEGMENTS = {
    ".git",
    ".hg",
    ".svn",
    ".vibelign",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    "__pycache__",
    "coverage",
    "out",
    "bin",
    "obj",
}


class PathSafetyError(ValueError):
    """Raised when a recovery path violates safety rules."""


# === ANCHOR: RECOVERY_PATH__NORMALIZE_RECOVERY_PATH_START ===
def normalize_recovery_path(
    project_root: Path,
    user_path: str,
    *,
    trusted_local_cli: bool = False,
) -> NormalizedPath:
    raw_path = unicodedata.normalize("NFC", user_path)
    if not raw_path.strip():
        raise PathSafetyError("recovery path is empty")
    if raw_path != raw_path.strip():
        raise PathSafetyError("leading or trailing whitespace is not valid in recovery targets")
    if raw_path.startswith("//") or raw_path.startswith("\\\\"):
        raise PathSafetyError("network paths are not valid recovery targets")

    raw_path = _normalize_wsl_root_identity(raw_path, project_root)
    normalized_text = raw_path.replace("\\", "/")
    if _has_windows_ads_stream(normalized_text):
        raise PathSafetyError("Windows ADS streams are not valid recovery targets")
    was_absolute = _is_absolute_like(raw_path, normalized_text)
    if was_absolute and not trusted_local_cli:
        raise PathSafetyError("absolute paths require trusted local CLI mode")

    root = project_root.resolve()
    candidate = Path(raw_path).expanduser() if was_absolute else root / normalized_text
    resolved = candidate.resolve(strict=False)

    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise PathSafetyError("recovery path must stay inside project root") from exc

    relative_text = unicodedata.normalize("NFC", relative.as_posix())
    parts = [part for part in relative_text.split("/") if part]
    _validate_relative_parts(parts)
    _validate_case_collisions(root, parts)

    return NormalizedPath(
        absolute_path=resolved,
        relative_path=relative_text,
        display_path=relative_text,
        was_absolute_input=was_absolute,
    )
# === ANCHOR: RECOVERY_PATH__NORMALIZE_RECOVERY_PATH_END ===


def _is_absolute_like(raw_path: str, normalized_text: str) -> bool:
    return raw_path.startswith("/") or normalized_text.startswith("/") or bool(_WINDOWS_DRIVE_RE.match(raw_path))


def _has_windows_ads_stream(normalized_text: str) -> bool:
    candidate = _WINDOWS_DRIVE_PREFIX_RE.sub("", normalized_text, count=1)
    return ":" in candidate


def _normalize_wsl_root_identity(raw_path: str, project_root: Path) -> str:
    normalized_text = raw_path.replace("\\", "/")
    drive_match = _WINDOWS_DRIVE_RE.match(normalized_text)
    if not drive_match:
        return raw_path
    root_text = project_root.as_posix()
    drive_letter = normalized_text[0].lower()
    wsl_prefix = f"/mnt/{drive_letter}/"
    if not root_text.lower().startswith(wsl_prefix):
        return raw_path
    return wsl_prefix + normalized_text[3:]


def _validate_relative_parts(parts: list[str]) -> None:
    if not parts:
        raise PathSafetyError("recovery path must name a project file")
    for part in parts:
        part = unicodedata.normalize("NFC", part)
        if part in (".", ".."):
            raise PathSafetyError("parent traversal is not a valid recovery target")
        if part.endswith(".") or part.endswith(" "):
            raise PathSafetyError("trailing dot or space is not valid in recovery targets")
        if part.lower() in _EXCLUDED_SEGMENTS:
            raise PathSafetyError("generated or internal directories are not valid recovery targets")
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
            raise PathSafetyError("Windows reserved names are not valid recovery targets")


def _validate_case_collisions(root: Path, parts: list[str]) -> None:
    current = root
    for part in parts:
        if current.exists() and current.is_dir():
            matches = [child.name for child in current.iterdir() if child.name.casefold() == part.casefold()]
            if matches and (part not in matches or len(set(matches)) > 1):
                raise PathSafetyError("case-insensitive path collisions are not valid recovery targets")
        current = current / part

# === ANCHOR: RECOVERY_PATH_END ===
