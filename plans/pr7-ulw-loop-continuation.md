# PR7 ULW Loop Continuation

> Archive status: Superseded by PR8 legacy removal on 2026-06-05.
>
> Do not execute the unchecked PR7 tasks as implementation work. This plan was written for a warning-only legacy-surface demotion that preserved `patch`, CodeSpeak, `plan-structure`, MCP patch tools, patch benchmarks, and internal patch modules. PR8 deliberately replaced that direction with hard removal and completed verification.
>
> Authoritative successor: `plans/pr8-legacy-removal.md`, `.omo/ulw-loop/pr8-legacy-removal/goals.json`, and `.omo/ulw-loop/evidence/pr8-final-quality-gate.json`.

## Archive Audit

This document is retained as historical PR7 planning context. The unchecked tasks below are not a live backlog after PR8.

| PR7 range | Archive disposition | PR8 replacement evidence |
|-----------|---------------------|--------------------------|
| Task 1 | Superseded. PR7 steering protected preservation-only scope; PR8 changed the product decision to removal. | `.omo/ulw-loop/pr8-legacy-removal/goals.json` G001/G002 complete. |
| Tasks 2-5 | Superseded. GUI, CLI, and docs work should not restore legacy discoverability or warning-only behavior. | G003/G004/G007 complete; `task-13-negative-smoke.txt`; `pr8-final-static-scan-classification.md`. |
| Task 6 | Invalid after PR8. Its preservation requirements conflict with the removed CodeSpeak, patch pipeline, MCP patch tools, and patch benchmark mode. | G005/G006 complete; `task-13-python-regression.txt`. |
| Tasks 7-8 | Superseded. Dependency classification and browser-visible QA were replaced by PR8 removal classification and preserved-workflow regressions. | G002/G007 complete; `pr8-final-gui-regression.txt`; `pr8-final-static-scan-classification.md`. |
| Task 9 and F1-F4 | Superseded by the PR8 final quality gate. | `pr8-final-quality-gate.json`: 21/21 criteria passed; commit `9aad567`. |

## TL;DR
> Summary:      Continue PR7 as a legacy-surface demotion, not an engine deletion. First steer the generated ulw-loop state away from excluded deletion goals, then finish the current GUI/help slice and verify CLI, docs, MCP, and browser-visible surfaces with captured evidence.
> Deliverables:
> - Superseded generated goals: `G013`-`G018`; annotated future-only goals: `G020`-`G021`
> - Finished GUI command/help legacy regression slice
> - Advanced/manual legacy discoverability with visible `legacy` badge
> - CLI/docs/MCP preservation evidence and PR7 browser QA artifacts
> Effort:       Medium
> Risk:         Medium - generated loop goals include deletion tasks that directly conflict with the PR7 spec.

## Scope
### Must have
- Steer `.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json` so excluded deletion goals are blocked/superseded before workers continue.
- Treat `plans/spec-pr7-legacy-surface-cleanup.md` as the source of truth: beginner-facing surfaces hide `patch`, `CodeSpeak`, and `plan-structure`; advanced/manual surfaces keep them findable with legacy wording.
- Finish the current uncommitted GUI/help work around `getPlanStructureCommand()`, `BEGINNER_COMMANDS`, `helpData`, and focused Vitest coverage.
- Verify current CLI legacy warning behavior and docs first-flow behavior before broadening work.
- Preserve MCP patch handlers, core patch/codespeak modules, benchmark fixtures, and `vib bench --patch` behavior.
- Capture agent-executed evidence under `.omo/ulw-loop/evidence/`.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not delete `vibelign/core/codespeak.py`, `vibelign/core/patch_suggester.py`, `vibelign/patch/`, MCP `patch_get`/`patch_apply`, benchmark fixtures, or `vib bench --patch`.
- Do not require `--legacy-confirm` in PR7; PR7 is warning-only and continues execution.
- Do not add broad navigation redesign, new product flows, or dependency additions unless a task's acceptance command proves the existing harness cannot capture evidence.
- Do not revert unrelated dirty files: `vibelign-gui/.omc/state/idle-notif-cooldown.json`, `vibelign-gui/src-tauri/.omc/state/last-tool-error.json`, and existing `.omo/ulw-loop/evidence/pr1-*`.
- Do not use VibeLign MCP safe-mode tooling unless the active user message explicitly contains the safe-mode keyword and the available tools support that workflow.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + tests-after where behavior already has committed tests; Vitest for GUI, pytest for Python CLI/docs/MCP, Chrome CDP browser QA for live GUI.
- QA policy: every task has agent-executed scenarios
- Evidence: `.omo/ulw-loop/evidence/task-<N>-<slug>.<ext>`

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (no dependencies):
- Task 1: steer generated PR7 goals to spec boundary; run this first before dispatching code workers
- Task 2: finish current GUI command/help legacy slice
- Task 3: harden advanced/manual legacy discoverability
- Task 4: lock CLI legacy help and execution notices
- Task 5: lock README/manual beginner-flow docs contract

Wave 2 (after Wave 1):
- Task 6: internal MCP/core/benchmark preservation checks; depends [1, 4]
- Task 7: dependency map classification evidence; depends [1, 2, 3, 4, 5, 6]
- Task 8: PR7 live browser QA evidence; depends [2, 3, 5]

Wave 3 (after Wave 2):
- Task 9: aggregate evidence, quality gates, and clean commits; depends [1, 2, 3, 4, 5, 6, 7, 8]

Critical path: Task 1 -> Task 2 -> Task 8 -> Task 9

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 6, 7, 9 | 2, 3, 4, 5 |
| 2    | none       | 7, 8, 9 | 1, 3, 4, 5 |
| 3    | none       | 7, 8, 9 | 1, 2, 4, 5 |
| 4    | none       | 6, 7, 9 | 1, 2, 3, 5 |
| 5    | none       | 7, 8, 9 | 1, 2, 3, 4 |
| 6    | 1, 4       | 7, 9    | 8 |
| 7    | 1, 2, 3, 4, 5, 6 | 9 | 8 |
| 8    | 2, 3, 5   | 9       | 6, 7 |
| 9    | 1, 2, 3, 4, 5, 6, 7, 8 | final verification | none |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Steer Generated PR7 Goals To Spec Boundary

  What to do: Use the ulw-loop steering command, not hand edits, to mark generated deletion goals `G013-vibelign-core-codespeak-py`, `G014-vibelign-core-patch-suggester-py`, `G015-vibelign-patch`, `G016-mcp-patch-get-patch-apply`, `G017-benchmark-test-fixture`, and `G018-vib-bench-patch` as `mark_blocked_superseded`. Add an audit note that `G020-legacy-confirm` and `G021-hidden-command` are future-release/final-state ideas outside PR7. Revise `G001` criteria if they still contain placeholder `Replace via revise_criterion` text.
  Must NOT do: Do not edit product source. Do not hand-edit `goals.json` or `ledger.jsonl`; write state through `omo ulw-loop steer`.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [6, 7, 9] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `/Users/usabatch/.codex/plugins/cache/sisyphuslabs/omo/0.1.0/skills/ulw-loop/SKILL.md:183` - dynamic steering kinds and command form
  - Pattern:  `.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json:432` - generated excluded deletion goals start here
  - Pattern:  `.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json:642` - PR7 warning-only goal appears after excluded deletion goals
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:46` - explicit exclusions
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:65` - PR7 decision: warning only, no `--legacy-confirm`
  - External: `https://v2.tauri.app/develop/calling-rust/` - confirms frontend/backend command surfaces should remain explicit, supporting preservation rather than silent deletion

  Acceptance criteria (agent-executable only):
  - [ ] Run `omo ulw-loop status --json > .omo/ulw-loop/evidence/task-1-pr7-goal-status.json` and confirm the audit trail contains `mark_blocked_superseded` for `G013` through `G018`.
  - [ ] Run `rg -n "\"G01[3-8].*삭제|G020|G021|mark_blocked_superseded|future-release|outside PR7" .omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7 .omo/ulw-loop/evidence > .omo/ulw-loop/evidence/task-1-pr7-goal-steering.txt` and confirm the output shows the superseded or annotated state.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: deletion goals are superseded
    Tool:     bash
    Steps:    omo ulw-loop steer --kind mark_blocked_superseded --goal-id G013-vibelign-core-codespeak-py --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting vibelign/core/codespeak.py" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop steer --kind mark_blocked_superseded --goal-id G014-vibelign-core-patch-suggester-py --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting vibelign/core/patch_suggester.py" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop steer --kind mark_blocked_superseded --goal-id G015-vibelign-patch --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting vibelign/patch/" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop steer --kind mark_blocked_superseded --goal-id G016-mcp-patch-get-patch-apply --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting MCP patch_get/patch_apply" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop steer --kind mark_blocked_superseded --goal-id G017-benchmark-test-fixture --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting benchmark/test fixtures" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop steer --kind mark_blocked_superseded --goal-id G018-vib-bench-patch --replacements '["G003-mcp","G004-deprecation","G012"]' --evidence "PR7 spec excludes deleting vib bench --patch" --rationale "PR7 demotes beginner surfaces only" --json
              omo ulw-loop status --json > .omo/ulw-loop/evidence/task-1-pr7-goal-status.json
    Expected: status/evidence shows G013-G018 are no longer ordinary pending implementation goals
    Evidence: .omo/ulw-loop/evidence/task-1-pr7-goal-status.json

  Scenario: future-only goals are annotated, not implemented
    Tool:     bash
    Steps:    omo ulw-loop steer --kind annotate_ledger --evidence "G020 and G021 are future-release/final-state ideas; PR7 remains warning-only per plans/spec-pr7-legacy-surface-cleanup.md" --rationale "Prevent executor from requiring --legacy-confirm or hiding/deleting commands in PR7" --json
              rg -n "G020|G021|future-release|warning-only|outside PR7" .omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7 .omo/ulw-loop/evidence > .omo/ulw-loop/evidence/task-1-pr7-future-goals.txt
    Expected: evidence text includes G020/G021 annotation and no source deletion occurs
    Evidence: .omo/ulw-loop/evidence/task-1-pr7-future-goals.txt
  ```

  Commit: NO | Message: `n/a` | Files: [.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json, .omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/ledger.jsonl]

- [ ] 2. Finish Current GUI Command And Help Legacy Slice

  What to do: Continue from the existing uncommitted GUI changes. Keep `getPlanStructureCommand()` in `commands.ts`, keep `PlanStructureCard` using that accessor, keep `PATCH_COMMAND` compatibility, and update `helpData` so the primary command overview omits `patch`/`plan-structure` while direct `patch` and `plan-structure` help answers say they are legacy and point to host AI / `vib plan` flows. Extend focused tests before changing source if any assertion is missing.
  Must NOT do: Do not remove command metadata. Do not make `patch` or `plan-structure` invisible to all users. Do not broaden this into Home navigation redesign.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 8, 9] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/lib/commands.ts:9` - `COMMANDS` default visibility merge and `BEGINNER_COMMANDS`
  - Pattern:  `vibelign-gui/src/lib/commands.ts:16` - safe patch accessor pattern
  - Pattern:  `vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx:1` - existing card should consume command metadata without non-null assertion
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:25` - fallback beginner help topics
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:147` - current direct `patch` help topic still needs legacy wording if not already updated
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:195` - current direct `plan-structure` help topic still needs legacy wording if not already updated
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:349` - alias matching allows direct legacy lookup
  - Test:     `vibelign-gui/src/lib/legacySurface.test.ts:5` - command visibility regression
  - Test:     `vibelign-gui/src/lib/helpData.test.ts:5` - primary help overview regression
  - External: `https://vitest.dev/guide/cli.html` - use file filters and `vitest run` for focused GUI tests

  Acceptance criteria (agent-executable only):
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts`
  - [ ] `cd vibelign-gui && npx tsc --noEmit`
  - [ ] `cd vibelign-gui && npm run lint`
  - [ ] `git diff -- vibelign-gui/src/lib/commands.ts vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx vibelign-gui/src/lib/helpData.ts vibelign-gui/src/lib/legacySurface.test.ts vibelign-gui/src/lib/helpData.test.ts > .omo/ulw-loop/evidence/task-2-gui-help-diff.patch`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: primary help omits legacy commands
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/lib/helpData.test.ts
    Expected: helpData test passes and asserts "vib start"/"guard" remain while "patch" and "plan-structure" are absent from the primary command overview
    Evidence: .omo/ulw-loop/evidence/task-2-help-primary.txt

  Scenario: command metadata keeps legacy entries accessible
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts
    Expected: test passes and asserts `getPatchCommand().visibility === "legacy"`, `getPlanStructureCommand().visibility === "legacy"`, and beginner list excludes both commands
    Evidence: .omo/ulw-loop/evidence/task-2-command-visibility.txt
  ```

  Commit: YES | Message: `test(gui): keep legacy commands out of beginner help` | Files: [vibelign-gui/src/lib/commands.ts, vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx, vibelign-gui/src/lib/helpData.ts, vibelign-gui/src/lib/legacySurface.test.ts, vibelign-gui/src/lib/helpData.test.ts]

- [ ] 3. Harden Advanced And Manual Legacy Discoverability

  What to do: Make advanced/manual legacy access explicit. Ensure `ManualCommandList` shows `legacy` badges for `patch` and `plan-structure`; ensure `ManualCommandDetail` preserves legacy wording; and if `GenericCommandCard` can render a legacy command, render the shared `LegacyCommandBadge` next to its title. Add tests that use user-facing queries.
  Must NOT do: Do not put `patch` back into `DEFAULT_CARD_ORDER` or beginner Home. Do not remove manual entries.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 8, 9] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/components/home/LegacyCommandBadge.tsx:5` - existing badge component
  - Pattern:  `vibelign-gui/src/components/home/ManualCommandList.tsx:24` - manual command cards render all commands
  - Pattern:  `vibelign-gui/src/components/home/ManualCommandList.tsx:44` - legacy badge already appears in list header row
  - Pattern:  `vibelign-gui/src/components/cards/GenericCommandCard.tsx:7` - command card type currently lacks explicit visibility
  - Pattern:  `vibelign-gui/src/components/cards/GenericCommandCard.tsx:116` - command card title/short row where badge belongs
  - Pattern:  `vibelign-gui/src/hooks/useCardOrder.ts:5` - beginner-safe advanced default order excludes `patch`
  - Test:     `vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx:12` - manual list render pattern
  - Test:     `vibelign-gui/src/components/home/__tests__/AdvancedHomeCards.test.tsx:15` - advanced card test pattern
  - External: `https://testing-library.com/docs/queries/about/` - prefer accessible role/name and user-visible text queries

  Acceptance criteria (agent-executable only):
  - [ ] `cd vibelign-gui && npm test -- --run src/components/home/__tests__/ManualCommandList.test.tsx src/components/home/__tests__/ManualCommandDetail.test.tsx src/components/home/__tests__/AdvancedHomeCards.test.tsx src/pages/__tests__/Home.simple.test.tsx`
  - [ ] `cd vibelign-gui && npm run lint`
  - [ ] `rg -n "patch|plan-structure" vibelign-gui/src/hooks/useCardOrder.ts` returns no default-card-order reintroduction.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: manual list marks legacy commands
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/components/home/__tests__/ManualCommandList.test.tsx
    Expected: focused test passes and includes an assertion that manual list renders `patch` and `plan-structure` with visible `legacy` badges
    Evidence: .omo/ulw-loop/evidence/task-3-manual-legacy-list.txt

  Scenario: beginner Home still hides legacy terms
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/pages/__tests__/Home.simple.test.tsx
    Expected: beginner Home test passes with `vib patch`, `CodeSpeak`, `plan-structure`, and `target_anchor` absent before advanced/manual navigation
    Evidence: .omo/ulw-loop/evidence/task-3-home-beginner-hidden.txt
  ```

  Commit: YES | Message: `feat(gui): label legacy commands in advanced surfaces` | Files: [vibelign-gui/src/components/home/LegacyCommandBadge.tsx, vibelign-gui/src/components/home/ManualCommandList.tsx, vibelign-gui/src/components/home/ManualCommandDetail.tsx, vibelign-gui/src/components/cards/GenericCommandCard.tsx, vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx, vibelign-gui/src/components/home/__tests__/ManualCommandDetail.test.tsx, vibelign-gui/src/components/home/__tests__/AdvancedHomeCards.test.tsx]

- [ ] 4. Lock CLI Legacy Help And Execution Notices

  What to do: Re-run and, if needed, patch CLI behavior so `vib --help` keeps `patch` and `plan-structure` out of beginner groups while retaining them in `고급 / legacy`, `vib patch ...` prints the PR7 legacy notice before continuing, and `vib plan-structure ...` prints its legacy notice before continuing. Keep JSON modes machine-readable if existing tests rely on that.
  Must NOT do: Do not remove CLI subcommands. Do not add `--legacy-confirm`. Do not alter unrelated command groups.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [6, 7, 9] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/cli/cli_base.py:79` - main help description groups
  - Pattern:  `vibelign/cli/cli_base.py:130` - current `고급 / legacy` group
  - Pattern:  `vibelign/commands/vib_patch_cmd.py:164` - `vib patch` legacy notice
  - Pattern:  `vibelign/commands/vib_plan_structure_cmd.py:39` - `vib plan-structure` execution flow and notice
  - Test:     `tests/cli/test_legacy_surface.py:14` - CLI PR7 regression tests
  - Test:     `tests/test_vib_cli_surface.py:33` - parser still includes legacy commands
  - External: `https://docs.python.org/3/library/argparse.html` - argparse help behavior if parser formatting changes are needed

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py`
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli --help > .omo/ulw-loop/evidence/task-4-vib-help.txt`
  - [ ] `rg -n "고급 / legacy|patch|plan-structure" .omo/ulw-loop/evidence/task-4-vib-help.txt`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: help keeps legacy commands out of beginner section
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python -m vibelign.cli.vib_cli --help > .omo/ulw-loop/evidence/task-4-vib-help.txt
              python -c 'from pathlib import Path; text=Path(".omo/ulw-loop/evidence/task-4-vib-help.txt").read_text(); beginner=text.split("고급 / legacy:",1)[0]; assert "  patch" not in beginner and "plan-structure" not in beginner and "고급 / legacy:" in text'
    Expected: assertion exits 0 and help file keeps legacy commands only after `고급 / legacy:`
    Evidence: .omo/ulw-loop/evidence/task-4-vib-help.txt

  Scenario: direct command execution warns but continues
    Tool:     bash
    Steps:    uv run pytest tests/cli/test_legacy_surface.py::LegacySurfaceTest::test_vib_patch_prints_legacy_notice_before_execution tests/cli/test_legacy_surface.py::LegacySurfaceTest::test_vib_plan_structure_prints_legacy_notice_before_execution
    Expected: both tests pass and prove warning output appears before mocked execution
    Evidence: .omo/ulw-loop/evidence/task-4-command-notices.txt
  ```

  Commit: YES | Message: `feat(cli): demote legacy patch commands in help` | Files: [vibelign/cli/cli_base.py, vibelign/commands/vib_patch_cmd.py, vibelign/commands/vib_plan_structure_cmd.py, tests/cli/test_legacy_surface.py, tests/test_vib_cli_surface.py]

- [ ] 5. Lock README And Manual Beginner-Flow Docs Contract

  What to do: Verify README/README.ko first-flow sections do not recommend `vib patch`, `CodeSpeak`, or `plan-structure`; verify `docs/MANUAL.md` marks `vib patch` and `vib plan-structure` as legacy/internal and points beginners to `vib plan`, GUI planning room, or host AI MCP flows. Patch docs/tests only if the current committed content fails.
  Must NOT do: Do not rewrite release notes or research docs where historic `vib patch` measurements are allowed. Do not remove legacy manual sections entirely.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 8, 9] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:107` - README/docs contract
  - Pattern:  `docs/MANUAL.md:462` - `vib patch` manual section
  - Pattern:  `docs/MANUAL.md:572` - `vib plan-structure` manual section
  - Pattern:  `README.md:368` - historic release note; allowed if outside first flow
  - Pattern:  `README.ko.md:368` - historic release note; allowed if outside first flow
  - Test:     `tests/test_beginner_surface_docs.py:7` - README first 220 lines regression
  - Test:     `tests/test_beginner_surface_docs.py:27` - manual legacy section regression
  - External: `https://www.markdownguide.org/basic-syntax/` - markdown section structure reference if headings need small edits

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest tests/test_beginner_surface_docs.py`
  - [ ] `sed -n '1,220p' README.md > .omo/ulw-loop/evidence/task-5-readme-first-flow.txt`
  - [ ] `sed -n '1,220p' README.ko.md >> .omo/ulw-loop/evidence/task-5-readme-first-flow.txt`
  - [ ] `! rg -n "vib patch|CodeSpeak|plan-structure" .omo/ulw-loop/evidence/task-5-readme-first-flow.txt`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: README first flow is beginner-safe
    Tool:     bash
    Steps:    uv run pytest tests/test_beginner_surface_docs.py::test_readme_first_flow_does_not_recommend_legacy_patch_surface tests/test_beginner_surface_docs.py::test_korean_readme_first_flow_does_not_recommend_legacy_patch_surface
    Expected: both tests pass and first 220 lines of both READMEs omit forbidden legacy terms
    Evidence: .omo/ulw-loop/evidence/task-5-readme-tests.txt

  Scenario: manual keeps legacy sections with legacy wording
    Tool:     bash
    Steps:    uv run pytest tests/test_beginner_surface_docs.py::test_manual_marks_patch_and_plan_structure_as_legacy
    Expected: test passes and both manual command sections contain case-insensitive `legacy`
    Evidence: .omo/ulw-loop/evidence/task-5-manual-legacy.txt
  ```

  Commit: YES | Message: `docs: move patch commands out of beginner flow` | Files: [README.md, README.ko.md, docs/MANUAL.md, tests/test_beginner_surface_docs.py]

- [ ] 6. Preserve Internal MCP Core And Benchmark Surfaces

  What to do: Prove the excluded internals still exist and their regression tests pass after PR7 surface changes. Run MCP patch tests, tool snapshot tests, patch/core model smoke tests, and benchmark parser/surface tests that cover `bench --patch` or patch fixtures.
  Must NOT do: Do not edit excluded internals except to fix a regression introduced by PR7 surface changes; if a fix is needed, keep it minimal and add a targeted test.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [7, 9] | Blocked by: [1, 4]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:46` - excluded deletion list
  - Pattern:  `vibelign/mcp/mcp_patch_handlers.py:32` - `patch_get` handler
  - Pattern:  `vibelign/mcp/mcp_patch_handlers.py:127` - `patch_apply` handler
  - Pattern:  `vibelign/mcp/mcp_handler_registry.py:497` - MCP patch tool registration
  - Pattern:  `vibelign/core/codespeak.py:433` - `CodeSpeakResult` preserved core type
  - Pattern:  `vibelign/patch/patch_builder.py:9` - patch package depends on core CodeSpeak
  - Test:     `tests/test_mcp_patch_get.py:14` - MCP patch_get regression suite
  - Test:     `tests/test_mcp_patch_apply.py:15` - MCP patch_apply regression suite
  - Test:     `tests/test_mcp_tool_snapshot.py:104` - MCP tool snapshot includes patch tools
  - External: `https://v2.tauri.app/develop/calling-rust/` - command/API preservation principle for GUI/backend integration surfaces

  Acceptance criteria (agent-executable only):
  - [ ] `test -f vibelign/core/codespeak.py && test -f vibelign/core/patch_suggester.py && test -d vibelign/patch`
  - [ ] `uv run pytest tests/test_mcp_patch_get.py tests/test_mcp_patch_apply.py tests/test_mcp_tool_snapshot.py tests/test_core_model_exports.py`
  - [ ] `rg -n "bench.*patch|--patch" vibelign tests/benchmark > .omo/ulw-loop/evidence/task-6-bench-patch-preserved.txt`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: MCP patch tools still work
    Tool:     bash
    Steps:    uv run pytest tests/test_mcp_patch_get.py tests/test_mcp_patch_apply.py tests/test_mcp_tool_snapshot.py
    Expected: all selected MCP tests pass; patch_get and patch_apply remain in tool snapshot
    Evidence: .omo/ulw-loop/evidence/task-6-mcp-tests.txt

  Scenario: excluded files and benchmark patch surface still exist
    Tool:     bash
    Steps:    test -f vibelign/core/codespeak.py && test -f vibelign/core/patch_suggester.py && test -d vibelign/patch && rg -n "bench.*patch|--patch" vibelign tests/benchmark > .omo/ulw-loop/evidence/task-6-preserved-files.txt
    Expected: command exits 0 and evidence lists preserved patch/bench references
    Evidence: .omo/ulw-loop/evidence/task-6-preserved-files.txt
  ```

  Commit: NO | Message: `n/a` | Files: [vibelign/core/codespeak.py, vibelign/core/patch_suggester.py, vibelign/patch, vibelign/mcp/mcp_patch_handlers.py, tests/test_mcp_patch_get.py, tests/test_mcp_patch_apply.py, tests/test_mcp_tool_snapshot.py]

- [ ] 7. Write Dependency Map Classification Evidence

  What to do: Run the PR7 dependency search and write a concise classification artifact that separates beginner UI/docs, advanced/manual/legacy surfaces, internal core/MCP/tests, historic release/research docs, and command help. The artifact should also list which generated goals were superseded and which concrete implementation tasks satisfied `G001`-`G012`.
  Must NOT do: Do not use the dependency map as a reason to delete internals in PR7.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [9] | Blocked by: [1, 2, 3, 4, 5, 6]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:129` - required dependency search command
  - Pattern:  `plans/spec-pr7-legacy-surface-cleanup.md:138` - classification table
  - Pattern:  `.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json:151` - included CLI/help goal set begins
  - Pattern:  `.omo/ulw-loop/019e8fe3-bfa9-7040-8285-e12a08f1f7c7/goals.json:432` - excluded generated deletion goals
  - Test:     `tests/test_beginner_surface_docs.py:7` - docs classification constraints
  - External: `https://vitest.dev/guide/cli.html` - no direct dependency; cited for focused test command reproducibility

  Acceptance criteria (agent-executable only):
  - [ ] `rg -n "PATCH_COMMAND|PatchCard|vib patch|CodeSpeak|plan-structure|patch_get|patch_apply|codespeak|patch_suggester" vibelign vibelign-gui README.md README.ko.md docs tests > .omo/ulw-loop/evidence/task-7-pr7-dependency-map.raw.txt`
  - [ ] Create `.omo/ulw-loop/evidence/task-7-pr7-dependency-map.md` with sections: `Beginner surfaces removed`, `Advanced/manual legacy retained`, `Internal preserved`, `Historic/research retained`, `Generated goals superseded`.
  - [ ] `rg -n "Beginner surfaces removed|Advanced/manual legacy retained|Internal preserved|Generated goals superseded|G013|G018" .omo/ulw-loop/evidence/task-7-pr7-dependency-map.md`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: dependency search captures all PR7 terms
    Tool:     bash
    Steps:    rg -n "PATCH_COMMAND|PatchCard|vib patch|CodeSpeak|plan-structure|patch_get|patch_apply|codespeak|patch_suggester" vibelign vibelign-gui README.md README.ko.md docs tests > .omo/ulw-loop/evidence/task-7-pr7-dependency-map.raw.txt
    Expected: evidence file is non-empty and includes GUI, CLI/docs, MCP/core, and tests
    Evidence: .omo/ulw-loop/evidence/task-7-pr7-dependency-map.raw.txt

  Scenario: classification documents preservation decisions
    Tool:     bash
    Steps:    rg -n "Internal preserved|Generated goals superseded|G013|G014|G015|G016|G017|G018" .omo/ulw-loop/evidence/task-7-pr7-dependency-map.md
    Expected: evidence includes all six excluded deletion goals and an internal-preserved classification
    Evidence: .omo/ulw-loop/evidence/task-7-pr7-dependency-map.md
  ```

  Commit: NO | Message: `n/a` | Files: [.omo/ulw-loop/evidence/task-7-pr7-dependency-map.raw.txt, .omo/ulw-loop/evidence/task-7-pr7-dependency-map.md]

- [ ] 8. Capture PR7 Live Browser QA

  What to do: Add or adapt a PR7-specific browser QA script based on `.omo/ulw-loop/evidence/pr1-browser-qa.mjs`. It must use real Chrome CDP against the Vite app, mock only Tauri backend commands needed to enter Home/manual, capture screenshots, and write JSON action logs. It must prove beginner Home hides legacy terms and manual/advanced legacy access remains findable with `legacy` badges.
  Must NOT do: Do not downgrade browser-visible behavior to only Vitest. Do not leave Vite, Chrome, tmux, or bound ports running after evidence capture.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [9] | Blocked by: [2, 3, 5]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `.omo/ulw-loop/evidence/pr1-browser-qa.mjs:1` - existing Chrome CDP evidence script pattern
  - Pattern:  `.omo/ulw-loop/evidence/pr1-browser-qa.mjs:66` - Tauri mock injection pattern
  - Pattern:  `.omo/ulw-loop/evidence/pr1-browser-qa.mjs:116` - page assertion helper pattern
  - Pattern:  `.omo/ulw-loop/evidence/pr1-browser-qa.mjs:148` - screenshot capture helper pattern
  - Pattern:  `vibelign-gui/src/App.tsx:240` - nav tabs include `메뉴얼`
  - Pattern:  `vibelign-gui/src/App.tsx:286` - Home render with projectDir
  - Pattern:  `vibelign-gui/src/App.tsx:288` - manual page renders `Home` with `initialView="manual_list"`
  - Pattern:  `vibelign-gui/src/pages/__tests__/Home.simple.test.tsx:60` - beginner hidden terms to mirror in browser
  - External: `https://playwright.dev/docs/screenshots` - screenshot evidence expectation if the executor uses Playwright instead of the existing Chrome CDP harness

  Acceptance criteria (agent-executable only):
  - [ ] `cd vibelign-gui && npm run build`
  - [ ] Start Vite on `127.0.0.1:4173`, start Chrome remote debugging on `127.0.0.1:9222`, then run `node .omo/ulw-loop/evidence/pr7-browser-qa.mjs`.
  - [ ] Evidence files exist: `.omo/ulw-loop/evidence/task-8-pr7-home-beginner.json`, `.omo/ulw-loop/evidence/task-8-pr7-home-beginner.png`, `.omo/ulw-loop/evidence/task-8-pr7-manual-legacy.json`, `.omo/ulw-loop/evidence/task-8-pr7-manual-legacy.png`.
  - [ ] `lsof -i :4173` and `lsof -i :9222` show no lingering listener after cleanup.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: beginner Home hides PR7 legacy terms
    Tool:     browser use (Chrome CDP)
    Steps:    tmux new-session -d -s pr7-vite 'cd /Users/usabatch/coding/VibeLign/vibelign-gui && npm run dev -- --host 127.0.0.1 --port 4173'
              tmux new-session -d -s pr7-chrome '"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --remote-debugging-port=9222 --user-data-dir=/private/tmp/pr7-chrome about:blank'
              node .omo/ulw-loop/evidence/pr7-browser-qa.mjs
              tmux kill-session -t pr7-vite; tmux kill-session -t pr7-chrome; lsof -i :4173; lsof -i :9222
    Expected: JSON result says Home visible, `vib patch`, `CodeSpeak`, `plan-structure`, and `target_anchor` absent; PNG screenshot exists; cleanup receipt shows no listeners
    Evidence: .omo/ulw-loop/evidence/task-8-pr7-home-beginner.json

  Scenario: manual legacy commands remain findable
    Tool:     browser use (Chrome CDP)
    Steps:    In the same PR7 browser script, enter a mocked project, click `메뉴얼`, assert `패치`, `구조 계획`, and two `legacy` badges are visible, then capture screenshot and JSON.
    Expected: manual evidence JSON includes visible `patch`/`plan-structure` command entries with legacy badges while beginner Home evidence remains clean
    Evidence: .omo/ulw-loop/evidence/task-8-pr7-manual-legacy.json
  ```

  Commit: NO | Message: `n/a` | Files: [.omo/ulw-loop/evidence/pr7-browser-qa.mjs, .omo/ulw-loop/evidence/task-8-pr7-home-beginner.json, .omo/ulw-loop/evidence/task-8-pr7-home-beginner.png, .omo/ulw-loop/evidence/task-8-pr7-manual-legacy.json, .omo/ulw-loop/evidence/task-8-pr7-manual-legacy.png]

- [ ] 9. Aggregate Evidence, Quality Gates, And Commit Hygiene

  What to do: Re-run the focused and broad-enough quality gates after Tasks 1-8. Record ulw-loop evidence for passing criteria, update `.omo/start-work/ledger.jsonl` if the start-work flow is active, and prepare clean commits only for source/test/doc changes. Keep unrelated dirty runtime files unstaged. If a task had no source diff because current code already passed, record that as evidence instead of creating an empty commit.
  Must NOT do: Do not mark PR7 complete until F1-F4 all approve and the user explicitly says okay. Do not stage unrelated `.omc` state or old PR1 evidence.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [final verification] | Blocked by: [1, 2, 3, 4, 5, 6, 7, 8]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `/Users/usabatch/.codex/plugins/cache/sisyphuslabs/omo/0.1.0/skills/ulw-loop/SKILL.md:145` - record-evidence command form
  - Pattern:  `/Users/usabatch/.codex/plugins/cache/sisyphuslabs/omo/0.1.0/skills/ulw-loop/SKILL.md:161` - final quality gate
  - Pattern:  `.omo/plans/planning-work-help-primary-legacy-commands.md:7` - existing evidence style for current help slice
  - Pattern:  `.omo/plans/planning-work-plan-structure-command-accessor.md:7` - existing evidence style for current accessor slice
  - Pattern:  `vibelign-gui/package.json:6` - GUI scripts
  - Pattern:  `.omo/ulw-loop/evidence/pr1-quality-gate.json:6` - quality-gate JSON shape
  - External: `https://vitest.dev/guide/cli.html` - focused Vitest command filters

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py tests/test_beginner_surface_docs.py tests/test_mcp_patch_get.py tests/test_mcp_patch_apply.py tests/test_mcp_tool_snapshot.py`
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts src/pages/__tests__/Home.simple.test.tsx src/pages/__tests__/Onboarding.input-bar.test.tsx src/components/home/__tests__/ManualCommandList.test.tsx src/components/home/__tests__/AdvancedHomeCards.test.tsx`
  - [ ] `cd vibelign-gui && npm run build && npm run lint`
  - [ ] `git status --short > .omo/ulw-loop/evidence/task-9-final-status.txt` and status excludes unrelated runtime files from staging.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: aggregate automated verification passes
    Tool:     bash
    Steps:    uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py tests/test_beginner_surface_docs.py tests/test_mcp_patch_get.py tests/test_mcp_patch_apply.py tests/test_mcp_tool_snapshot.py
              cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts src/pages/__tests__/Home.simple.test.tsx src/pages/__tests__/Onboarding.input-bar.test.tsx src/components/home/__tests__/ManualCommandList.test.tsx src/components/home/__tests__/AdvancedHomeCards.test.tsx
              cd vibelign-gui && npm run build && npm run lint
    Expected: every command exits 0
    Evidence: .omo/ulw-loop/evidence/task-9-aggregate-verification.txt

  Scenario: clean staging set
    Tool:     bash
    Steps:    git status --short > .omo/ulw-loop/evidence/task-9-final-status.txt
              git diff --name-only --cached > .omo/ulw-loop/evidence/task-9-staged-files.txt
    Expected: staged files contain only PR7 source/test/doc changes and exclude unrelated `.omc` runtime state plus old `pr1-*` evidence
    Evidence: .omo/ulw-loop/evidence/task-9-final-status.txt
  ```

  Commit: YES | Message: `chore(pr7): complete legacy surface cleanup evidence` | Files: [.omo/start-work/ledger.jsonl, .omo/boulder.json, PR7 source/test/doc files from Tasks 2-5]

## Final verification wave (MANDATORY - after all implementation tasks)
> Runs in PARALLEL. ALL must APPROVE. Surface results to the caller and wait for an explicit "okay" before declaring complete.
- [ ] F1. Plan compliance audit - every task done, every acceptance criterion met
- [ ] F2. Code quality review - diagnostics clean, idioms match, no dead code
- [ ] F3. Real manual QA - every QA scenario executed with evidence captured
- [ ] F4. Scope fidelity - nothing extra shipped beyond Must-Have, nothing Must-NOT-Have introduced

## Commit strategy
- One logical change per commit. Conventional Commits (`<type>(<scope>): <subject>` body + footer).
- Atomic: every commit builds and passes tests on its own.
- No "WIP" / "fix typo squash later" commits on the final branch - clean up before merge.
- Reference the plan file path in the final commit footer: `Plan: plans/pr7-ulw-loop-continuation.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
