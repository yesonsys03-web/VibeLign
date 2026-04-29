# === ANCHOR: SECRET_SCAN_START ===
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

def _find_git() -> str:
    found = shutil.which("git")
    if found:
        return found
    if sys.platform == "win32":
        # cmd\git.exe 는 CMD 래퍼라서 PyInstaller 환경에서 exit 129 발생 가능.
        # mingw64\bin\git.exe (실제 바이너리)를 먼저 시도.
        candidates = [
            r"C:\Program Files\Git\mingw64\bin\git.exe",
            r"C:\Program Files\Git\usr\bin\git.exe",
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\mingw64\bin\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\mingw64\bin\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ]
        for p in candidates:
            if Path(p).exists():
                return p
    raise FileNotFoundError("git 실행 파일을 찾을 수 없어요. Git을 설치하고 PATH에 추가해주세요.")


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
    ("gemini-api-key", re.compile(r"\bAIzaSy[A-Za-z0-9_-]{33}\b")),
    ("anthropic-api-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{40,}\b")),
    ("openai-api-key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("url-inline-key", re.compile(r"[?&]key=[A-Za-z0-9_-]{16,}")),
    (
        "jwt-token",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
        ),
    ),
    (
        "db-url-with-password",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|amqps)://"
            r"[^:/\s\"']+:[^@\s\"']+@[^\s\"']+"
        ),
    ),
    (
        "gcp-service-account",
        re.compile(r'"type"\s*:\s*"service_account"'),
    ),
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


# === ANCHOR: SECRET_SCAN_SECRETFINDING_START ===
@dataclass(frozen=True)
class SecretFinding:
    path: str
    rule_id: str
    line_number: int | None
    snippet: str
# === ANCHOR: SECRET_SCAN_SECRETFINDING_END ===


# === ANCHOR: SECRET_SCAN_SECRETSCANRESULT_START ===
@dataclass(frozen=True)
class SecretScanResult:
    findings: list[SecretFinding]

    # === ANCHOR: SECRET_SCAN_HAS_FINDINGS_START ===
    @property
    def has_findings(self) -> bool:
        return bool(self.findings)
    # === ANCHOR: SECRET_SCAN_HAS_FINDINGS_END ===
# === ANCHOR: SECRET_SCAN_SECRETSCANRESULT_END ===


# === ANCHOR: SECRET_SCAN__RUN_GIT_START ===
def _run_git(root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            [_find_git(), *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        return completed.stdout
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        combined = (stderr + " " + (e.stdout or "")).lower()
        if "not a git repository" in combined or ("unknown option" in combined and "cached" in combined):
            raise RuntimeError("git 저장소가 아닌 폴더예요. 먼저 git init 을 실행해 주세요.") from None
        raise RuntimeError(
            f"git 명령 실패 (exit {e.returncode})"
            + (f": {stderr}" if stderr else "")
        ) from None
# === ANCHOR: SECRET_SCAN__RUN_GIT_END ===


# === ANCHOR: SECRET_SCAN__LOOKS_LIKE_SECRET_FILE_START ===
def _looks_like_secret_file(path: str) -> bool:
    name = path.replace("\\", "/")
    basename = Path(name).name
    return (
        name in _BINARY_SECRET_PATHS
        or basename in _BINARY_SECRET_PATHS
        or name.endswith(_BINARY_SECRET_SUFFIXES)
        or basename.endswith(_BINARY_SECRET_SUFFIXES)
    )
# === ANCHOR: SECRET_SCAN__LOOKS_LIKE_SECRET_FILE_END ===


# === ANCHOR: SECRET_SCAN__IS_PLACEHOLDER_START ===
def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("\"'").upper()
    return normalized in _PLACEHOLDER_VALUES or normalized.startswith("YOUR_")
# === ANCHOR: SECRET_SCAN__IS_PLACEHOLDER_END ===


# === ANCHOR: SECRET_SCAN__REDACT_START ===
def _redact(text: str) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= 4:
        return "[redacted]"
    return f"...{compact[-4:]}"
# === ANCHOR: SECRET_SCAN__REDACT_END ===


# === ANCHOR: SECRET_SCAN__EXTRACT_ADDED_LINE_START ===
def _extract_added_line(line: str) -> str | None:
    if not line.startswith("+") or line.startswith("+++"):
        return None
    return line[1:]
# === ANCHOR: SECRET_SCAN__EXTRACT_ADDED_LINE_END ===


# === ANCHOR: SECRET_SCAN_SCAN_UNIFIED_DIFF_FOR_SECRETS_START ===
def scan_unified_diff_for_secrets(
    diff_text: str, path_hint: str
# === ANCHOR: SECRET_SCAN_SCAN_UNIFIED_DIFF_FOR_SECRETS_END ===
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


# === ANCHOR: SECRET_SCAN_SCAN_STAGED_SECRETS_START ===
def scan_staged_secrets(root: Path) -> SecretScanResult:
    if not (root / ".git").is_dir():
        return SecretScanResult(findings=[])
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
# === ANCHOR: SECRET_SCAN_SCAN_STAGED_SECRETS_END ===


_COMMIT_MARKER_PREFIX = "COMMIT_MARKER_"
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*?) b/")

_HISTORY_AUDIT_SKIP_PATHS: tuple[str, ...] = (
    "tests/test_secret_scan.py",
)


def _is_history_audit_skipped(path: str) -> bool:
    return path in _HISTORY_AUDIT_SKIP_PATHS


# === ANCHOR: SECRET_SCAN_PARSE_GIT_LOG_CHUNKS_START ===
def parse_git_log_chunks(
    lines: Iterable[str],
) -> Iterator[tuple[str, str, str]]:
    current_commit = ""
    current_file = ""
    buffer: list[str] = []

    def _flush() -> tuple[str, str, str] | None:
        nonlocal buffer, current_file
        if buffer and current_file:
            out = (current_commit, current_file, "\n".join(buffer))
            buffer = []
            current_file = ""
            return out
        buffer = []
        current_file = ""
        return None

    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith(_COMMIT_MARKER_PREFIX):
            flushed = _flush()
            if flushed is not None:
                yield flushed
            current_commit = line[len(_COMMIT_MARKER_PREFIX):]
            continue
        m = _DIFF_GIT_RE.match(line)
        if m is not None:
            flushed = _flush()
            if flushed is not None:
                yield flushed
            current_file = m.group(1)
            buffer.append(line)
            continue
        if current_file:
            buffer.append(line)

    tail = _flush()
    if tail is not None:
        yield tail
# === ANCHOR: SECRET_SCAN_PARSE_GIT_LOG_CHUNKS_END ===


# === ANCHOR: SECRET_SCAN_SCAN_ALL_HISTORY_START ===
def scan_all_history(
    root: Path,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> SecretScanResult:
    if not (root / ".git").is_dir():
        return SecretScanResult(findings=[])

    total: int | None = None
    try:
        total_out = _run_git(root, ["rev-list", "--count", "--all"])
        total = int(total_out.strip())
    except (RuntimeError, ValueError):
        total = None

    findings: list[SecretFinding] = []

    try:
        git_bin = _find_git()
    except FileNotFoundError:
        return SecretScanResult(findings=[])

    proc = subprocess.Popen(
        [
            git_bin,
            "log",
            "--all",
            "-p",
            "--no-color",
            f"--format={_COMMIT_MARKER_PREFIX}%H",
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
        creationflags=WINDOWS_SUBPROCESS_FLAGS,
    )
    assert proc.stdout is not None

    try:
        last_reported = None
        processed = 0
        for commit_sha, file_path, diff_text in parse_git_log_chunks(proc.stdout):
            display_path = (
                f"{commit_sha[:8]}:{file_path}" if commit_sha else file_path
            )
            if _is_history_audit_skipped(file_path):
                if commit_sha != last_reported:
                    last_reported = commit_sha
                    processed += 1
                    if on_progress is not None:
                        on_progress(processed, total)
                continue
            if _looks_like_secret_file(file_path):
                findings.append(
                    SecretFinding(
                        path=display_path,
                        rule_id="secret-file",
                        line_number=None,
                        snippet="secret-like file path",
                    )
                )
            elif not (
                diff_text.startswith("Binary files") or "GIT binary patch" in diff_text
            ):
                findings.extend(
                    scan_unified_diff_for_secrets(diff_text, display_path)
                )

            if commit_sha != last_reported:
                last_reported = commit_sha
                processed += 1
                if on_progress is not None:
                    on_progress(processed, total)
    finally:
        try:
            proc.stdout.close()
        except OSError:
            pass
        try:
            _ = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            _ = proc.wait()

    return SecretScanResult(findings=findings)
# === ANCHOR: SECRET_SCAN_SCAN_ALL_HISTORY_END ===
# === ANCHOR: SECRET_SCAN_END ===
