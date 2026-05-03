from importlib import import_module
from typing import Callable, Protocol, cast

from vibelign.core.memory.models import (
    MemoryRelevantFile,
    MemoryState,
    MemoryTextField,
    MemoryVerification,
)


class _RedactedTextLike(Protocol):
    text: str
    redaction: object


class _RedactedMemorySummaryLike(Protocol):
    active_intent: str
    next_action: str
    decisions: list[str]
    relevant_files: list[str]
    verification: list[str]
    warnings: list[str]
    redaction: object


def _redact_memory_text() -> Callable[[str], _RedactedTextLike]:
    module = import_module("vibelign.core.memory.redaction")
    return cast(Callable[[str], _RedactedTextLike], getattr(module, "redact_memory_text"))


def _redact_memory_path() -> Callable[[str], _RedactedTextLike]:
    module = import_module("vibelign.core.memory.redaction")
    return cast(Callable[[str], _RedactedTextLike], getattr(module, "redact_memory_path"))


def _build_redacted_memory_summary() -> Callable[[MemoryState], _RedactedMemorySummaryLike]:
    module = import_module("vibelign.core.memory.redaction")
    return cast(
        Callable[[MemoryState], _RedactedMemorySummaryLike],
        getattr(module, "build_redacted_memory_summary"),
    )


def test_redact_memory_text_masks_secrets_and_private_context() -> None:
    secret_text = "tok" + "en=fixtureSecretValue1234"
    redacted = _redact_memory_text()(
        f"{secret_text} in /Users/alice/project with 192.168.1.10"
    )

    assert "fixtureSecretValue1234" not in redacted.text
    assert "/Users/alice" not in redacted.text
    assert "192.168.1.10" not in redacted.text
    assert "[redacted]" in redacted.text
    assert "[local-path]" in redacted.text
    assert "[private-ip]" in redacted.text
    assert int(getattr(redacted.redaction, "secret_hits", 0)) >= 1
    assert int(getattr(redacted.redaction, "privacy_hits", 0)) >= 2


def test_redact_memory_path_keeps_relative_paths_and_masks_absolute_paths() -> None:
    relative = _redact_memory_path()("vibelign/core/memory/store.py")
    absolute = _redact_memory_path()("/Users/alice/project/secret.py")

    assert relative.text == "vibelign/core/memory/store.py"
    assert int(getattr(relative.redaction, "privacy_hits", 0)) == 0
    assert absolute.text == "[local-path]/secret.py"
    assert int(getattr(absolute.redaction, "privacy_hits", 0)) == 1


def test_build_redacted_memory_summary_preserves_structure_and_counts() -> None:
    secret_text = "tok" + "en=fixtureSecretValue1234"
    state = MemoryState(
        active_intent=MemoryTextField(text=f"Fix {secret_text}"),
        next_action=MemoryTextField(text="Check /Users/alice/project before handoff"),
        decisions=[MemoryTextField(text="Use typed redaction summary")],
        relevant_files=[
            MemoryRelevantFile(
                path="vibelign/core/memory/redaction.py",
                why="redaction service",
                source="explicit",
            )
        ],
        verification=[MemoryVerification(command="pytest tests/test_memory_redaction.py", stale=True)],
        risks=[MemoryTextField(text="Internal host build.local appeared")],
    )

    summary = _build_redacted_memory_summary()(state)
    rendered = "\n".join(
        [summary.active_intent, summary.next_action]
        + summary.decisions
        + summary.relevant_files
        + summary.verification
        + summary.warnings
    )

    assert "fixtureSecretValue1234" not in rendered
    assert "/Users/alice" not in rendered
    assert "build.local" not in rendered
    assert "[redacted]" in rendered
    assert "[local-path]" in rendered
    assert "[internal-host]" in rendered
    assert summary.relevant_files == ["vibelign/core/memory/redaction.py — redaction service"]
    assert summary.verification == ["pytest tests/test_memory_redaction.py (stale: stale)"]
    assert int(getattr(summary.redaction, "secret_hits", 0)) >= 1
    assert int(getattr(summary.redaction, "privacy_hits", 0)) >= 2
