# === ANCHOR: VIB_MEMORY_CMD_START ===
from __future__ import annotations

from argparse import Namespace
from importlib import import_module
from pathlib import Path
from typing import Callable, Protocol, cast

from vibelign.core.memory.store import (
    add_memory_decision,
    add_memory_relevant_file,
    is_memory_read_only,
    load_memory_state,
    set_memory_active_intent,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import cli_print

print = cli_print


class _MemoryReviewLike(Protocol):
    has_memory: bool
    active_intent: str
    next_action: str
    decisions: list[str]
    relevant_files: list[str]
    observed_context: list[str]
    verification: list[str]
    warnings: list[str]
    redaction: object
    suggestions: list[str]


_ReviewMemory = Callable[[Path], _MemoryReviewLike]


def _memory_path() -> Path:
    root = resolve_project_root(Path.cwd())
    return MetaPaths(root).work_memory_path


def _print_lines(title: str, lines: list[str]) -> None:
    print(title)
    if not lines:
        print("- (none)")
        return
    for line in lines:
        print(f"- {line}")


def run_vib_memory_show(_: Namespace) -> None:
    path = _memory_path()
    state = load_memory_state(path)
    print("VibeLign Memory")
    if state.downgrade_warning:
        print(f"Warning: {state.downgrade_warning}")
    active = state.active_intent.text if state.active_intent is not None else "(none)"
    next_action = state.next_action.text if state.next_action is not None else "(none)"
    print(f"Active intent: {active}")
    print(f"Next action: {next_action}")
    _print_lines("Decisions:", [item.text for item in state.decisions[-5:]])
    _print_lines(
        "Relevant files:",
        [f"{item.path} — {item.why} ({item.source})" for item in state.relevant_files[-5:]],
    )
    _print_lines("Verification:", _verification_lines(state))


def run_vib_memory_review(_: Namespace) -> None:
    path = _memory_path()
    review = _review_memory()(path)
    print("VibeLign Memory Review")
    if not review.has_memory:
        print("No memory yet.")
        _print_lines("Suggestions:", review.suggestions)
        return
    active = review.active_intent or "(none)"
    print(f"Active intent: {active}")
    print(f"Next action: {review.next_action or '(none)'}")
    _print_lines("Decisions:", review.decisions)
    _print_lines("Explicit relevant files:", review.relevant_files)
    _print_lines("Observed context:", review.observed_context)
    _print_lines("Next verification:", review.verification)
    _print_lines("Warnings:", review.warnings)
    secret_hits = int(getattr(review.redaction, "secret_hits", 0))
    privacy_hits = int(getattr(review.redaction, "privacy_hits", 0))
    summarized_fields = int(getattr(review.redaction, "summarized_fields", 0))
    print(
        "Redaction: "
        f"secrets={secret_hits}, privacy={privacy_hits}, summarized={summarized_fields}"
    )
    _print_lines("Suggestions:", review.suggestions)


def run_vib_memory_decide(args: Namespace) -> None:
    path = _memory_path()
    decision = " ".join(getattr(args, "decision", []) or []).strip()
    if not decision:
        print("Usage: vib memory decide \"decision text\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; decision was not saved.")
        return
    add_memory_decision(path, decision)
    print("Memory decision saved.")


def run_vib_memory_intent(args: Namespace) -> None:
    path = _memory_path()
    intent = " ".join(getattr(args, "intent", []) or []).strip()
    if not intent:
        print("Usage: vib memory intent \"current goal\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; active intent was not saved.")
        return
    set_memory_active_intent(path, intent)
    print("Memory active intent saved.")


def run_vib_memory_relevant(args: Namespace) -> None:
    path = _memory_path()
    rel_path = str(getattr(args, "path", "") or "").strip()
    why = " ".join(getattr(args, "why", []) or []).strip()
    if not rel_path or not why:
        print("Usage: vib memory relevant <path> \"why it matters\"")
        return
    if is_memory_read_only(path):
        print("Memory schema is newer than this VibeLign supports; relevant file was not saved.")
        return
    add_memory_relevant_file(path, rel_path, why, source="explicit")
    print("Memory relevant file saved.")


def _review_memory() -> _ReviewMemory:
    module = import_module("vibelign.core.memory.review")
    return cast(_ReviewMemory, getattr(module, "review_memory"))


def _verification_lines(state) -> list[str]:
    lines: list[str] = []
    for item in state.verification[-5:]:
        line = _dedupe_stale_labels(item.command)
        if item.stale and "(stale" not in line:
            line = f"{line} (stale)"
        lines.append(line)
    return lines


def _dedupe_stale_labels(line: str) -> str:
    marker = " (stale: scope unknown)"
    while line.count(marker) > 1:
        line = line.replace(marker + marker, marker)
    return line

# === ANCHOR: VIB_MEMORY_CMD_END ===
