# Render Payload Key Fix - Done Claim

Completed: 2026-06-20T22:00:00+09:00

## Changed Files

- `vibelign/commands/vib_report_render_payload.py`
  - Added payload `key` parsing and comparison against the current `--polish-key`.
  - Rejects missing, empty, or mismatched keys before returning env payload models.
- `vibelign/commands/vib_report_runtime.py`
  - Reads `raw.polish_key` before loading env payload models and passes it into the loader.
  - Keeps the existing cache fallback and missing-key cache error path when no env payload is present.
- `tests/cli/test_vib_report_render_payload.py`
  - Renamed the existing positive payload test to make the matching-key contract explicit.
  - Added parameterized regression coverage for missing `--polish-key` and mismatched `--polish-key`.
- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-*.txt|md`
  - Captured hypotheses, red/green tests, CLI QA, lint, diff check, and LOC evidence.

## Root Cause

`_render_payload_models()` loaded and returned `VIBELIGN_REPORT_RENDER_PAYLOAD_PATH` content before reading `raw.polish_key`. The loader validated only `ok`, `base`, and `polished`, so a stale GUI payload could render a different plan even when the caller supplied no key or the wrong key.

## Red Evidence

Scenario: stale alpha env payload used while rendering beta with missing or stale `--polish-key`.

Invocation:

```bash
uv run python -m pytest tests/cli/test_vib_report_render_payload.py::test_render_decisions_payload_file_rejects_missing_or_mismatched_key -v
```

Binary observable:

- 2 failures before the fix.
- Both failures were `Failed: DID NOT RAISE <class 'SystemExit'>`.
- Captured stdout showed `{"ok": true, "path": ".../결제-앱-work.html", "report_type": "work"}`.

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-red.txt`

## Green Evidence

Focused regression:

```bash
uv run python -m pytest tests/cli/test_vib_report_render_payload.py::test_render_decisions_payload_file_rejects_missing_or_mismatched_key -v
```

Observable: `2 passed in 0.16s`

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-green-focused.txt`

Full focused CLI report render-payload test file:

```bash
uv run python -m pytest tests/cli/test_vib_report_render_payload.py -v
```

Observable: `19 passed in 0.16s`

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-pytest-full.txt`

Matching-key preservation:

- Scenario: `test_render_decisions_payload_file_matching_key_writes_draft_content`
- Invocation: included in the full focused pytest command above.
- Observable: test passed and still found the draft marker in rendered HTML.

## Manual CLI QA

Scenario: actual `uv run vib report` emitted an alpha payload, then attempted beta render with that env payload and `--polish-key stale-key`.

Invocation: Python harness invoking the real CLI commands:

```bash
uv run python - <<'PY'
# creates temp alpha/beta plans, runs `uv run vib report ... --emit-model`,
# mutates payload with an alpha marker, then runs beta render with stale key
PY
```

Observable:

- `CLI status: 1`
- `CLI stdout: {"ok": false, "error": "render payload 형식이 잘못됐어요: payload.key does not match polish-key"}`
- `Rendered html count: 0`
- `Marker rendered: False`

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-cli-qa.txt`

## Quality Gates

Ruff:

```bash
uv run ruff check vibelign/commands/vib_report_runtime.py vibelign/commands/vib_report_render_payload.py tests/cli/test_vib_report_render_payload.py
```

Observable: `All checks passed!`

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-ruff.txt`

Diff whitespace:

```bash
git diff --check -- vibelign/commands/vib_report_runtime.py vibelign/commands/vib_report_render_payload.py tests/cli/test_vib_report_render_payload.py .omo/evidence/report-writing-quality/global-review-render-payload-key-fix-hypotheses.md
```

Observable: `PASS: git diff --check found no whitespace errors for touched files and final evidence.`

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-diff-check.txt`

Untracked-file whitespace check:

```bash
git diff --no-index --check -- /dev/null <touched untracked file>
```

Observable: all touched untracked code/test/evidence files reported `PASS no whitespace errors`.

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-noindex-diff-check.txt`

Targeted final status:

- `.debug-journal.md` and `.git/info/exclude` are clean after cleanup.
- The three code/test files remain untracked because they were already untracked in the shared worktree.

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-status.txt`

LOC:

- `vibelign/commands/vib_report_runtime.py`: 160 pure LOC
- `vibelign/commands/vib_report_render_payload.py`: 55 pure LOC
- `tests/cli/test_vib_report_render_payload.py`: 270 pure LOC

Artifact:

- `.omo/evidence/report-writing-quality/global-review-render-payload-key-fix-loc.txt`

## VibeLign Safe-Mode Evidence

- `project_map_get`: ran.
- `anchor_read_content`: ran for `VIB_REPORT_RUNTIME_RENDER` and `VIB_REPORT_RENDER_PAYLOAD`.
- Pre-edit checkpoint: `20260620125400132301Z`
- Post-fix checkpoint: `20260620130001673622Z`
- `guard_check`: ran with `since_minutes=60`, `strict=false`.

Guard residual:

- Status: `fail`, verdict `stop`.
- Reason is the accepted broad dirty-tree/missing-anchor residual: high-risk multi-file production edit and missing anchor in `vibelign/core/reporting_cli/report_visual_cards.py`.
- This was not treated as a blocker because the caller explicitly accepted missing-anchor/guard residuals for this lane.

## Residuals

- The worktree was already broadly dirty before this patch; the three code/test files touched here were already untracked.
- `tests/cli/test_vib_report_render_payload.py` is now 270 pure LOC. I kept the required regression in the named focused file to satisfy the requested verification command instead of introducing another test module.
- I did not run broad suites or commit.
