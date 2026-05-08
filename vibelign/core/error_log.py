# === ANCHOR: ERROR_LOG_START ===
from __future__ import annotations

import importlib.metadata
import json
import platform
import re
import sys
import threading
import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import cast

from vibelign.core.config_loader import is_local_error_log_enabled
from vibelign.core.file_lock import file_lock
from vibelign.core.memory.redaction import MemoryRedaction, combine_redactions, redact_memory_text

LOG_LINE_LIMIT = 8 * 1024
MAX_LINES_PER_FILE = 1000
RETENTION_DAYS = 30
TRUNCATION_MARKER = "…[truncated]"
MAX_TRUNCATION_PASSES = 12

_reporting_in_progress = threading.local()

_TOKEN_PREFIX_RE = re.compile(
    r"(?:sk-ant-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]+|gho_[A-Za-z0-9_]+|xox[bp]-[A-Za-z0-9-]+|AKIA[A-Z0-9]{12,}|AIza[0-9A-Za-z_-]+|ya29\.[0-9A-Za-z_-]+)"
)
_WINDOWS_PATH_RE = re.compile(r"(?:[A-Za-z]:\\[^\s`'\"]+|file:///[A-Za-z]:/[^\s`'\"]+|/Applications/[^\s`'\"]+)")


def record_cli_error(
    root: Path, exc_info: tuple[type[BaseException], BaseException, TracebackType | None], argv: list[str]
) -> None:
    _record_error(root, "cli", lambda: _build_cli_record(exc_info, argv))


def record_gui_error(root: Path, payload: dict[str, object]) -> None:
    _record_error(root, "gui", lambda: _build_gui_record(payload))


def _record_error(root: Path, kind: str, build_record: Callable[[], dict[str, object]]) -> None:
    if getattr(_reporting_in_progress, "active", False):
        return
    _reporting_in_progress.active = True
    try:
        if not is_local_error_log_enabled(root):
            return
        logs_dir = root / ".vibelign" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _sweep_old_logs(logs_dir)
        record = build_record()
        path = _select_log_path(logs_dir, kind)
        _append_jsonl(path, record)
    except Exception as exc:
        _ = exc
    finally:
        _reporting_in_progress.active = False


def _build_cli_record(
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None], argv: list[str]
) -> dict[str, object]:
    exc_type, exc_value, tb = exc_info
    redactions: list[MemoryRedaction] = []
    traceback_lines = traceback.format_exception(exc_type, exc_value, tb)
    record: dict[str, object] = {
        "ts": _utc_now(),
        "vib_version": resolve_vib_version(),
        "python_version": platform.python_version(),
        "platform": f"{sys.platform}-{platform.machine()}",
        "command": _redact(" ".join(argv), redactions),
        "error_class": exc_type.__name__,
        "error_message": _redact(str(exc_value), redactions),
        "traceback_redacted": [_redact(line.rstrip("\n"), redactions) for line in traceback_lines],
    }
    record["redaction"] = _redaction_dict(combine_redactions(*redactions))
    return record


def _build_gui_record(payload: dict[str, object]) -> dict[str, object]:
    redactions: list[MemoryRedaction] = []
    message = _payload_str(payload, "message")
    stack = _payload_str(payload, "stack")
    component_stack = _payload_str(payload, "componentStack")
    if component_stack:
        stack = f"{stack}\n{component_stack}" if stack else component_stack
    record: dict[str, object] = {
        "ts": _utc_now(),
        "app_version": resolve_vib_version(),
        "tauri_version": _payload_str(payload, "tauri_version") or "unknown",
        "platform": sys.platform,
        "source": _redact(_payload_str(payload, "source") or "unknown", redactions),
        "message_redacted": _redact(message, redactions),
        "stack_redacted": _redact(stack, redactions),
        "url": _redact(_payload_str(payload, "url"), redactions),
    }
    record["redaction"] = _redaction_dict(combine_redactions(*redactions))
    return record


def resolve_vib_version() -> str:
    try:
        return importlib.metadata.version("vibelign")
    except importlib.metadata.PackageNotFoundError:
        try:
            import vibelign

            version = getattr(vibelign, "__version__", None)
            return version if isinstance(version, str) and version else "unknown"
        except Exception as exc:
            _ = exc
            return "unknown"


def _redact(value: str, redactions: list[MemoryRedaction]) -> str:
    redacted = redact_memory_text(value)
    text = redacted.text
    text, token_hits = _TOKEN_PREFIX_RE.subn("[secret-token]", text)
    text, path_hits = _WINDOWS_PATH_RE.subn("[local-path]", text)
    redactions.append(
        combine_redactions(
            redacted.redaction,
            MemoryRedaction(secret_hits=token_hits, privacy_hits=path_hits),
        )
    )
    return text


def _append_jsonl(path: Path, record: dict[str, object]) -> None:
    with file_lock(path) as locked:
        if not locked:
            return
        line = _json_line(record)
        with open(path, "a", encoding="utf-8", newline="") as handle:
            _ = handle.write(line)


def _json_line(record: dict[str, object]) -> str:
    current = record
    previous_size = 0
    for _ in range(MAX_TRUNCATION_PASSES):
        text = json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n"
        size = len(text.encode("utf-8"))
        if size <= LOG_LINE_LIMIT:
            _ = cast(object, json.loads(text))
            return text
        if previous_size and size >= previous_size:
            current = _fallback_truncated_record(current)
            break
        previous_size = size
        current = cast(dict[str, object], _truncate_record_strings(current))
    text = json.dumps(_fallback_truncated_record(current), ensure_ascii=False, separators=(",", ":")) + "\n"
    _ = cast(object, json.loads(text))
    return text


def _fallback_truncated_record(record: dict[str, object]) -> dict[str, object]:
    keep_keys = [
        "ts",
        "vib_version",
        "app_version",
        "python_version",
        "platform",
        "source",
        "error_class",
        "redaction",
    ]
    fallback: dict[str, object] = {}
    for key in keep_keys:
        value = record.get(key)
        if isinstance(value, str):
            fallback[key] = value[:120]
        elif isinstance(value, (int, float, bool, dict)) or value is None:
            fallback[key] = value
    fallback["truncated"] = True
    fallback["message_redacted"] = TRUNCATION_MARKER
    return fallback


def _truncate_record_strings(value: object) -> object:
    if isinstance(value, str):
        limit = max(1, len(value) // 2)
        return value[: max(1, limit - len(TRUNCATION_MARKER))].rstrip() + TRUNCATION_MARKER
    if isinstance(value, list):
        values = cast(list[object], value)
        return [_truncate_record_strings(item) for item in values]
    if isinstance(value, dict):
        values = cast(dict[object, object], value)
        return {str(key): _truncate_record_strings(item) for key, item in values.items()}
    return value


def _select_log_path(logs_dir: Path, kind: str) -> Path:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    index = 1
    while True:
        suffix = "" if index == 1 else f"-{index}"
        path = logs_dir / f"{kind}-error-{date}{suffix}.jsonl"
        if _line_count(path) < MAX_LINES_PER_FILE:
            return path
        index += 1


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return MAX_LINES_PER_FILE


def _sweep_old_logs(logs_dir: Path) -> None:
    now_date = datetime.now(timezone.utc).date()
    for path in list(logs_dir.glob("*-error-*.jsonl")):
        match = re.match(r"(?:cli|gui)-error-(\d{8})(?:-\d+)?\.jsonl$", path.name)
        if not match:
            continue
        try:
            file_date = datetime.strptime(match.group(1), "%Y%m%d").date()
            if (now_date - file_date).days > RETENTION_DAYS:
                path.unlink()
        except (OSError, ValueError) as exc:
            _ = exc


def _payload_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _redaction_dict(redaction: MemoryRedaction) -> dict[str, int]:
    return {
        "secret_hits": redaction.secret_hits,
        "privacy_hits": redaction.privacy_hits,
        "summarized_fields": redaction.summarized_fields,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
# === ANCHOR: ERROR_LOG_END ===
