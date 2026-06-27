# report-writing-quality basedpyright focused fix doneclaim

## Changed files

- `vibelign/commands/vib_report_context.py`
  - Tightened `ReportFailure.__call__` from `None` to `NoReturn`, matching the runtime `_fail(...)` implementation that raises `SystemExit`.
  - This lets basedpyright understand that `fail(...)` does not return after missing plan, read failure, invalid font sizes/fonts, or model build failure.
- `vibelign/core/reporting_cli/model_json.py`
  - Replaced raw `dict` / `object` JSON boundary annotations with `JsonScalar`, `JsonValue`, and `JsonObject` aliases.
  - Kept validation at the JSON boundary and returned typed `ReportModel` dataclasses without `Any`, `cast`, or public `object` annotations.
- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`
  - Evidence record for this focused fix.

## Verification

Scenario: focused basedpyright blockers for report context and model JSON.

Invocation:

```bash
uv run basedpyright vibelign/commands/vib_report_context.py vibelign/core/reporting_cli/model_json.py
```

Observable:

- Before fix: exit 1 with 9 errors and 18 warnings.
- After fix: exit 0 with `0 errors, 0 warnings, 0 notes`.

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

Scenario: focused report model JSON, render payload, and report command regressions.

Invocation:

```bash
uv run pytest tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_cmd.py
```

Observable:

- Exit 0.
- `50 passed in 0.28s`.

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

Scenario: ruff on touched Python files.

Invocation:

```bash
uv run ruff check vibelign/commands/vib_report_context.py vibelign/core/reporting_cli/model_json.py
```

Observable:

- Exit 0.
- `All checks passed!`

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

Scenario: whitespace check for touched tracked diff.

Invocation:

```bash
git diff --check -- vibelign/commands/vib_report_context.py vibelign/core/reporting_cli/model_json.py
```

Observable:

- Exit 0.
- No output.
- Note: `vibelign/commands/vib_report_context.py` is currently untracked in the shared worktree, so normal `git diff --check -- <paths>` only reports tracked diff content.

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

Scenario: whitespace check for touched untracked file.

Invocation:

```bash
git diff --check --no-index /dev/null vibelign/commands/vib_report_context.py
```

Observable:

- Exit 1 because `/dev/null` and the untracked file differ.
- No whitespace-warning output.

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

Scenario: programming skill no-excuse helper.

Invocation:

```bash
uv run scripts/python/check-no-excuse-rules.py vibelign/commands/vib_report_context.py vibelign/core/reporting_cli/model_json.py
```

Observable:

- Exit 2.
- `scripts/python/check-no-excuse-rules.py` does not exist in this repo.
- Manual pure LOC check was run instead:
  - `vibelign/commands/vib_report_context.py:148`
  - `vibelign/core/reporting_cli/model_json.py:82`

Artifact path:

- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

## VibeLign fallback checks

Scenario: VibeLign safe-mode CLI fallback, because MCP tools were not available in this session.

Invocations:

```bash
vib doctor --strict
vib scan
vib explain --write-report
vib guard --strict --write-report
```

Observables:

- `vib doctor --strict`: exit 1, project remains High Risk with broad pre-existing structure/anchor residuals.
- `vib scan`: exit 0, project map regenerated; reports 2 anchor integrity issues for unreadable `__init__.py` files.
- `vib explain --write-report`: exit 0, wrote `.vibelign/reports/explain_latest.md`.
- `vib guard --strict --write-report`: exit 1, wrote `.vibelign/reports/guard_latest.md`; stop reasons are accepted residuals from broad worktree state, including `planning_required` and missing anchor on `vibelign/core/reporting_cli/report_visual_cards.py`.

Artifact paths:

- `.vibelign/reports/explain_latest.md`
- `.vibelign/reports/guard_latest.md`
- `.omo/evidence/report-writing-quality/global-review-basedpyright-fix-doneclaim.md`

## Residuals

- User explicitly accepted missing-anchor/guard residuals; they are not treated as blockers for this focused basedpyright fix.
- The shared worktree already contains many unrelated modified and untracked files. I did not revert or stage them.
- `vibelign/commands/vib_report_context.py` is untracked in the shared worktree, but it is present in `.vibelign/project_map.json` and was one of the requested basedpyright targets.
