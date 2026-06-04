# === ANCHOR: BENCH_FIXTURES_START ===
from __future__ import annotations

from pathlib import Path

def _find_benchmark_dir() -> Path:
    """Locate `tests/benchmark/` across editable and uv-tool installs.

    When VibeLign is installed via `uv tool install`, `__file__` points into
    site-packages which has no sibling `tests/` tree — the __file__-based
    walk that works from a source checkout resolves to site-packages and
    returns a non-existent path. Fall back to walking up from cwd until we
    find `tests/benchmark/sample_project`. Callers run `vib bench` from
    inside the repo, so this is reliable.
    """
    candidate = Path(__file__).resolve().parents[2] / "tests" / "benchmark"
    if (candidate / "sample_project").exists():
        return candidate
    here = Path.cwd().resolve()
    for parent in (here, *here.parents):
        probe = parent / "tests" / "benchmark" / "sample_project"
        if probe.exists():
            return parent / "tests" / "benchmark"
    return candidate


BENCHMARK_DIR = _find_benchmark_dir()
SAMPLE_PROJECT = BENCHMARK_DIR / "sample_project"
# === ANCHOR: BENCH_FIXTURES_END ===
