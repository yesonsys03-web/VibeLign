# F2 CLI Refactor Code Review

Verdict: PASS
codeQualityStatus: WATCH
recommendation: APPROVE
reportPath: .omo/evidence/f2-cli-refactor-code-review.md
blockers: none

## Scope

Reviewed the requested F2 CLI command group refactor only:

- vibelign/cli/cli_command_groups.py
- vibelign/cli/cli_report_command_groups.py
- vibelign/cli/cli_workflow_command_groups.py

The working tree contains broad unrelated report-writing changes. This review does not approve those broader changes.

Notepad path: not provided in the review prompt.

## Skill-Perspective Check

Ran the required skill-perspective check before judging maintainability and tests:

- remove-ai-slops: consulted. No deletion-only tests, tautological tests, implementation-constant-only tests, needless data extraction, or refactor-specific production slop found in the reviewed CLI split.
- programming: consulted, including the Python reference and code-smells reference. No new `Any`, `type: ignore`, broad exception handling, or avoidable runtime circular import found in the reviewed files.

Perspective residual: strict programming/remove-ai-slops file-size guidance still dislikes `vibelign/cli/cli_command_groups.py` at 627 physical lines / 581 pure LOC. I am classifying this as a MEDIUM residual, not an F2 blocker, because the explicit F2 gate is physical lines `<650`, the file is now wiring-only for the remaining command groups, and the new extracted modules are below 250 pure LOC.

## Findings By Severity

### CRITICAL

None.

### HIGH

None.

### MEDIUM

- vibelign/cli/cli_command_groups.py:1 remains above the strict 250 pure-LOC programming/remove-ai-slops ceiling: 627 physical lines and 581 pure LOC. This is still maintenance pressure, but it no longer violates the F2 exact `<650` gate that blocked the prior done claim.

### LOW

None.

## Review Checks

Behavior preserved:

- Current parser contains 42 top-level commands and 42 unique command names.
- Moved command order in the live parser is preserved for the extracted groups:
  - `plan` index 33
  - `report` index 34
  - `report-stamp-pdf` index 35
  - `transfer` index 36
  - `watch` index 37
  - `bench` index 38
  - `manual` index 39
  - `rules` index 40
  - `completion` remains after them
- Static command target review:
  - `plan` -> `vibelign.commands.vib_plan_cmd.run_vib_plan`
  - `report` -> `vibelign.commands.vib_report_cmd.run_vib_report`
  - `report-stamp-pdf` -> `vibelign.commands.vib_report_stamp_cmd.run_vib_report_stamp`
  - `transfer` -> `vibelign.commands.vib_transfer_cmd.run_transfer`
  - `watch` -> `vibelign.commands.watch_cmd.run_watch_cmd`
  - `bench` -> `vibelign.commands.vib_bench_cmd.run_vib_bench`
  - `manual` -> `_run_vib_manual`
  - `rules` -> `_run_vib_rules`
- `manual` wrapper check passed with an in-memory monkeypatch: parsed `manual checkpoint --json` called `run_vib_manual` with `command_name='checkpoint'`, `all=False`, `save=False`, `json=True`.
- `rules` wrapper check passed with an in-memory monkeypatch: parsed `rules` called `run_vib_manual` with `command_name='rules'`, `save=False`, `all=False`, `json=False`.

Type/import quality:

- `vibelign/cli/cli_report_command_groups.py` and `vibelign/cli/cli_workflow_command_groups.py` import `SubparserFactory` only under `TYPE_CHECKING`, with postponed annotations enabled. This avoids a runtime circular import while preserving annotation intent.
- No `Any`, `type: ignore`, `pyright: ignore`, broad `except Exception`, or broad `except BaseException` found in the three reviewed files.
- `object` and `cast` use is limited to the existing lazy-wrapper pattern and did not expand beyond the moved manual/rules wrapper behavior.

Anchors:

- `vibelign/cli/cli_command_groups.py` has balanced anchors, including `CLI_COMMAND_GROUPS`, `CLI_COMMAND_GROUPS_SUBPARSERFACTORY`, `CLI_COMMAND_GROUPS_ADD_PARSER`, `CLI_COMMAND_GROUPS__RUN_VIB_MCP`, `CLI_COMMAND_GROUPS_REGISTER_EXTENDED_COMMANDS`, and `CLI_COMMAND_GROUPS__RECOVER_COMMAND`.
- `vibelign/cli/cli_report_command_groups.py` has balanced anchors: `CLI_REPORT_COMMAND_GROUPS` and `CLI_REPORT_COMMAND_GROUPS_REGISTER_REPORT_COMMAND_GROUP`.
- `vibelign/cli/cli_workflow_command_groups.py` has balanced anchors: `CLI_WORKFLOW_COMMAND_GROUPS`, `CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_MANUAL`, `CLI_WORKFLOW_COMMAND_GROUPS__RUN_VIB_RULES`, and `CLI_WORKFLOW_COMMAND_GROUPS_REGISTER_WORKFLOW_COMMAND_GROUP`.
- `.vibelign/project_map.json` includes the two new production files and their anchor spans.

F2 exact gate:

- Re-ran the exact F2 logic without redirecting over the artifact: `APPROVE code quality scope`.
- Existing artifact `.omo/evidence/report-writing-quality/f2-code-quality-scope.txt` contains `APPROVE code quality scope`.
- `vibelign/cli/cli_command_groups.py` is 627 physical lines, under the explicit F2 `<650` threshold.

Focused tests and compile evidence:

- Read `.omo/evidence/report-writing-quality/f2-cli-refactor-tests.txt`: 21 focused CLI/report tests passed.
- Re-ran the focused suite: `uv run pytest tests/cli/test_vib_report_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/cli/test_vib_report_assist_cmd.py tests/cli/test_vib_report_format_parity.py -q` -> 21 passed in 0.27s.
- Read `.omo/evidence/report-writing-quality/f2-cli-refactor-compileall.txt`: compileall listed `vibelign/cli` and `vibelign/commands`.
- Re-ran `python3 -m compileall -q vibelign/cli vibelign/commands` -> exit 0.
- Re-ran `git diff --check -- vibelign/cli/cli_command_groups.py vibelign/cli` -> exit 0.

No unrelated help/default/choices drift:

- Within the refactor scope, the moved command definitions remain in extracted modules with their command names, lazy targets, defaults, choices, and wrapper behavior intact.
- `git diff HEAD` is not a clean refactor-only comparator because the branch already contains earlier report-feature CLI changes; I did not treat those broader changes as F2 refactor drift.

## Residual Risks / Test Gaps

- There is no committed focused regression test specifically for `manual` and `rules` wrapper dispatch after the move. I verified those wrappers with a read-only in-memory monkeypatch instead.
- `vib guard` evidence still exits 1 because of broad dirty worktree state and an unrelated missing-anchor production file outside this CLI refactor. That is not an F2 CLI refactor blocker.
- `vibelign/cli/cli_command_groups.py` remains above the stricter 250 pure-LOC ideal, so future command additions should continue extracting cohesive groups rather than expanding this file.
