"""
patch_suggester baseline lock — file/anchor 매칭 정확도를 수치로 고정.
MCP host-LLM pivot PoC 측정 기준선. 동등 이상이어야 회귀가 아님.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibelign.core.patch_suggester import suggest_patch

ROOT = Path(__file__).parent.parent.parent
SCENARIOS = json.loads(
    (ROOT / "tests" / "benchmark" / "scenarios.json").read_text(encoding="utf-8")
)
SAMPLE = ROOT / "tests" / "benchmark" / "sample_project"


def _normalize(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def _file_matches(actual: str, correct_files: list[str]) -> bool:
    a = _normalize(actual)
    return any(
        a.endswith(_normalize(c)) or _normalize(c).endswith(a) for c in correct_files
    )


def _anchor_matches(actual: str, correct_anchor: str | None) -> bool:
    if correct_anchor is None:
        return True
    return actual == correct_anchor


@pytest.fixture(scope="module")
def results() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for s in SCENARIOS:
        suggestion = suggest_patch(SAMPLE, str(s["request"]), use_ai=False)
        out.append(
            {
                "id": s["id"],
                "request": s["request"],
                "correct_files": s["correct_files"],
                "correct_anchor": s.get("correct_anchor"),
                "got_file": suggestion.target_file,
                "got_anchor": suggestion.target_anchor,
                "file_ok": _file_matches(
                    suggestion.target_file, [str(p) for p in s["correct_files"]]
                ),
                "anchor_ok": _anchor_matches(
                    suggestion.target_anchor, s.get("correct_anchor")
                ),
            }
        )
    return out


# Pinned after first run on 2026-05-13 against sample_project (20 scenarios).
BASELINE_FILE_PASSING: int = 14
BASELINE_ANCHOR_PASSING: int = 0


def test_file_accuracy_baseline(results: list[dict[str, object]]) -> None:
    """Lock current file-level matching count. Update value if intentional change."""
    passing = sum(1 for r in results if r["file_ok"])
    failed = [r["id"] for r in results if not r["file_ok"]]
    if BASELINE_FILE_PASSING is None:
        pytest.fail(
            f"BASELINE_FILE_PASSING is unset. Observed passing={passing} "
            f"out of {len(results)} scenarios. Failed: {failed}. "
            f"Update BASELINE_FILE_PASSING to {passing} and re-run."
        )
    assert passing == BASELINE_FILE_PASSING, (
        f"file accuracy regression — passing={passing}, "
        f"baseline={BASELINE_FILE_PASSING}.\n"
        f"failed scenarios: {failed}"
    )


def test_anchor_accuracy_baseline(results: list[dict[str, object]]) -> None:
    """Lock current anchor-level matching count among scenarios with a pinned anchor."""
    anchor_scenarios = [r for r in results if r["correct_anchor"] is not None]
    passing = sum(1 for r in anchor_scenarios if r["anchor_ok"])
    failed = [r["id"] for r in anchor_scenarios if not r["anchor_ok"]]
    if BASELINE_ANCHOR_PASSING is None:
        pytest.fail(
            f"BASELINE_ANCHOR_PASSING is unset. Observed passing={passing} "
            f"out of {len(anchor_scenarios)} anchor-pinned scenarios. "
            f"Failed: {failed}. Update BASELINE_ANCHOR_PASSING to {passing} and re-run."
        )
    assert passing == BASELINE_ANCHOR_PASSING, (
        f"anchor accuracy regression — passing={passing}, "
        f"baseline={BASELINE_ANCHOR_PASSING}.\n"
        f"failed: {failed}"
    )
