from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


_ALLOW_MARKER = "vibelign: allow-secret"
_PLACEHOLDER_VALUES = {
    "ENV",
    "YOUR_API_KEY",
    "YOUR_KEY",
    "YOUR_TOKEN",
    "YOUR_SECRET",
    "EXAMPLE",
    "CHANGE_ME",
    "CHANGEME",
    "CHANGE-ME",
    "REPLACE_ME",
    "REPLACE_WITH_REAL_VALUE",
}
_KEYWORD_VALUE_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|passwd|client_secret|access_key)\s*[:=]\s*[\"']?([A-Za-z0-9_./+=:@\-]{16,})[\"']?"
)
_HIGH_CONFIDENCE_RULES = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "github-token",
        re.compile(r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    ("slack-token", re.compile(r"\bxox(?:a|b|p|r|s)-[A-Za-z0-9-]{10,}\b")),
    ("stripe-live-key", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
]
_BINARY_SECRET_PATHS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".aws/credentials",
    "id_rsa",
}
_BINARY_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


@dataclass(frozen=True)
class SecretFinding:
    path: str
    rule_id: str
    line_number: int | None
    snippet: str


@dataclass(frozen=True)
class SecretScanResult:
    findings: list[SecretFinding]

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)


def _run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _looks_like_secret_file(path: str) -> bool:
    name = path.replace("\\", "/")
    basename = Path(name).name
    return (
        name in _BINARY_SECRET_PATHS
        or basename in _BINARY_SECRET_PATHS
        or name.endswith(_BINARY_SECRET_SUFFIXES)
        or basename.endswith(_BINARY_SECRET_SUFFIXES)
    )


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").upper()
    return normalized in _PLACEHOLDER_VALUES or normalized.startswith("YOUR_")


def _redact(text: str) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= 4:
        return "[redacted]"
    return f"...{compact[-4:]}"


def _extract_added_line(line: str) -> str | None:
    if not line.startswith("+") or line.startswith("+++"):
        return None
    return line[1:]


def scan_unified_diff_for_secrets(
    diff_text: str, path_hint: str
) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    current_line_number: int | None = None

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            current_line_number = int(match.group(1)) if match else None
            continue

        added_line = _extract_added_line(raw_line)
        if added_line is None:
            if raw_line.startswith("-") or raw_line.startswith("diff --git"):
                continue
            if current_line_number is not None and not raw_line.startswith("\\"):
                current_line_number += 1
            continue

        line_number = current_line_number
        if current_line_number is not None:
            current_line_number += 1

        if _ALLOW_MARKER in added_line:
            continue

        matched_high_confidence = False
        for rule_id, pattern in _HIGH_CONFIDENCE_RULES:
            matched = pattern.search(added_line)
            if matched:
                matched_high_confidence = True
                findings.append(
                    SecretFinding(
                        path=path_hint,
                        rule_id=rule_id,
                        line_number=line_number,
                        snippet=_redact(matched.group(0)),
                    )
                )

        keyword_match = _KEYWORD_VALUE_RE.search(added_line)
        if not keyword_match or matched_high_confidence:
            continue

        value = keyword_match.group(2)
        if _is_placeholder(value):
            continue
        findings.append(
            SecretFinding(
                path=path_hint,
                rule_id="generic-secret",
                line_number=line_number,
                snippet=_redact(value),
            )
        )

    return findings


def scan_staged_secrets(root: Path) -> SecretScanResult:
    findings: list[SecretFinding] = []
    names_output = _run_git(root, ["diff", "--cached", "--name-only", "-z"])
    staged_paths = [item for item in names_output.split("\0") if item]

    for path in staged_paths:
        if _looks_like_secret_file(path):
            findings.append(
                SecretFinding(
                    path=path,
                    rule_id="secret-file",
                    line_number=None,
                    snippet="secret-like file path",
                )
            )
            continue
        diff_text = _run_git(root, ["diff", "--cached", "--unified=0", "--", path])
        if diff_text.startswith("Binary files") or "GIT binary patch" in diff_text:
            continue
        findings.extend(scan_unified_diff_for_secrets(diff_text, path))

    return SecretScanResult(findings=findings)
