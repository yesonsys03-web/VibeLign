# C5 Patch Accuracy Bench Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `vib bench --patch`, a single-command reproducible patch-accuracy regression runner backed by a pinned-intent sandbox and a committed baseline file.

**Architecture:**
Extract `suggest_patch`'s file-ranking loop into a reusable `score_candidates` helper. Move the pinned-intent sandbox fixture out of the test module and into `vibelign/commands/bench_fixtures.py` so both pytest and the runner share one canonical setup path. Add a new `_run_patch_accuracy` handler to `vib_bench_cmd.py` that measures 5 scenarios × 2 modes (deterministic / `--ai`), computes 3 metrics (files_ok, anchor_ok, prefilter_recall@3), diffs against `tests/benchmark/patch_accuracy_baseline.json`, and exits 1 on regression. Baseline updates are manual (`--update-baseline`).

**Tech Stack:** Python 3.11+, unittest.mock, pytest (via `uv run --with pytest`), argparse, existing `vibelign` patch-suggester internals.

**Spec:** `docs/superpowers/specs/2026-04-12-patch-accuracy-c5-bench-runner-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `vibelign/core/patch_suggester.py` | MODIFY | Extract `_score_all_files` helper and expose public `score_candidates(root, request) -> list[tuple[Path, int]]`. `suggest_patch` delegates to the helper (behavior preserved). |
| `vibelign/commands/bench_fixtures.py` | CREATE | `PINNED_INTENTS` dict + `prepare_patch_sandbox(tmp)` fixture. Single source of truth for the pinned-intent sandbox. |
| `tests/test_patch_accuracy_scenarios.py` | MODIFY | Re-import `PINNED_INTENTS` / `prepare_patch_sandbox` from `bench_fixtures`. Remove the inline copies. No behavior change. |
| `tests/test_patch_suggester_score_candidates.py` | CREATE | Unit test for `score_candidates`: 5 scenarios, top-1 matches `suggest_patch`'s `target_file`, scores are monotonically non-increasing. |
| `vibelign/commands/vib_bench_cmd.py` | MODIFY | Add metric helpers, `_run_patch_accuracy(args)`, baseline load/diff/write helpers. Route `args.patch` in `run_vib_bench`. |
| `vibelign/cli/cli_command_groups.py` | MODIFY | Register `--patch` and `--update-baseline` flags on the `bench` subparser. |
| `tests/benchmark/patch_accuracy_baseline.json` | CREATE | Initial baseline (C6-era results, pinned intents, 2026-04-12). |
| `tests/test_bench_patch_command.py` | CREATE | In-process unit test of `_run_patch_accuracy` with `_ai_select_file` mocked; verifies metric computation, baseline diff, exit-code logic. |

**Architectural rationale — why in-process tests, not subprocess:**
The spec §9.2 suggests subprocess E2E. During plan review I switched this to in-process + mocked `_ai_select_file` because:
1. `--ai` mode on `fix_login_lock_bug` (low confidence) would hit Gemini on every run, making the test flaky and network-dependent.
2. Mocking at the subprocess boundary is painful; at the function-call boundary it's one `with mock_patch(...)` block.
3. The real `vib bench --patch` smoke (Task 8) is the human acceptance check — no network-free automated test can replace it.

This is a spec deviation, noted here and called out in Task 8.

---

## Task 1: Extract `score_candidates` from `suggest_patch`

**Files:**
- Modify: `vibelign/core/patch_suggester.py:1140-1179` (extract ranking loop)
- Test: `tests/test_patch_suggester_score_candidates.py` (new)

- [ ] **Step 1: Write the failing unit test**

Create `tests/test_patch_suggester_score_candidates.py`:

```python
"""Unit test for score_candidates: prove behavior-preserving extraction.

score_candidates should return the same file ordering that suggest_patch
uses internally. The guarantee we check: suggest_patch's target_file
appears as score_candidates' top-1 (same ranking loop, same inputs).
"""
import json
import tempfile
import unittest
from pathlib import Path

from vibelign.commands.bench_fixtures import prepare_patch_sandbox
from vibelign.core.patch_suggester import score_candidates, suggest_patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = REPO_ROOT / "tests" / "benchmark" / "scenarios.json"


class ScoreCandidatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = prepare_patch_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = json.load(fh)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_top1_matches_suggest_patch_target_file(self):
        for sc in self.scenarios:
            with self.subTest(scenario=sc["id"]):
                candidates = score_candidates(self.sandbox, sc["request"])
                self.assertGreater(len(candidates), 0)
                top1_path, _top1_score = candidates[0]
                top1_rel = str(top1_path.relative_to(self.sandbox)).replace("\\", "/")

                det_result = suggest_patch(
                    self.sandbox, sc["request"], use_ai=False
                )
                self.assertEqual(
                    top1_rel,
                    det_result.target_file,
                    f"score_candidates top-1 ({top1_rel}) must match "
                    f"suggest_patch target_file ({det_result.target_file}) "
                    f"for scenario {sc['id']}",
                )

    def test_scores_are_monotonically_non_increasing(self):
        sc = self.scenarios[0]
        candidates = score_candidates(self.sandbox, sc["request"])
        scores = [score for _path, score in candidates]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(
                scores[i],
                scores[i + 1],
                f"score_candidates must be sorted descending: "
                f"index {i}={scores[i]} < {i+1}={scores[i+1]}",
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --with pytest python -m pytest tests/test_patch_suggester_score_candidates.py -v`
Expected: FAIL with `ImportError: cannot import name 'score_candidates'` (and possibly `prepare_patch_sandbox`). That's fine — both come from later tasks. **For this task we only need the `score_candidates` import to start working.**

If `prepare_patch_sandbox` isn't yet defined (Task 2), this test won't run. To unblock Task 1 alone, temporarily inline a `_prepare_sandbox` copy at the top of this test file, then delete it at the end of Task 2. **OR** — simpler — do Task 2 before Step 2 of Task 1. Recommendation: implement Task 1 Step 1 (write this test file), jump to Task 2 (create `bench_fixtures.py`), then come back and run Step 2.

- [ ] **Step 3: Extract `_score_all_files` helper in patch_suggester.py**

Open `vibelign/core/patch_suggester.py`. Find `def suggest_patch(root: Path, request: str, use_ai: bool = True)` (around line 1140). Replace the top of the function body (lines 1140-1179, the part that builds `scored` and sorts it) with a call to a new internal helper.

Insert this new helper **immediately above** `def suggest_patch`:

```python
def _score_all_files(
    root: Path, request: str
) -> tuple[list[tuple[int, Path, list[str]]], dict, dict, object, object]:
    """Rank every source file under `root` for the given `request`.

    Returns (scored, metadata, anchor_meta, project_map, ui_label_idx).
    `scored` is sorted descending by score, ties broken by path string.
    `suggest_patch` consumes all 5 return values; `score_candidates`
    consumes only `scored`.
    """
    from vibelign.core.anchor_tools import load_anchor_meta

    request_tokens = tokenize(request)
    metadata = load_anchor_metadata(root)
    anchor_meta = load_anchor_meta(root)
    project_map, _err = load_project_map(root)
    ui_label_idx = load_ui_label_index(root)
    scored: list[tuple[int, Path, list[str]]] = []
    for path in iter_source_files(root):
        rel = relpath_str(root, path)
        score, rationale = score_path(
            path,
            request_tokens,
            rel,
            metadata.get(rel, {}),
            project_map,
            intent_meta=anchor_meta,
        )
        if ui_label_idx:
            ui_boost, ui_reasons = score_boost_for_ui_labels(
                rel, request_tokens, ui_label_idx
            )
            if ui_boost:
                score += ui_boost + 8
                rationale = rationale + ui_reasons
        scored.append((score, path, rationale))
    scored.sort(key=lambda x: (-x[0], str(x[1])))
    return scored, metadata, anchor_meta, project_map, ui_label_idx


def score_candidates(root: Path, request: str) -> list[tuple[Path, int]]:
    """Public API: return files ranked for `request`, descending by score.

    Used by the patch-accuracy benchmark runner to measure prefilter recall.
    This is the same ranking `suggest_patch` uses internally before the
    AI-select / anchor-pick stages — extracted so downstream tooling can
    inspect the raw deterministic order.
    """
    scored, *_ = _score_all_files(root, request)
    return [(path, score) for score, path, _rationale in scored]
```

Now modify `suggest_patch` to call `_score_all_files`. Replace the block from line 1141 to line 1179 (the `from vibelign.core.anchor_tools import load_anchor_meta` line through `scored.sort(...)`) with:

```python
    scored, metadata, anchor_meta, project_map, _ui_label_idx = _score_all_files(
        root, request
    )
    request_tokens = tokenize(request)
```

Leave everything from `if not scored:` (around line 1170) onward untouched.

**Important:** `request_tokens` is still used in the rest of `suggest_patch` (for `choose_anchor`, `_is_stateful_ui_request`, etc.), so we recompute it on line ~1143. `_score_all_files` tokenizes internally but doesn't return it — duplicating the one-liner keeps the helper's return tuple from bloating.

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_patch_suggester_score_candidates.py -v`
Expected: Both tests PASS. If `test_top1_matches_suggest_patch_target_file` fails for any scenario, the extraction changed behavior — revert and retry.

- [ ] **Step 5: Run the existing patch accuracy regression suite**

Run: `uv run --with pytest python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: All 5 tests PASS (3 scenario tests + 2 deference tests). Any failure means the refactor broke `suggest_patch`'s behavior.

- [ ] **Step 6: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_patch_suggester_score_candidates.py
git commit -m "$(cat <<'EOF'
refactor(patch-suggester): extract score_candidates public API

Pull the file-ranking loop out of suggest_patch into _score_all_files
and expose score_candidates as a public API. Behavior-preserving:
suggest_patch still uses the same ranking, same tie-breaking, same
confidence bookkeeping. The bench runner (C5) will use score_candidates
to measure prefilter_recall@3 independent of suggest_patch's AI-select
stage.
EOF
)"
```

---

## Task 2: Create `bench_fixtures.py` — shared pinned-intent sandbox

**Files:**
- Create: `vibelign/commands/bench_fixtures.py`
- Modify: `tests/test_patch_accuracy_scenarios.py` (re-import from `bench_fixtures`)

- [ ] **Step 1: Create the new module**

Create `vibelign/commands/bench_fixtures.py`:

```python
"""Shared fixtures for patch-accuracy measurement.

Moved here from tests/test_patch_accuracy_scenarios.py so that both the
test suite and `vib bench --patch` can share one canonical sandbox setup
path. Pinned intents make measurement hermetic (vib anchor --auto calls
an LLM, which drifts across runs).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PROJECT = _REPO_ROOT / "tests" / "benchmark" / "sample_project"

PINNED_INTENTS: dict[str, str] = {
    "DATABASE_INIT_DB": "데이터를 저장할 빈 공간을 처음 준비합니다.",
    "DATABASE_CREATE_USER": "회원 정보를 새로 만들어 명부에 등록합니다.",
    "DATABASE_FIND_USER_BY_EMAIL": "이메일로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_FIND_USER_BY_ID": "고유 번호로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_UPDATE_USER": "회원의 등록 정보를 최신으로 수정합니다.",
    "DATABASE_UPDATE_LOGIN_ATTEMPTS": "로그인 시도 횟수를 기록하고 업데이트합니다.",
    "AUTH__HASH_PASSWORD": "비밀번호를 안전하게 암호로 바꿉니다.",
    "AUTH__GENERATE_TOKEN": "사용자 인증을 위한 암호 키를 만듭니다.",
    "AUTH_LOGIN_USER": "이메일과 비밀번호로 로그인을 처리합니다.",
    "AUTH_REGISTER_USER": "새로운 사용자의 회원가입을 처리합니다.",
    "APP_MAIN": "프로그램을 실행하고 서버를 시작합니다.",
    "USERS_GET_USER_PROFILE": "공개 가능한 사용자 정보를 가져옵니다.",
    "USERS_UPDATE_USER_PROFILE": "사용자의 이름과 소개글을 수정합니다.",
    "VALIDATORS_VALIDATE_EMAIL": "이메일 주소 형식이 올바른지 확인합니다.",
    "VALIDATORS_VALIDATE_EMAIL_DOMAIN": "허용된 이메일 도메인인지 확인합니다.",
    "VALIDATORS_VALIDATE_PASSWORD": "비밀번호가 조건에 맞는지 확인합니다.",
    "SIGNUP_RENDER_SIGNUP_FORM": "회원가입 화면을 보여줄 양식을 만듭니다.",
    "SIGNUP_HANDLE_SIGNUP": "입력한 회원가입 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_FORM": "로그인 화면을 보여줄 양식을 만듭니다.",
    "LOGIN_HANDLE_LOGIN": "입력한 로그인 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_ERROR": "로그인 실패 시 오류 메시지를 보여줍니다.",
    "PROFILE_RENDER_PROFILE": "사용자 프로필 화면을 보여줄 양식을 만듭니다.",
    "PROFILE_HANDLE_PROFILE_UPDATE": "수정된 프로필 정보를 받아 저장합니다.",
    "CONFIG": "프로그램 설정 값을 모아 놓은 곳입니다.",
}

PINNED_INTENTS_VERSION = "2026-04-12"


def prepare_patch_sandbox(tmp: Path) -> Path:
    """Copy sample_project into `tmp`, insert anchors, pin intents.

    Returns the sandbox project root. Caller owns `tmp` lifecycle.
    Calls `vib start` and `vib anchor --auto` via subprocess — both are
    deterministic (marker insertion + anchor_index.json generation).
    Then overwrites anchor_meta.json with PINNED_INTENTS so the downstream
    patch-suggester scoring is reproducible across machines.
    """
    dst = tmp / "project"
    shutil.copytree(SAMPLE_PROJECT, dst)
    subprocess.run(
        ["vib", "start"],
        cwd=dst,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["vib", "anchor", "--auto"],
        cwd=dst,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    meta_path = dst / ".vibelign" / "anchor_meta.json"
    meta_path.write_text(
        json.dumps(
            {name: {"intent": text} for name, text in PINNED_INTENTS.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return dst
```

- [ ] **Step 2: Refactor `tests/test_patch_accuracy_scenarios.py` to import from bench_fixtures**

Open `tests/test_patch_accuracy_scenarios.py`. Replace the top of the file (lines 1-80, up to and including the `_prepare_sandbox` function) with:

```python
import json
import tempfile
import unittest
from pathlib import Path

from vibelign.commands.bench_fixtures import (
    PINNED_INTENTS as _PINNED_INTENTS,
    prepare_patch_sandbox as _prepare_sandbox,
)
from vibelign.core.patch_suggester import suggest_patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = REPO_ROOT / "tests" / "benchmark" / "scenarios.json"


# Backwards-compat aliases retained in case anything else imports them.
__all__ = ["_PINNED_INTENTS", "_prepare_sandbox"]
```

Leave the two test classes (`PatchAccuracyScenarioTest` and `TestAIDeference`) untouched — they already reference `_prepare_sandbox` and `_PINNED_INTENTS` via the local names.

Note: `shutil` and `subprocess` imports were only used by the removed `_prepare_sandbox`; they can be deleted if nothing else in the file uses them. Check with a quick `grep -n "shutil\|subprocess" tests/test_patch_accuracy_scenarios.py` after editing. If zero matches outside the import line, delete the imports.

- [ ] **Step 3: Run both test files to verify behavior is preserved**

Run: `uv run --with pytest python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_patch_suggester_score_candidates.py -v`
Expected: All tests PASS (5 from scenarios, 2 from score_candidates = 7 total).

If `test_patch_suggester_score_candidates.py` imports still fail, confirm `vibelign/commands/bench_fixtures.py` is importable: `uv run python -c "from vibelign.commands.bench_fixtures import PINNED_INTENTS, prepare_patch_sandbox; print(len(PINNED_INTENTS))"` — expected output: `24`.

- [ ] **Step 4: Commit**

```bash
git add vibelign/commands/bench_fixtures.py tests/test_patch_accuracy_scenarios.py
git commit -m "$(cat <<'EOF'
refactor(bench): extract pinned-intent sandbox to bench_fixtures

Move PINNED_INTENTS and prepare_patch_sandbox from the test module into
vibelign/commands/bench_fixtures.py so the forthcoming `vib bench --patch`
runner can share the same canonical sandbox setup. No behavior change:
test_patch_accuracy_scenarios.py re-imports under its private aliases.
EOF
)"
```

---

## Task 3: Create initial baseline file

**Files:**
- Create: `tests/benchmark/patch_accuracy_baseline.json`

- [ ] **Step 1: Write the baseline file with current C6 values**

Create `tests/benchmark/patch_accuracy_baseline.json`:

```json
{
  "pinned_intents_version": "2026-04-12",
  "generated_at": "2026-04-12",
  "notes": "Initial baseline after C1 (verb-aware ranking) + C6 (AI deference rule). Update manually via `vib bench --patch --update-baseline` after intended changes.",
  "scenarios": {
    "change_error_msg": {
      "det": {"files_ok": true, "anchor_ok": true, "recall_at_3": true},
      "ai":  {"files_ok": true, "anchor_ok": true, "recall_at_3": true}
    },
    "add_email_domain_check": {
      "det": {"files_ok": false, "anchor_ok": false, "recall_at_3": false},
      "ai":  {"files_ok": false, "anchor_ok": false, "recall_at_3": false}
    },
    "fix_login_lock_bug": {
      "det": {"files_ok": true, "anchor_ok": true, "recall_at_3": true},
      "ai":  {"files_ok": true, "anchor_ok": true, "recall_at_3": true}
    },
    "add_bio_length_limit": {
      "det": {"files_ok": true, "anchor_ok": true, "recall_at_3": true},
      "ai":  {"files_ok": true, "anchor_ok": true, "recall_at_3": true}
    },
    "add_password_change": {
      "det": {"files_ok": false, "anchor_ok": null, "recall_at_3": true},
      "ai":  {"files_ok": false, "anchor_ok": null, "recall_at_3": true}
    }
  },
  "totals": {
    "det": {"files_ok": "3/5", "anchor_ok": "3/4", "recall_at_3": "4/5"},
    "ai":  {"files_ok": "3/5", "anchor_ok": "3/4", "recall_at_3": "4/5"}
  }
}
```

**Important notes on the initial values:**
- `add_password_change.correct_anchor` is `null` in `scenarios.json`, so `anchor_ok` is always `null` for that scenario (not counted in totals denominator).
- `anchor_ok` totals are `3/4` because 4 scenarios have a `correct_anchor` and 3 of those pass.
- `recall_at_3` values are provisional — Task 7 will verify and adjust them against the actual deterministic ranking. If Task 7 finds a different value, that's the correct initial baseline. The unit-test for the runner (Task 6) does NOT assert against these specific values — only structure and diff logic — so a one-time correction in Task 7 is clean.
- `add_password_change.recall_at_3` being `true` is the assumption: at least one of `api/auth.py` or `pages/profile.py` appears in the deterministic top-3. Verified empirically in Task 7.

- [ ] **Step 2: Do NOT commit yet**

The file will be committed together with the runner in a later task, after Task 7 verifies the values. For now leave it uncommitted; it's a fixture for Task 6's test.

---

## Task 4a: Metric helpers in `vib_bench_cmd.py`

**Files:**
- Modify: `vibelign/commands/vib_bench_cmd.py` (add pure helper functions)
- Test: `tests/test_bench_patch_command.py` (new — will hold all Task 6 tests too)

- [ ] **Step 1: Write failing tests for the metric helpers**

Create `tests/test_bench_patch_command.py`:

```python
"""In-process unit tests for `vib bench --patch` runner internals.

We mock `_ai_select_file` so tests never hit the network. The real
end-to-end smoke (actual `vib bench --patch` invocation) is done
manually in Task 8 of the plan and is not part of the automated suite.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch as mock_patch

from vibelign.commands.vib_bench_cmd import (
    _compute_files_ok,
    _compute_anchor_ok,
    _compute_recall_at_3,
)


class MetricHelpersTest(unittest.TestCase):
    def test_files_ok_matches_any_correct_file(self):
        self.assertTrue(_compute_files_ok("pages/login.py", ["pages/login.py"]))
        self.assertTrue(
            _compute_files_ok(
                "api/auth.py", ["api/auth.py", "pages/profile.py"]
            )
        )

    def test_files_ok_rejects_wrong_file(self):
        self.assertFalse(
            _compute_files_ok("core/validators.py", ["pages/login.py"])
        )

    def test_anchor_ok_returns_none_when_scenario_has_no_anchor(self):
        self.assertIsNone(_compute_anchor_ok("ANY_ANCHOR", None))

    def test_anchor_ok_true_on_match(self):
        self.assertTrue(
            _compute_anchor_ok("LOGIN_HANDLE_LOGIN", "LOGIN_HANDLE_LOGIN")
        )

    def test_anchor_ok_false_on_mismatch(self):
        self.assertFalse(
            _compute_anchor_ok("LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN")
        )

    def test_recall_at_3_true_when_correct_in_top3(self):
        # candidates is list[tuple[str, int]] of relpath -> score,
        # already sorted descending.
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
            ("core/database.py", 4),
        ]
        self.assertTrue(_compute_recall_at_3(candidates, ["api/auth.py"]))
        self.assertTrue(_compute_recall_at_3(candidates, ["pages/login.py"]))

    def test_recall_at_3_false_when_correct_below_top3(self):
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
            ("core/database.py", 4),
            ("core/validators.py", 2),
        ]
        self.assertFalse(_compute_recall_at_3(candidates, ["core/validators.py"]))

    def test_recall_at_3_true_if_any_correct_file_in_top3(self):
        candidates = [
            ("pages/login.py", 20),
            ("api/auth.py", 12),
            ("pages/signup.py", 8),
        ]
        self.assertTrue(
            _compute_recall_at_3(
                candidates, ["core/validators.py", "pages/login.py"]
            )
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py::MetricHelpersTest -v`
Expected: FAIL with `ImportError: cannot import name '_compute_files_ok'`.

- [ ] **Step 3: Add the metric helpers to `vib_bench_cmd.py`**

Open `vibelign/commands/vib_bench_cmd.py`. Immediately after the existing `SCENARIOS_PATH = ...` line near the top, add a new section:

```python
# === ANCHOR: VIB_BENCH_PATCH_METRICS_START ===
# Patch-accuracy bench runner helpers (C5, 2026-04-12).

PATCH_BASELINE_PATH = BENCHMARK_DIR / "patch_accuracy_baseline.json"
PATCH_PREFILTER_TOP_N = 3


def _compute_files_ok(target_file: str, correct_files: list[str]) -> bool:
    """True when suggest_patch's target_file is in the scenario's correct set."""
    return target_file in correct_files


def _compute_anchor_ok(
    target_anchor: str, correct_anchor: str | None
) -> bool | None:
    """True/False when the scenario specifies an anchor, None otherwise.

    Scenarios like `add_password_change` have `correct_anchor: null` — they
    are excluded from the anchor_ok denominator.
    """
    if correct_anchor is None:
        return None
    return target_anchor == correct_anchor


def _compute_recall_at_3(
    candidates: list[tuple[str, int]], correct_files: list[str]
) -> bool:
    """True when any correct file appears in the top-N deterministic candidates.

    `candidates` is a list of (relpath, score) pairs already sorted descending.
    N = PATCH_PREFILTER_TOP_N.
    """
    top_paths = {relpath for relpath, _score in candidates[:PATCH_PREFILTER_TOP_N]}
    return any(cf in top_paths for cf in correct_files)


# === ANCHOR: VIB_BENCH_PATCH_METRICS_END ===
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py::MetricHelpersTest -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add vibelign/commands/vib_bench_cmd.py tests/test_bench_patch_command.py
git commit -m "$(cat <<'EOF'
feat(bench): add patch-accuracy metric helpers

Pure helpers for the forthcoming `vib bench --patch` runner:
_compute_files_ok, _compute_anchor_ok, _compute_recall_at_3. Unit-tested
in isolation from the measurement loop so the runner can rely on them
as trusted building blocks.
EOF
)"
```

---

## Task 4b: Measurement loop + baseline I/O

**Files:**
- Modify: `vibelign/commands/vib_bench_cmd.py` (add measurement + baseline logic)
- Test: `tests/test_bench_patch_command.py` (extend)

- [ ] **Step 1: Write failing tests for the measurement + baseline functions**

Append to `tests/test_bench_patch_command.py`:

```python
class MeasureAndDiffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from vibelign.commands.bench_fixtures import prepare_patch_sandbox

        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = prepare_patch_sandbox(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_measure_returns_full_result_dict(self):
        """_measure_patch_accuracy returns per-scenario metrics for both modes."""
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        self.assertIn("scenarios", result)
        self.assertIn("totals", result)
        # All 5 scenarios present, both modes (det, ai)
        for sid in [
            "change_error_msg",
            "add_email_domain_check",
            "fix_login_lock_bug",
            "add_bio_length_limit",
            "add_password_change",
        ]:
            self.assertIn(sid, result["scenarios"], f"missing scenario {sid}")
            for mode in ("det", "ai"):
                self.assertIn(mode, result["scenarios"][sid])
                entry = result["scenarios"][sid][mode]
                self.assertIn("files_ok", entry)
                self.assertIn("anchor_ok", entry)
                self.assertIn("recall_at_3", entry)
                self.assertIsInstance(entry["files_ok"], bool)

    def test_add_password_change_anchor_ok_is_none(self):
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        self.assertIsNone(
            result["scenarios"]["add_password_change"]["det"]["anchor_ok"]
        )
        self.assertIsNone(
            result["scenarios"]["add_password_change"]["ai"]["anchor_ok"]
        )

    def test_totals_string_format(self):
        from vibelign.commands.vib_bench_cmd import _measure_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            result = _measure_patch_accuracy(self.sandbox)

        det_totals = result["totals"]["det"]
        self.assertRegex(det_totals["files_ok"], r"^\d+/5$")
        self.assertRegex(det_totals["anchor_ok"], r"^\d+/4$")
        self.assertRegex(det_totals["recall_at_3"], r"^\d+/5$")


class BaselineDiffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = {
            "scenarios": {
                "change_error_msg": {
                    "det": {"files_ok": True, "anchor_ok": True, "recall_at_3": True},
                    "ai":  {"files_ok": True, "anchor_ok": True, "recall_at_3": True},
                },
            },
            "totals": {
                "det": {"files_ok": "1/1", "anchor_ok": "1/1", "recall_at_3": "1/1"},
                "ai":  {"files_ok": "1/1", "anchor_ok": "1/1", "recall_at_3": "1/1"},
            },
        }

    def test_no_diff_when_identical(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        current = json.loads(json.dumps(self.baseline))
        diff = _diff_against_baseline(current, self.baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(diff["improvements"], [])

    def test_regression_detected(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        current = json.loads(json.dumps(self.baseline))
        current["scenarios"]["change_error_msg"]["det"]["files_ok"] = False
        diff = _diff_against_baseline(current, self.baseline)
        self.assertEqual(len(diff["regressions"]), 1)
        self.assertEqual(
            diff["regressions"][0],
            {
                "scenario": "change_error_msg",
                "mode": "det",
                "metric": "files_ok",
                "was": True,
                "now": False,
            },
        )
        self.assertEqual(diff["improvements"], [])

    def test_improvement_detected(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        baseline = json.loads(json.dumps(self.baseline))
        baseline["scenarios"]["change_error_msg"]["ai"]["recall_at_3"] = False
        current = json.loads(json.dumps(self.baseline))
        diff = _diff_against_baseline(current, baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(len(diff["improvements"]), 1)

    def test_null_anchor_ok_treated_as_na_not_regression(self):
        from vibelign.commands.vib_bench_cmd import _diff_against_baseline

        baseline = {
            "scenarios": {
                "add_password_change": {
                    "det": {"files_ok": False, "anchor_ok": None, "recall_at_3": True},
                    "ai":  {"files_ok": False, "anchor_ok": None, "recall_at_3": True},
                },
            },
            "totals": {
                "det": {"files_ok": "0/1", "anchor_ok": "0/0", "recall_at_3": "1/1"},
                "ai":  {"files_ok": "0/1", "anchor_ok": "0/0", "recall_at_3": "1/1"},
            },
        }
        current = json.loads(json.dumps(baseline))
        diff = _diff_against_baseline(current, baseline)
        self.assertEqual(diff["regressions"], [])
        self.assertEqual(diff["improvements"], [])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py::MeasureAndDiffTest tests/test_bench_patch_command.py::BaselineDiffTest -v`
Expected: FAIL with `ImportError` on `_measure_patch_accuracy` and `_diff_against_baseline`.

- [ ] **Step 3: Implement `_measure_patch_accuracy`**

Append to `vibelign/commands/vib_bench_cmd.py` (after the metric helpers added in Task 4a, and after the `VIB_BENCH_PATCH_METRICS_END` anchor but before `_empty_project_map`):

```python
# === ANCHOR: VIB_BENCH_PATCH_MEASURE_START ===


def _measure_patch_accuracy(sandbox: Path) -> dict:
    """Run all 5 scenarios × 2 modes against `sandbox`, compute metrics.

    `sandbox` must already be prepared via `prepare_patch_sandbox`.
    Returns a dict with `scenarios` (per-scenario metric map) and `totals`
    (aggregated strings like "3/5"). Ready to diff against a baseline file.
    """
    from vibelign.core.patch_suggester import score_candidates, suggest_patch

    scenarios_raw = _load_scenarios()
    scenarios: dict[str, dict] = {}

    for sc in scenarios_raw:
        sid = sc["id"]
        request = sc["request"]
        correct_files = list(sc["correct_files"])
        correct_anchor = sc.get("correct_anchor")

        candidates = score_candidates(sandbox, request)
        candidate_relpaths = [
            (
                str(path.relative_to(sandbox)).replace("\\", "/"),
                score,
            )
            for path, score in candidates
        ]
        recall = _compute_recall_at_3(candidate_relpaths, correct_files)

        entry: dict[str, dict] = {}
        for mode_key, use_ai in (("det", False), ("ai", True)):
            result = suggest_patch(sandbox, request, use_ai=use_ai)
            entry[mode_key] = {
                "files_ok": _compute_files_ok(result.target_file, correct_files),
                "anchor_ok": _compute_anchor_ok(
                    result.target_anchor, correct_anchor
                ),
                "recall_at_3": recall,
            }
        scenarios[sid] = entry

    totals = _compute_totals(scenarios)
    return {"scenarios": scenarios, "totals": totals}


def _compute_totals(scenarios: dict[str, dict]) -> dict[str, dict[str, str]]:
    """Aggregate per-scenario booleans into 'N/M' strings by mode.

    - files_ok / recall_at_3 denominator = number of scenarios
    - anchor_ok denominator = scenarios where anchor_ok is not None
    """
    n_scenarios = len(scenarios)
    totals: dict[str, dict[str, str]] = {}
    for mode in ("det", "ai"):
        files_hits = sum(
            1 for s in scenarios.values() if s[mode]["files_ok"]
        )
        anchor_hits = sum(
            1
            for s in scenarios.values()
            if s[mode]["anchor_ok"] is True
        )
        anchor_total = sum(
            1
            for s in scenarios.values()
            if s[mode]["anchor_ok"] is not None
        )
        recall_hits = sum(
            1 for s in scenarios.values() if s[mode]["recall_at_3"]
        )
        totals[mode] = {
            "files_ok": f"{files_hits}/{n_scenarios}",
            "anchor_ok": f"{anchor_hits}/{anchor_total}",
            "recall_at_3": f"{recall_hits}/{n_scenarios}",
        }
    return totals


def _load_patch_baseline() -> dict | None:
    """Read `patch_accuracy_baseline.json`. Returns None if missing."""
    if not PATCH_BASELINE_PATH.exists():
        return None
    return json.loads(PATCH_BASELINE_PATH.read_text(encoding="utf-8"))


def _diff_against_baseline(current: dict, baseline: dict) -> dict:
    """Compute regressions + improvements per (scenario, mode, metric).

    Regression: baseline was True, current is False.
    Improvement: baseline was False, current is True.
    None (anchor_ok for no-anchor scenarios) is never a regression or improvement.
    """
    regressions: list[dict] = []
    improvements: list[dict] = []
    cur_scenarios = current.get("scenarios", {})
    base_scenarios = baseline.get("scenarios", {})
    for sid, cur_entry in cur_scenarios.items():
        base_entry = base_scenarios.get(sid, {})
        for mode in ("det", "ai"):
            cur_metrics = cur_entry.get(mode, {})
            base_metrics = base_entry.get(mode, {})
            for metric in ("files_ok", "anchor_ok", "recall_at_3"):
                was = base_metrics.get(metric)
                now = cur_metrics.get(metric)
                if was is None or now is None:
                    continue
                if was is True and now is False:
                    regressions.append(
                        {
                            "scenario": sid,
                            "mode": mode,
                            "metric": metric,
                            "was": was,
                            "now": now,
                        }
                    )
                elif was is False and now is True:
                    improvements.append(
                        {
                            "scenario": sid,
                            "mode": mode,
                            "metric": metric,
                            "was": was,
                            "now": now,
                        }
                    )
    return {"regressions": regressions, "improvements": improvements}


def _write_patch_baseline(current: dict) -> None:
    """Overwrite the baseline file with `current`, preserving metadata."""
    payload = {
        "pinned_intents_version": "2026-04-12",
        "generated_at": "2026-04-12",
        "notes": (
            "Updated via `vib bench --patch --update-baseline`. "
            "See docs/superpowers/specs/2026-04-12-patch-accuracy-c5-bench-runner-design.md."
        ),
        "scenarios": current["scenarios"],
        "totals": current["totals"],
    }
    PATCH_BASELINE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# === ANCHOR: VIB_BENCH_PATCH_MEASURE_END ===
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py -v`
Expected: All tests PASS (MetricHelpersTest from Task 4a + MeasureAndDiffTest + BaselineDiffTest).

**Important:** `MeasureAndDiffTest` actually runs `prepare_patch_sandbox` (which calls `vib start` + `vib anchor --auto` via subprocess) and `_measure_patch_accuracy` end-to-end. This is slow (~20-40s) and requires the `vib` CLI to be installed. If it fails with `FileNotFoundError: vib`, run `uv tool install --reinstall --force .` first.

- [ ] **Step 5: Commit**

```bash
git add vibelign/commands/vib_bench_cmd.py tests/test_bench_patch_command.py
git commit -m "$(cat <<'EOF'
feat(bench): patch accuracy measurement loop + baseline diff

Add _measure_patch_accuracy (5 scenarios × 2 modes), _compute_totals
(N/M aggregation with anchor_ok None handling), _load_patch_baseline,
_diff_against_baseline (regression vs improvement), _write_patch_baseline.
Tested in isolation with mocked _ai_select_file.
EOF
)"
```

---

## Task 4c: Runner entry point + report formatting

**Files:**
- Modify: `vibelign/commands/vib_bench_cmd.py` (add `_run_patch_accuracy`, modify `run_vib_bench`)

- [ ] **Step 1: Add the runner entry point and report formatter**

Append to `vibelign/commands/vib_bench_cmd.py` (after the `VIB_BENCH_PATCH_MEASURE_END` anchor):

```python
# === ANCHOR: VIB_BENCH_PATCH_RUNNER_START ===


def _format_patch_report(current: dict, baseline: dict | None, diff: dict) -> str:
    """Human-readable report showing totals vs baseline + per-scenario rows."""
    lines = []
    lines.append(
        "Patch accuracy benchmark (pinned intents, 5 scenarios × 2 modes)"
    )
    if baseline is not None:
        lines.append(
            f"Baseline: {PATCH_BASELINE_PATH.relative_to(BENCHMARK_DIR.parent)} "
            f"({baseline.get('generated_at', 'unknown')})"
        )
    else:
        lines.append("Baseline: (none — this run could be used as a new baseline)")
    lines.append("")

    header = f"{'':<21}{'deterministic':<20}{'--ai':<20}"
    lines.append(header)
    for metric_key, metric_label in (
        ("files_ok", "files_ok"),
        ("anchor_ok", "anchor_ok"),
        ("recall_at_3", "prefilter_recall@3"),
    ):
        det_cell = _format_totals_cell(
            current["totals"]["det"][metric_key],
            baseline["totals"]["det"][metric_key] if baseline else None,
        )
        ai_cell = _format_totals_cell(
            current["totals"]["ai"][metric_key],
            baseline["totals"]["ai"][metric_key] if baseline else None,
        )
        lines.append(f"  {metric_label:<19}{det_cell:<20}{ai_cell:<20}")
    lines.append("")

    lines.append("Per-scenario (files_ok / anchor_ok / recall@3):")
    for sid, entry in current["scenarios"].items():
        det_row = _format_scenario_row(entry["det"])
        ai_row = _format_scenario_row(entry["ai"])
        lines.append(f"  {sid:<26}det {det_row}   ai {ai_row}")
    lines.append("")

    if diff["regressions"]:
        lines.append(f"Regressions: {len(diff['regressions'])}")
        for r in diff["regressions"]:
            lines.append(
                f"  - {r['scenario']} [{r['mode']}] {r['metric']}: "
                f"{r['was']} -> {r['now']}"
            )
    else:
        lines.append("Regressions: none")

    if diff["improvements"]:
        lines.append(f"Improvements: {len(diff['improvements'])}")
        for i in diff["improvements"]:
            lines.append(
                f"  + {i['scenario']} [{i['mode']}] {i['metric']}: "
                f"{i['was']} -> {i['now']}"
            )
    else:
        lines.append("Improvements: none")

    return "\n".join(lines)


def _format_totals_cell(current_str: str, baseline_str: str | None) -> str:
    """Render 'N/M' with a (=/+k/-k) delta marker vs baseline."""
    if baseline_str is None:
        return f"{current_str}"
    cur_num = int(current_str.split("/")[0])
    base_num = int(baseline_str.split("/")[0])
    delta = cur_num - base_num
    if delta == 0:
        marker = "(=)"
    elif delta > 0:
        marker = f"(+{delta})"
    else:
        marker = f"({delta})"
    return f"{current_str} {marker}"


def _format_scenario_row(entry: dict) -> str:
    """Render one scenario row as three checkmarks/crosses/dashes."""

    def glyph(v: bool | None) -> str:
        if v is True:
            return "✓"
        if v is False:
            return "✗"
        return "—"

    return (
        f"{glyph(entry['files_ok'])} "
        f"{glyph(entry['anchor_ok'])} "
        f"{glyph(entry['recall_at_3'])}"
    )


def _run_patch_accuracy(
    *, update_baseline: bool, as_json: bool
) -> int:
    """Execute the patch-accuracy bench. Returns desired process exit code."""
    import tempfile

    from vibelign.commands.bench_fixtures import prepare_patch_sandbox

    baseline = _load_patch_baseline()
    with tempfile.TemporaryDirectory() as tmp_str:
        sandbox = prepare_patch_sandbox(Path(tmp_str))
        current = _measure_patch_accuracy(sandbox)

    if update_baseline:
        _write_patch_baseline(current)
        baseline = _load_patch_baseline()

    diff = (
        _diff_against_baseline(current, baseline)
        if baseline is not None
        else {"regressions": [], "improvements": []}
    )

    if as_json:
        from vibelign.terminal_render import cli_print

        cli_print(
            json.dumps(
                {
                    "current": current,
                    "baseline": baseline,
                    "diff": diff,
                    "update_baseline": update_baseline,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        report = _format_patch_report(current, baseline, diff)
        from vibelign.terminal_render import cli_print

        cli_print(report)

    if update_baseline:
        return 0
    return 1 if diff["regressions"] else 0


# === ANCHOR: VIB_BENCH_PATCH_RUNNER_END ===
```

- [ ] **Step 2: Wire `run_vib_bench` to dispatch `--patch`**

Find `def run_vib_bench(args: object) -> None:` (around line 499). Near the top of the function body, **before** the existing `do_generate = getattr(args, "generate", False)` line, add:

```python
    do_patch = getattr(args, "patch", False)
    update_baseline = getattr(args, "update_baseline", False)
    as_json_flag = getattr(args, "json", False)

    if do_patch:
        exit_code = _run_patch_accuracy(
            update_baseline=update_baseline, as_json=as_json_flag
        )
        raise SystemExit(exit_code)
```

This short-circuits before the existing A/B anchor-effect path runs. The existing `--generate` / `--score` / `--report` flow is untouched.

- [ ] **Step 3: Smoke-test the wiring inline**

Run:

```bash
uv run python -c "
from pathlib import Path
import tempfile
from unittest.mock import patch as mock_patch
from vibelign.commands.vib_bench_cmd import _run_patch_accuracy
with mock_patch('vibelign.core.patch_suggester._ai_select_file', return_value=None):
    code = _run_patch_accuracy(update_baseline=False, as_json=False)
print('exit:', code)
"
```

Expected: a report is printed (totals + per-scenario rows + 'Regressions: ...' line) and `exit: 0` (if baseline matches) or `exit: 1` (if Task 3's baseline values don't match actual measurement yet — this is expected and will be reconciled in Task 7).

If this command prints a traceback, the wiring is broken; fix before continuing.

- [ ] **Step 4: Commit**

```bash
git add vibelign/commands/vib_bench_cmd.py
git commit -m "$(cat <<'EOF'
feat(bench): --patch runner entry point and report formatter

_run_patch_accuracy wires measurement + baseline diff into a single
function with exit-code semantics (regression -> 1, clean -> 0,
--update-baseline always -> 0). run_vib_bench dispatches on args.patch
before the existing A/B anchor-effect flow. Report format matches the
spec (§7): totals grid with deltas + per-scenario glyph rows.
EOF
)"
```

---

## Task 5: Register `--patch` and `--update-baseline` flags

**Files:**
- Modify: `vibelign/cli/cli_command_groups.py:510-535`

- [ ] **Step 1: Add the new flags to the bench subparser**

Open `vibelign/cli/cli_command_groups.py`. Find the `bench` subparser block (around line 510-535). Modify the description, epilog, and add two new `add_argument` calls.

Replace:

```python
    p = sub.add_parser(
        "bench",
        help="앵커 효과 검증 벤치마크",
        description=(
            "앵커가 AI 코드 수정 정확도를 높이는지 검증하는 벤치마크 도구예요.\n"
            "A(앵커 없음) vs B(앵커 있음) 조건으로 프롬프트를 생성하고,\n"
            "AI 수정 결과를 채점할 수 있어요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib bench --generate    A/B 프롬프트 생성\n"
            "  vib bench --score       AI 수정 결과 채점\n"
            "  vib bench --report      마크다운 리포트 생성"
        ),
    )
    _ = p.add_argument(
        "--generate", action="store_true", help="A/B 조건별 프롬프트 생성"
    )
    _ = p.add_argument("--score", action="store_true", help="AI 수정 결과 채점")
    _ = p.add_argument(
        "--report", action="store_true", help="마크다운 비교 리포트 생성"
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
```

With:

```python
    p = sub.add_parser(
        "bench",
        help="앵커 효과 검증 벤치마크",
        description=(
            "앵커가 AI 코드 수정 정확도를 높이는지 검증하는 벤치마크 도구예요.\n"
            "A(앵커 없음) vs B(앵커 있음) 조건으로 프롬프트를 생성하고,\n"
            "AI 수정 결과를 채점할 수 있어요. --patch 옵션은 별도의\n"
            "patch-suggester 정확도 회귀 테스트 (pinned-intent)를 돌려요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib bench --generate           A/B 프롬프트 생성\n"
            "  vib bench --score              AI 수정 결과 채점\n"
            "  vib bench --report             마크다운 리포트 생성\n"
            "  vib bench --patch              patch-suggester 정확도 측정\n"
            "  vib bench --patch --update-baseline  baseline 갱신"
        ),
    )
    _ = p.add_argument(
        "--generate", action="store_true", help="A/B 조건별 프롬프트 생성"
    )
    _ = p.add_argument("--score", action="store_true", help="AI 수정 결과 채점")
    _ = p.add_argument(
        "--report", action="store_true", help="마크다운 비교 리포트 생성"
    )
    _ = p.add_argument(
        "--patch",
        action="store_true",
        help="patch-suggester 정확도 회귀 측정 (pinned-intent sandbox)",
    )
    _ = p.add_argument(
        "--update-baseline",
        action="store_true",
        help="--patch 와 함께 사용, 현재 측정값으로 baseline 파일 덮어쓰기",
    )
    _ = p.add_argument("--json", action="store_true", help="JSON으로 출력")
```

- [ ] **Step 2: Verify argparse sees the new flags**

Run: `uv run python -m vibelign bench --help`
Expected: Output includes both `--patch` and `--update-baseline` lines. If the `vibelign` package isn't directly runnable as a module, run instead: `uv run python -c "from vibelign.cli.vib_cli import main; import sys; sys.argv=['vib','bench','--help']; main()"` — should display the same help text.

- [ ] **Step 3: Commit**

```bash
git add vibelign/cli/cli_command_groups.py
git commit -m "$(cat <<'EOF'
feat(cli): register --patch and --update-baseline on vib bench

Flags wire directly to _run_patch_accuracy via run_vib_bench's dispatch.
Existing --generate / --score / --report flow is untouched.
EOF
)"
```

---

## Task 6: Exit-code integration test

**Files:**
- Modify: `tests/test_bench_patch_command.py` (add one more test class)

- [ ] **Step 1: Write a failing test for exit-code semantics**

Append to `tests/test_bench_patch_command.py`:

```python
class ExitCodeTest(unittest.TestCase):
    """End-to-end (in-process) exit-code semantics for _run_patch_accuracy."""

    @classmethod
    def setUpClass(cls) -> None:
        # Ensure baseline exists for the clean-run test.
        from vibelign.commands.vib_bench_cmd import PATCH_BASELINE_PATH

        cls.baseline_path = PATCH_BASELINE_PATH
        cls._backup = (
            PATCH_BASELINE_PATH.read_text(encoding="utf-8")
            if PATCH_BASELINE_PATH.exists()
            else None
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._backup is not None:
            cls.baseline_path.write_text(cls._backup, encoding="utf-8")

    def test_clean_run_exits_zero(self):
        from vibelign.commands.vib_bench_cmd import _run_patch_accuracy

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            # First run with --update-baseline to establish a matching baseline.
            code_update = _run_patch_accuracy(
                update_baseline=True, as_json=True
            )
            # Second run without --update-baseline should be clean.
            code_clean = _run_patch_accuracy(
                update_baseline=False, as_json=True
            )

        self.assertEqual(code_update, 0)
        self.assertEqual(code_clean, 0)

    def test_regression_exits_one(self):
        from vibelign.commands.vib_bench_cmd import (
            PATCH_BASELINE_PATH,
            _run_patch_accuracy,
        )

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            return_value=None,
        ):
            # Seed a known-good baseline.
            _ = _run_patch_accuracy(update_baseline=True, as_json=True)
            # Corrupt the baseline: force every metric to True so every
            # failing scenario becomes a regression.
            poisoned = json.loads(
                PATCH_BASELINE_PATH.read_text(encoding="utf-8")
            )
            for sid in poisoned["scenarios"]:
                for mode in ("det", "ai"):
                    for metric in ("files_ok", "anchor_ok", "recall_at_3"):
                        if poisoned["scenarios"][sid][mode][metric] is not None:
                            poisoned["scenarios"][sid][mode][metric] = True
            PATCH_BASELINE_PATH.write_text(
                json.dumps(poisoned, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            code = _run_patch_accuracy(update_baseline=False, as_json=True)

        self.assertEqual(code, 1)
```

- [ ] **Step 2: Run to verify it passes**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py::ExitCodeTest -v`
Expected: PASS. The baseline file is backed up before tests and restored after, so repo state stays clean.

**Important:** This test temporarily writes to the real `tests/benchmark/patch_accuracy_baseline.json`. If tests crash mid-run, the restored copy may not happen. Before committing this task, run `git diff tests/benchmark/patch_accuracy_baseline.json` — if there's a diff, the teardown failed and you need to revert manually.

- [ ] **Step 3: Run the full test file**

Run: `uv run --with pytest python -m pytest tests/test_bench_patch_command.py -v`
Expected: All test classes PASS (`MetricHelpersTest`, `MeasureAndDiffTest`, `BaselineDiffTest`, `ExitCodeTest`).

- [ ] **Step 4: Commit**

```bash
git add tests/test_bench_patch_command.py
git commit -m "$(cat <<'EOF'
test(bench): exit-code semantics for vib bench --patch

Seed baseline via --update-baseline, then confirm clean re-run exits 0.
Poison the baseline to force every non-null metric to True; confirm the
resulting run exits 1 with regressions reported. Baseline file is backed
up + restored around the test to keep repo state clean.
EOF
)"
```

---

## Task 7: Reconcile baseline with real measurement

**Files:**
- Modify (maybe): `tests/benchmark/patch_accuracy_baseline.json`

- [ ] **Step 1: Reinstall the local `vib` CLI so the new command is live**

Run: `uv tool install --reinstall --force .`
Expected: `Installed 1 executable: vib`. This is required because `vib` is installed in an isolated `uv`-managed environment at `~/.local/share/uv/tools/vibelign/`; local repo changes don't reach it until reinstall.

- [ ] **Step 2: Run the bench without `--update-baseline` and capture the diff**

Run: `vib bench --patch`
Expected outcomes:
- **Exit 0 and "Regressions: none"** → Task 3's baseline values were already correct, proceed to Step 4.
- **Exit 1 with a list of regressions/improvements** → Task 3's baseline values were provisional. Read the diff carefully. If every listed change is consistent with "this is the actual post-C6 state we agreed to commit," go to Step 3 to accept them.

**Red flag:** if the diff includes a regression on `change_error_msg`, `fix_login_lock_bug`, or `add_bio_length_limit` (the 3 scenarios that passed in C1+C6), something is broken in the measurement path. Stop and investigate before continuing.

- [ ] **Step 3: Update the baseline with real values**

Run: `vib bench --patch --update-baseline`
Expected: exit 0, and `git diff tests/benchmark/patch_accuracy_baseline.json` now shows only adjustments to `recall_at_3` / `add_password_change` (the fields Task 3 marked as provisional).

Inspect the diff. If any `files_ok` or `anchor_ok` value for a scenario you expect to pass flipped to `false`, **stop and investigate** — the runner may be measuring the wrong thing.

- [ ] **Step 4: Second run to confirm stability**

Run: `vib bench --patch`
Expected: exit 0, "Regressions: none", "Improvements: none" — proves the measurement is deterministic across back-to-back runs.

- [ ] **Step 5: Commit the final baseline (if step 3 modified it)**

```bash
git add tests/benchmark/patch_accuracy_baseline.json
git commit -m "$(cat <<'EOF'
feat(bench): initial patch accuracy baseline

Snapshot of post-C1 + post-C6 patch accuracy state under pinned-intent
sandbox. Update manually via `vib bench --patch --update-baseline` after
intended patch-suggester changes.
EOF
)"
```

If Step 3 did not modify the file (Task 3's values were already correct), there is nothing new to commit for this task — Task 3's baseline will be committed together with the runner code instead. Use `git add tests/benchmark/patch_accuracy_baseline.json` and commit only if `git status` shows it as untracked; otherwise skip.

---

## Task 8: Acceptance — spec requirements + commit uncommitted baseline

**Files:**
- None to modify (verification only)
- Commit: `tests/benchmark/patch_accuracy_baseline.json` if not yet tracked

- [ ] **Step 1: Confirm the baseline file is committed**

Run: `git ls-files tests/benchmark/patch_accuracy_baseline.json`
Expected: the path is printed (meaning it's tracked). If blank, run:

```bash
git add tests/benchmark/patch_accuracy_baseline.json
git commit -m "$(cat <<'EOF'
feat(bench): add patch_accuracy_baseline.json

Tracked baseline file for `vib bench --patch`. Current state reflects
post-C1 + post-C6 measurements (det 3/5·3/4·4/5, ai 3/5·3/4·4/5 under
pinned-intent sandbox).
EOF
)"
```

- [ ] **Step 2: Reproduce the spec success criteria (§11.1)**

Run: `vib bench --patch`
Expected: report showing `det` and `ai` totals matching the committed baseline, `Regressions: none`, exit 0.

Paste the totals line (or a screenshot) into the subagent/executor report so the reviewer can cross-check against the spec's stated values (det 3/5·3/4·4/5, ai 3/5·3/4·4/5).

- [ ] **Step 3: Reproduce spec success criteria §11.2 (determinism)**

Run: `vib bench --patch && vib bench --patch`
Expected: two back-to-back reports with identical totals, "Regressions: none" both times, exit 0 both times.

- [ ] **Step 4: Reproduce spec success criteria §11.3 (regression detection)**

Temporarily corrupt the baseline to force a regression, run the bench, revert.

```bash
cp tests/benchmark/patch_accuracy_baseline.json /tmp/patch_baseline_backup.json
python -c "
import json
from pathlib import Path
p = Path('tests/benchmark/patch_accuracy_baseline.json')
data = json.loads(p.read_text())
for sid in data['scenarios']:
    for mode in ('det', 'ai'):
        for metric in ('files_ok', 'anchor_ok', 'recall_at_3'):
            if data['scenarios'][sid][mode][metric] is not None:
                data['scenarios'][sid][mode][metric] = True
p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
"
vib bench --patch
echo "Exit code: $?"
cp /tmp/patch_baseline_backup.json tests/benchmark/patch_accuracy_baseline.json
rm /tmp/patch_baseline_backup.json
```

Expected: the `vib bench --patch` line shows several regressions, "Exit code: 1", and after the `cp` revert the file is back to the committed state (confirm with `git diff tests/benchmark/patch_accuracy_baseline.json` → no diff).

- [ ] **Step 5: Run the full automated test suite once more**

Run:
```bash
uv run --with pytest python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_patch_suggester_score_candidates.py tests/test_bench_patch_command.py -v
```
Expected: all tests PASS.

- [ ] **Step 6: Sanity-check the repo state**

Run:
```bash
git status
git log --oneline -15
```
Expected:
- Working tree clean (or only documentation-related changes).
- Recent commits in order: refactor(patch-suggester) → refactor(bench) fixtures → feat(bench) metrics → feat(bench) measurement → feat(bench) runner → feat(cli) flags → test(bench) exit-code → feat(bench) baseline.
- No leftover debug prints, temporary files, or uncommitted changes.

- [ ] **Step 7: Update memory file with C5 completion**

Edit `/Users/topsphinx/.claude/projects/-Users-topsphinx-YesonENT-Dropbox-top-sphinx-Mac-Documents-coding-VibeLign/memory/project_patch_accuracy_c1_done.md`.

Append a new section at the top:

```markdown
**C5 (bench runner) 완료 (2026-04-12):**
- `vib bench --patch` / `--update-baseline` 출시
- Baseline: `tests/benchmark/patch_accuracy_baseline.json` (수동 갱신)
- Pinned-intent canonical fixture: `vibelign/commands/bench_fixtures.py`
- Public API: `vibelign.core.patch_suggester.score_candidates`
- 회귀 가드: `tests/test_bench_patch_command.py` (mocked `_ai_select_file`)
- 다음 단계: C2 (F2 layer routing) 또는 C4 (F4 multi-fanout)
```

Also update the "다음 단계 후보" section to reflect that C5 is done.

---

## Self-review notes

After writing this plan, I checked it against the spec:

- **Spec §2 (측정 원칙):** Task 2 creates `bench_fixtures.prepare_patch_sandbox`; Task 4b uses it directly. Pinned-intent path is the only measurement path. ✓
- **Spec §3 (메트릭):** Task 4a implements all 3 metrics as pure functions, unit-tested in isolation. ✓
- **Spec §4 (새 API):** Task 1 extracts `score_candidates`. Behavior-preserving via `test_top1_matches_suggest_patch_target_file` assertion across all 5 scenarios. ✓
- **Spec §5 (baseline):** Task 3 creates the initial file, Task 4b implements load/diff/write, Task 7 reconciles provisional values with real measurement. ✓
- **Spec §6 (CLI):** Task 5 adds both flags. Task 4c's `_run_patch_accuracy` honors exit-code rules (regression → 1, `--update-baseline` → always 0). ✓
- **Spec §7 (리포트):** Task 4c implements `_format_patch_report` with totals grid + per-scenario glyph rows. ✓
- **Spec §8 (파일별 변경):** All 6 files in the spec table are touched by the plan, plus two test files. ✓
- **Spec §9 (테스트):** Unit test for `score_candidates` (Task 1). Metric helper tests (Task 4a). Measurement + baseline-diff tests (Task 4b). Exit-code tests (Task 6). **Deviation from spec §9.2:** the "E2E" test is in-process with mocked `_ai_select_file` rather than subprocess. Rationale explained at the top of this plan under "File Structure."
- **Spec §11 (성공 기준):** All 4 criteria are reproduced as Task 8 steps.
- **Spec §10 (스코프 제외):** No task touches history, multi-sandbox, provider switching, flaky detection, or CI integration. ✓

Type consistency check: `_measure_patch_accuracy` returns `dict` with `"scenarios"` and `"totals"` keys. `_diff_against_baseline(current, baseline)` takes dicts of the same shape. `_run_patch_accuracy` passes them consistently. Metric function names (`_compute_files_ok`, `_compute_anchor_ok`, `_compute_recall_at_3`) are used identically in the implementation and the tests. ✓

Placeholder scan: no "TBD" / "handle edge cases" / "similar to task N" patterns found. Every code block is complete.
