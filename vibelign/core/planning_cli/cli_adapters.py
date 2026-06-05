# === ANCHOR: CLI_ADAPTERS_START ===
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

PlanningCliStatus = Literal[
    "ok",
    "not_installed",
    "not_logged_in",
    "timeout",
    "rate_limited",
    "tty_required",
    "bad_output",
    "terms_blocked",
    "process_error",
]


@dataclass(frozen=True)
# === ANCHOR: CLI_ADAPTERS_PLANNINGCLIRESULT_START ===
class PlanningCliResult:
    status: PlanningCliStatus
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
# === ANCHOR: CLI_ADAPTERS_PLANNINGCLIRESULT_END ===


@dataclass(frozen=True)
# === ANCHOR: CLI_ADAPTERS_PLANNINGCLICANDIDATE_START ===
class PlanningCliCandidate:
    adapter: str
    executable: str | None
    available: bool
    probe_status: str
# === ANCHOR: CLI_ADAPTERS_PLANNINGCLICANDIDATE_END ===


# === ANCHOR: CLI_ADAPTERS_PLANNINGCLIRUNNER_START ===
class PlanningCliRunner(Protocol):
    # === ANCHOR: CLI_ADAPTERS_RUN_START ===
    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
# === ANCHOR: CLI_ADAPTERS_PLANNINGCLIRUNNER_END ===
    # === ANCHOR: CLI_ADAPTERS_RUN_END ===
    ) -> PlanningCliResult: ...


# === ANCHOR: CLI_ADAPTERS_SUBPROCESSPLANNINGCLIRUNNER_START ===
class SubprocessPlanningCliRunner:
    # === ANCHOR: CLI_ADAPTERS_RUN_START ===
    def run(
        self,
        command: list[str],
        *,
        cwd: Path,
        input_text: str,
        timeout_seconds: int,
    # === ANCHOR: CLI_ADAPTERS_RUN_END ===
    ) -> PlanningCliResult:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input=input_text,
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
                check=False,
                creationflags=WINDOWS_SUBPROCESS_FLAGS,
            )
        except subprocess.TimeoutExpired as exc:
            return PlanningCliResult(
                status="timeout",
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                exit_code=None,
                duration_ms=_duration_ms(started),
            )
        except OSError as exc:
            return PlanningCliResult(
                status="process_error",
                stdout="",
                stderr=str(exc),
                exit_code=None,
                duration_ms=_duration_ms(started),
            )

        status = classify_cli_output(
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
        return PlanningCliResult(
            status=status,
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
# === ANCHOR: CLI_ADAPTERS_SUBPROCESSPLANNINGCLIRUNNER_END ===
            duration_ms=_duration_ms(started),
        )


# === ANCHOR: CLI_ADAPTERS__DURATION_MS_START ===
def _duration_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
# === ANCHOR: CLI_ADAPTERS__DURATION_MS_END ===


# === ANCHOR: CLI_ADAPTERS_CLASSIFY_CLI_OUTPUT_START ===
def classify_cli_output(exit_code: int, stdout: str, stderr: str) -> PlanningCliStatus:
    if exit_code == 0 and stdout.strip():
        return "ok"

    combined = f"{stdout}\n{stderr}".lower()
    login_patterns = (
        "not logged in",
        "not signed in",
        "please login",
        "please log in",
        "login required",
        "authentication required",
        "auth required",
    )
    if any(pattern in combined for pattern in login_patterns):
        return "not_logged_in"
    if "rate limit" in combined or "rate_limited" in combined:
        return "rate_limited"
    if "tty" in combined or "interactive" in combined:
        return "tty_required"
    if "terms" in combined:
        return "terms_blocked"
    if exit_code != 0:
        return "process_error"
    if not stdout.strip():
        return "bad_output"
    return "ok"
# === ANCHOR: CLI_ADAPTERS_CLASSIFY_CLI_OUTPUT_END ===


# === ANCHOR: CLI_ADAPTERS_RESOLVE_CLI_EXECUTABLE_START ===
def resolve_cli_executable(adapter: str) -> str | None:
    executable_name = {"codex": "codex", "claude": "claude", "agy": "agy"}.get(adapter)
    if executable_name is None:
        return None
    return shutil.which(executable_name)
# === ANCHOR: CLI_ADAPTERS_RESOLVE_CLI_EXECUTABLE_END ===


# === ANCHOR: CLI_ADAPTERS_PROBE_CLI_CANDIDATES_START ===
def probe_cli_candidates() -> list[PlanningCliCandidate]:
    candidates: list[PlanningCliCandidate] = []
    for adapter in ("codex", "claude", "agy"):
        executable = resolve_cli_executable(adapter)
        candidates.append(
            PlanningCliCandidate(
                adapter=adapter,
                executable=executable,
                available=executable is not None,
                probe_status="installed" if executable else "not_installed",
            )
        )
    return candidates
# === ANCHOR: CLI_ADAPTERS_PROBE_CLI_CANDIDATES_END ===


# === ANCHOR: CLI_ADAPTERS_SELECT_ADAPTER_START ===
def select_adapter(cli_choice: str) -> str:
    match cli_choice:
        case "" | "auto":
            return "codex"
        case "codex" | "claude" | "agy":
            return cli_choice
        case _:
            raise ValueError(f"unsupported planning cli: {cli_choice}")
# === ANCHOR: CLI_ADAPTERS_SELECT_ADAPTER_END ===


# === ANCHOR: CLI_ADAPTERS_BUILD_CODEX_COMMAND_START ===
def build_codex_command(prompt: str) -> list[str] | None:
    return build_cli_command("codex", prompt)
# === ANCHOR: CLI_ADAPTERS_BUILD_CODEX_COMMAND_END ===


# === ANCHOR: CLI_ADAPTERS_BUILD_CLI_COMMAND_START ===
def build_cli_command(adapter: str, prompt: str) -> list[str] | None:
    executable = resolve_cli_executable(adapter)
    if executable is None:
        return None
    match adapter:
        case "codex":
            return [executable, "exec", prompt]
        case "claude":
            return [executable, "-p", prompt]
        case "agy":
            return [executable, "-p", prompt]
        case _:
            raise ValueError(f"unsupported planning cli: {adapter}")
# === ANCHOR: CLI_ADAPTERS_BUILD_CLI_COMMAND_END ===
# === ANCHOR: CLI_ADAPTERS_END ===
