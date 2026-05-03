# === ANCHOR: MEMORY_REDACTION_START ===
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from vibelign.core.memory.models import MemoryState, MemoryVerification
from vibelign.core.secret_scan import scan_unified_diff_for_secrets


@dataclass(frozen=True)
class MemoryRedaction:
    secret_hits: int = 0
    privacy_hits: int = 0
    summarized_fields: int = 0


@dataclass(frozen=True)
class RedactedText:
    text: str
    redaction: MemoryRedaction


@dataclass(frozen=True)
class RedactedMemorySummary:
    active_intent: str = ""
    next_action: str = ""
    decisions: list[str] = field(default_factory=list)
    relevant_files: list[str] = field(default_factory=list)
    observed_context: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    redaction: MemoryRedaction = field(default_factory=MemoryRedaction)


_LOCAL_PATH_RE = re.compile(r"(?:(?:/Users|/home)/[^\s`'\"]+|[A-Za-z]:\\Users\\[^\s`'\"]+)")
_PRIVATE_IP_RE = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b"
)
_INTERNAL_HOST_RE = re.compile(r"\b[A-Za-z0-9.-]+\.(?:local|internal|corp|lan)\b")
_KEYWORD_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|passwd|client_secret|access_key)\s*[:=]\s*[\"']?([A-Za-z0-9_./+=:@\-]{8,})[\"']?"
)
_LONG_LINE_LIMIT = 240


def redact_memory_text(value: str) -> RedactedText:
    text = " ".join(value.split())
    secret_hits = len(scan_unified_diff_for_secrets("+" + text, "memory"))
    text, keyword_hits = _KEYWORD_VALUE_RE.subn(_replace_secret_value, text)
    text, path_hits = _LOCAL_PATH_RE.subn("[local-path]", text)
    text, ip_hits = _PRIVATE_IP_RE.subn("[private-ip]", text)
    text, host_hits = _INTERNAL_HOST_RE.subn("[internal-host]", text)
    summarized_fields = 0
    if len(text) > _LONG_LINE_LIMIT:
        text = text[: _LONG_LINE_LIMIT - 1].rstrip() + "…"
        summarized_fields = 1
    return RedactedText(
        text=text,
        redaction=MemoryRedaction(
            secret_hits=secret_hits + keyword_hits,
            privacy_hits=path_hits + ip_hits + host_hits,
            summarized_fields=summarized_fields,
        ),
    )


def redact_memory_path(value: str) -> RedactedText:
    text = value.replace("\\", "/")
    if _LOCAL_PATH_RE.search(value) or text.startswith("/") or _looks_like_windows_absolute(value):
        return RedactedText(
            text=f"[local-path]/{Path(text).name}" if Path(text).name else "[local-path]",
            redaction=MemoryRedaction(privacy_hits=1),
        )
    return RedactedText(text=text, redaction=MemoryRedaction())


def combine_redactions(*items: MemoryRedaction) -> MemoryRedaction:
    return MemoryRedaction(
        secret_hits=sum(item.secret_hits for item in items),
        privacy_hits=sum(item.privacy_hits for item in items),
        summarized_fields=sum(item.summarized_fields for item in items),
    )


def build_redacted_memory_summary(state: MemoryState) -> RedactedMemorySummary:
    redactions: list[MemoryRedaction] = []
    active_intent = _redact_text(
        state.active_intent.text if state.active_intent is not None else "", redactions
    )
    next_action = _redact_text(
        state.next_action.text if state.next_action is not None else "", redactions
    )
    decisions = [_redact_text(item.text, redactions) for item in state.decisions[-5:] if item.text]
    relevant_files = [
        f"{_redact_path(item.path, redactions)} — {_redact_text(item.why, redactions)}"
        for item in state.relevant_files[-5:]
        if item.source == "explicit" and item.path
    ]
    observed_context = [
        f"{_redact_text(item.kind, redactions)}: {_redact_path(item.path, redactions) if item.path else '(unknown)'} — {_redact_text(item.summary or '(no details)', redactions)}"
        for item in state.observed_context[-5:]
    ]
    verification = [_redact_text(_verification_line(item), redactions) for item in state.verification[-5:]]
    warnings = [_redact_text(item.text, redactions) for item in state.risks[-5:] if item.text]
    return RedactedMemorySummary(
        active_intent=active_intent,
        next_action=next_action,
        decisions=decisions,
        relevant_files=relevant_files,
        observed_context=observed_context,
        verification=verification,
        warnings=warnings,
        redaction=combine_redactions(*redactions),
    )


def _verification_line(item: MemoryVerification) -> str:
    line = item.command
    if item.result:
        line = f"{line} -> {item.result}"
    if item.stale and "(stale" not in line:
        reason = "scope unknown" if item.scope_unknown else "stale"
        line = f"{line} (stale: {reason})"
    return line


def _redact_text(value: str, redactions: list[MemoryRedaction]) -> str:
    redacted = redact_memory_text(value)
    redactions.append(redacted.redaction)
    return redacted.text


def _redact_path(value: str, redactions: list[MemoryRedaction]) -> str:
    redacted = redact_memory_path(value)
    redactions.append(redacted.redaction)
    return redacted.text


def _replace_secret_value(match: re.Match[str]) -> str:
    return f"{match.group(1)}=[redacted]"


def _looks_like_windows_absolute(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return len(normalized) >= 3 and normalized[1:3] == ":/" and normalized[0].isalpha()
# === ANCHOR: MEMORY_REDACTION_END ===
