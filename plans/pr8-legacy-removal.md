# PR8 Legacy Feature Removal

## TL;DR
> Summary:      Hard-remove the failed legacy `patch`, CodeSpeak, and `plan-structure` surfaces in that order, while preserving the supported host-AI direct-read flow and current safety/rollback workflows.
> Deliverables:
> - Removed active `vib patch`, plain patch wrapper, MCP patch tools, patch bench mode, GUI patch card/help, and active patch guidance
> - Removed CodeSpeak and patch-targeting implementation after extracting or replacing the few supported dependencies that still import it
> - Removed `vib plan-structure` and legacy JSON structure-plan gating, with guard/precheck/manual/docs retargeted to `vib plan` and the planning room
> - Updated Python, GUI, docs, and MCP tests with RED->GREEN evidence and real-surface QA logs
> Effort:       XL
> Risk:         High - removal crosses CLI, MCP, GUI, docs, tests, and hidden recovery/anchor dependencies

## Scope
### Must have
- Hard-remove active `patch` surfaces:
  - `vib patch` parser and runtime.
  - `vibelign.commands.patch_cmd` plain wrapper.
  - `patch_get`, `patch_apply`, and patch-session MCP state.
  - MCP `doctor_patch` and `action_engine/generators/patch_generator.py` if it remains the only patch-preview consumer.
  - `vib bench --patch`, patch benchmark fixtures, and patch benchmark tests.
  - GUI patch command metadata, cards, help/search entries, and persisted card-order handling.
  - Active docs/rules that tell users or host AIs to use `vib patch`, `patch_get`, `patch_apply`, CodeSpeak, `target_file`, or `target_anchor` as a required workflow.
- Hard-remove CodeSpeak implementation:
  - `vibelign/core/codespeak.py`
  - `vibelign/core/ai_codespeak.py`
  - `vibelign/core/patch_suggester.py`
  - `vibelign/patch/`
  - strict patch contract/apply modules if no supported non-patch consumer remains.
- Preserve supported dependencies before deleting patch internals:
  - Keep anchor intent generation working by moving alias data out of `patch_suggester`.
  - Keep recovery preview/recommend/apply working without patch-target prediction.
  - Keep generic planning-session storage if any supported planning-room flow still needs it.
- Hard-remove active `plan-structure` surfaces:
  - `vib plan-structure` parser and runtime.
  - `vibelign/core/structure_planner.py` and `.vibelign/plans/*.json` active-plan validation path when used only by legacy `plan-structure`.
  - Guard/precheck/override/close/manual/docs wording that directs users to `vib plan-structure`.
  - GUI `plan-structure` command metadata, card, help/search entries, and persisted card-order handling.
- Preserve supported workflows:
  - CLI: `vib start`, `checkpoint`, `undo`, `history`, `doctor`, `guard`, `anchor`, `manual`, `rules`, `plan`, docs commands.
  - MCP: checkpoint tools, `doctor_run`, `guard_check`, anchor tools, `anchor_read_content`, `project_map_get`, memory/transfer tools.
  - GUI: Home beginner flow, planning room, checkpoint/undo/history, docs viewer, doctor, settings.
  - Project-rule workflow: host AI reads `.vibelign/project_map.json`/`anchor_read_content`, edits directly inside appropriate scope, then runs `guard_check` and `checkpoint_create`.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not delete or rewrite historical release notes, research docs, or `docs/superpowers/**` unless a file is actively linked as current guidance.
- Do not remove unrelated uses of the word `patch` meaning “small safe diff/patch” in engineering principles.
- Do not remove unrelated `legacy` compatibility surfaces such as the `vibelign` CLI wrapper, backup legacy rows, old API-key migration, or Rust/Tauri compatibility code.
- Do not remove `vib plan` or GUI planning-room code.
- Do not remove `mcp_state_store.load_planning_session` / `save_planning_session` unless the executor first proves no supported planning-room or `vib plan` lifecycle code imports them.
- Do not remove `doctor_run`, `doctor_plan`, `doctor_apply`, `guard_check`, `anchor_read_content`, or `project_map_get`.
- Do not rely on dirty `.omo/**` or `.omc/**` state, and do not revert unrelated working-tree changes.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest for Python/MCP/docs, Vitest for GUI, direct CLI/MCP smoke commands, and browser QA only if GUI route behavior changes require it
- QA policy: every task has agent-executed scenarios
- Evidence: `evidence/task-<N>-<slug>.<ext>`

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (patch removal, no dependencies):
- Task 1: Remove active Python CLI patch command surfaces
- Task 2: Remove MCP patch tools and patch-session capture
- Task 3: Remove patch benchmark mode
- Task 4: Remove GUI patch command/card/help surface
- Task 5: Remove active patch workflow guidance from docs and exported project rules
- Task 6: Replace supported hidden dependencies on patch internals

Wave 2 (after Wave 1):
- Task 7: Remove CodeSpeak and patch core modules, depends [1, 2, 3, 6]

Wave 3 (plan-structure removal, after CodeSpeak cleanup):
- Task 8: Remove active Python CLI plan-structure command surfaces, depends [7]
- Task 9: Migrate guard/precheck away from legacy structure-plan JSON, depends [8]
- Task 10: Remove GUI plan-structure command/card/help surface, depends [8]
- Task 11: Remove active plan-structure guidance from docs and exported project rules, depends [8, 9]
- Task 12: Static cleanup of stale tests/imports/fixtures, depends [7, 8, 9, 10, 11]

Wave 4 (integration):
- Task 13: End-to-end preserved-workflow regression sweep, depends [1-12]

Critical path: Task 1 -> Task 7 -> Task 8 -> Task 9 -> Task 13

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 7, 13  | 2, 3, 4, 5, 6       |
| 2    | none       | 7, 13  | 1, 3, 4, 5, 6       |
| 3    | none       | 7, 13  | 1, 2, 4, 5, 6       |
| 4    | none       | 13     | 1, 2, 3, 5, 6       |
| 5    | none       | 13     | 1, 2, 3, 4, 6       |
| 6    | none       | 7, 13  | 1, 2, 3, 4, 5       |
| 7    | 1, 2, 3, 6 | 8, 12, 13 | none             |
| 8    | 7          | 9, 10, 11, 12, 13 | none       |
| 9    | 8          | 11, 12, 13 | 10                 |
| 10   | 8          | 12, 13 | 9, 11               |
| 11   | 8, 9       | 12, 13 | 10                  |
| 12   | 7, 8, 9, 10, 11 | 13 | none              |
| 13   | 1-12       | final  | F1-F4 after completion |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Remove active Python CLI patch command surfaces

  What to do: Rewrite PR7 legacy-surface tests so `patch` is absent instead of hidden/legacy. Remove the `patch` parser block from `vibelign/cli/cli_command_groups.py`, remove the lazy command target to `vibelign.commands.vib_patch_cmd`, remove the plain wrapper module `vibelign/commands/patch_cmd.py`, and remove direct tests that only validate `vib patch` behavior. Update hand-written CLI help so it has no `patch` legacy command row. Keep unrelated `--patch` options for other supported commands until their owning task removes them.
  Must NOT do: Do not touch `plan-structure` in this task. Do not remove generic “small safe patch” engineering language. Do not remove `vib guard --patch` or other non-legacy flags unless a test proves they are part of `vib patch`.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/cli/cli_command_groups.py:289` - `vib patch` parser registration starts here and points to `run_vib_patch` at line 333.
  - Pattern:  `vibelign/cli/cli_base.py:130` - main help still lists `patch` under “고급 / legacy”.
  - Pattern:  `vibelign/commands/vib_patch_cmd.py:164` - active `vib patch` runtime path and legacy notice.
  - Pattern:  `vibelign/commands/patch_cmd.py:7` - plain patch wrapper imports `build_legacy_patch_suggestion`.
  - Test:     `tests/cli/test_legacy_surface.py:36` - currently asserts `vib patch` prints a legacy notice; rewrite to assert parser absence.
  - Test:     `tests/test_vib_cli_surface.py:32` - broad command-surface snapshot; add explicit absence for `patch`.
  - External: `https://docs.python.org/3/library/argparse.html#sub-commands` - `argparse` subcommands are registered through `add_subparsers().add_parser()` and can be tested through parser choices/help.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: after rewriting tests but before implementation, `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py` fails because `patch` is still registered. Save output to `evidence/task-1-patch-cli-red.txt`.
  - [ ] `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py` passes after implementation. Save output to `evidence/task-1-patch-cli-green.txt`.
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli patch "login"` exits nonzero and stderr/stdout contains `invalid choice` or `usage:`. Save output to `evidence/task-1-patch-cli-error.txt`.
  - [ ] `PYTHONPATH=. uv run python - <<'PY'` script over `build_parser()` asserts `"patch" not in subparsers_action.choices` and preserved commands include `start`, `checkpoint`, `doctor`, `guard`, `anchor`, `manual`, `rules`, `plan`. Save output to `evidence/task-1-patch-cli-choices.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: patch command is gone while supported commands remain
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              from typing import Any, cast
              from vibelign.cli.vib_cli import build_parser
              parser = build_parser()
              sub = cast(Any, next(a for a in parser._actions if getattr(a, "choices", None)))
              commands = set(sub.choices)
              assert "patch" not in commands
              for name in ["start", "checkpoint", "doctor", "guard", "anchor", "manual", "rules", "plan"]:
                  assert name in commands, name
              print("ok")
              PY
    Expected: Prints `ok` and exits 0.
    Evidence: evidence/task-1-patch-cli-choices.txt

  Scenario: removed patch command fails clearly
    Tool:     bash
    Steps:    set +e; PYTHONPATH=. uv run python -m vibelign.cli.vib_cli patch "login" > evidence/task-1-patch-cli-error.txt 2>&1; code=$?; test "$code" -ne 0; grep -E "invalid choice|usage:" evidence/task-1-patch-cli-error.txt
    Expected: Command exits nonzero and captured output contains `invalid choice` or `usage:`.
    Evidence: evidence/task-1-patch-cli-error.txt
  ```

  Commit: YES | Message: `feat(cli): remove patch command surface` | Files: [`vibelign/cli/cli_command_groups.py`, `vibelign/cli/cli_base.py`, `vibelign/commands/vib_patch_cmd.py`, `vibelign/commands/patch_cmd.py`, `tests/cli/test_legacy_surface.py`, `tests/test_vib_cli_surface.py`, `tests/test_patch_cmd_wrapper.py`, `tests/test_vib_patch_contract_v0.py`, `tests/test_vib_patch_render.py`]

- [ ] 2. Remove MCP patch tools and patch-session capture

  What to do: Rewrite MCP snapshots to assert removed tool names are absent and preserved tool names remain. Remove `patch_get`, `patch_apply`, and `doctor_patch` from tool specs, handler protocols, registry mappings, and dispatch behavior. Delete `vibelign/mcp/mcp_patch_handlers.py` once no registry imports it. Remove `PATCH_SESSION_KEY`, `load_patch_session`, `save_patch_session`, `new_patch_session_id`, and patch-apply dispatch memory capture if they are only used by removed tools. Keep the generic timestamp helper by renaming it to a non-patch name if `plan-close` or supported planning code still needs it.
  Must NOT do: Do not remove `doctor_run`, `doctor_plan`, `doctor_apply`, `guard_check`, checkpoint tools, memory/transfer tools, `anchor_read_content`, or `project_map_get`.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/mcp/mcp_tool_specs.py:277` - `patch_get` tool spec begins.
  - Pattern:  `vibelign/mcp/mcp_tool_specs.py:303` - `patch_apply` tool spec begins.
  - Pattern:  `vibelign/mcp/mcp_tool_specs.py:491` - `anchor_read_content` and `project_map_get` specs that must remain.
  - Pattern:  `vibelign/mcp/mcp_handler_registry.py:108` - patch handler protocol.
  - Pattern:  `vibelign/mcp/mcp_handler_registry.py:497` - `patch_get` registry entry.
  - Pattern:  `vibelign/mcp/mcp_handler_registry.py:498` - `patch_apply` registry entry.
  - Pattern:  `vibelign/mcp/mcp_patch_handlers.py:32` - active `handle_patch_get`.
  - Pattern:  `vibelign/mcp/mcp_patch_handlers.py:127` - active `handle_patch_apply`.
  - Pattern:  `vibelign/mcp/mcp_state_store.py:11` - patch-session key and helpers.
  - Pattern:  `vibelign/mcp/mcp_dispatch.py:84` - patch-apply memory auto-capture.
  - Pattern:  `vibelign/mcp/mcp_doctor_handlers.py:39` - `doctor_patch` delegates to patch preview generator.
  - Test:     `tests/test_mcp_tool_snapshot.py:73` - MCP tool list snapshot currently includes patch tools.
  - Test:     `tests/test_mcp_patch_get.py:1` - behavioral tests to remove or replace with absence tests.
  - Test:     `tests/test_mcp_patch_apply.py:1` - behavioral tests to remove or replace with absence tests.
  - Test:     `tests/test_mcp_patch_session.py:1` - patch-session behavior to remove.
  - External: `https://modelcontextprotocol.io/specification/2025-06-18/server/tools` - `tools/list` advertises tool `name`, `description`, and `inputSchema`; absence from this list is the MCP contract for removed tools.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: rewritten MCP snapshot/absence tests fail before implementation because `patch_get`, `patch_apply`, or `doctor_patch` still appear. Save output to `evidence/task-2-mcp-patch-red.txt`.
  - [ ] `uv run pytest tests/test_mcp_tool_snapshot.py tests/test_mcp_dispatch_new_tools.py tests/test_mcp_dispatch_capture.py tests/test_mcp_state_store.py` passes. Save output to `evidence/task-2-mcp-patch-green.txt`.
  - [ ] `rg -n '"patch_get"|"patch_apply"|"doctor_patch"|PATCH_SESSION_KEY|load_patch_session|save_patch_session|new_patch_session_id' vibelign/mcp tests/test_mcp_tool_snapshot.py` returns no active-code matches except explicit negative assertions in tests. Save output to `evidence/task-2-mcp-patch-static.txt`.
  - [ ] A direct list-tools script asserts removed tools are absent and `checkpoint_create`, `checkpoint_restore`, `doctor_run`, `guard_check`, `anchor_read_content`, and `project_map_get` remain. Save output to `evidence/task-2-mcp-tools-list.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: MCP tool list removes patch tools and preserves supported tools
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              import asyncio
              from vibelign.mcp.mcp_tool_specs import TOOL_SPECS
              names = [tool["name"] for tool in TOOL_SPECS]
              for removed in ["patch_get", "patch_apply", "doctor_patch"]:
                  assert removed not in names, removed
              for kept in ["checkpoint_create", "checkpoint_restore", "doctor_run", "guard_check", "anchor_read_content", "project_map_get"]:
                  assert kept in names, kept
              print("ok")
              PY
    Expected: Prints `ok` and exits 0.
    Evidence: evidence/task-2-mcp-tools-list.txt

  Scenario: removed MCP patch tool call is rejected
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              import asyncio
              from vibelign.mcp.mcp_dispatch import call_tool_dispatch
              async def main():
                  result = await call_tool_dispatch("patch_get", {"request": "fix login"})
                  text = "\\n".join(getattr(item, "text", str(item)) for item in result)
                  assert "Unknown tool" in text or "unknown" in text.lower() or "지원하지" in text
                  print(text)
              asyncio.run(main())
              PY
    Expected: Output reports an unknown/unsupported tool rather than executing patch logic.
    Evidence: evidence/task-2-mcp-patch-call-error.txt
  ```

  Commit: YES | Message: `feat(mcp): remove patch tools` | Files: [`vibelign/mcp/mcp_tool_specs.py`, `vibelign/mcp/mcp_handler_registry.py`, `vibelign/mcp/mcp_patch_handlers.py`, `vibelign/mcp/mcp_state_store.py`, `vibelign/mcp/mcp_health_handlers.py`, `vibelign/mcp/mcp_dispatch.py`, `vibelign/mcp/mcp_doctor_handlers.py`, `vibelign/action_engine/generators/patch_generator.py`, `tests/test_mcp_tool_snapshot.py`, `tests/test_mcp_patch_get.py`, `tests/test_mcp_patch_apply.py`, `tests/test_mcp_patch_session.py`, `tests/test_mcp_dispatch_capture.py`, `tests/test_mcp_dispatch_new_tools.py`, `tests/test_mcp_state_store.py`, `tests/test_mcp_doctor_handlers.py`]

- [ ] 3. Remove patch benchmark mode

  What to do: Remove `vib bench --patch` and `--update-baseline` behavior when it only applies to patch-suggester accuracy. Keep the generic anchor A/B benchmark modes `--generate`, `--score`, and `--report`. Remove patch benchmark fixture modules and tests. Update CLI/manual/docs copy so `bench` no longer mentions patch-suggester.
  Must NOT do: Do not remove the `bench` command itself or the non-patch benchmark output fixtures unless tests prove they are exclusively patch-suggester fixtures.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/cli/cli_command_groups.py:875` - `bench` parser description.
  - Pattern:  `vibelign/cli/cli_command_groups.py:900` - `--patch` argument registration.
  - Pattern:  `vibelign/commands/vib_bench_cmd.py:71` - patch accuracy measurement imports `score_candidates` and `suggest_patch`.
  - Pattern:  `vibelign/commands/bench_fixtures.py:1` - shared patch benchmark sandbox fixtures.
  - Test:     `tests/test_bench_patch_command.py:1` - in-process patch benchmark tests.
  - Test:     `tests/benchmark/test_patch_suggester_baseline.py:1` - patch-suggester baseline lock.
  - Pattern:  `vibelign/commands/vib_manual_cmd.py:790` - manual command data mentions patch benchmark.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: a parser/test update asserts `bench --patch` is gone and fails before implementation. Save output to `evidence/task-3-bench-patch-red.txt`.
  - [ ] `uv run pytest tests/test_vib_cli_surface.py` passes with `bench` still present and `bench --patch` rejected. Save output to `evidence/task-3-bench-patch-green.txt`.
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli bench --patch` exits nonzero with invalid/unrecognized argument. Save output to `evidence/task-3-bench-patch-error.txt`.
  - [ ] `rg -n "bench --patch|patch-suggester 정확도|_measure_patch_accuracy|prepare_patch_sandbox" vibelign tests docs/MANUAL.md` returns no active matches except historical docs excluded by scope. Save output to `evidence/task-3-bench-patch-static.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: generic bench remains available
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python -m vibelign.cli.vib_cli bench --help > evidence/task-3-bench-help.txt 2>&1 && grep -E -- "--generate|--score|--report" evidence/task-3-bench-help.txt && ! grep -F -- "--patch" evidence/task-3-bench-help.txt
    Expected: Help includes generic bench options and omits `--patch`.
    Evidence: evidence/task-3-bench-help.txt

  Scenario: removed patch benchmark flag fails
    Tool:     bash
    Steps:    set +e; PYTHONPATH=. uv run python -m vibelign.cli.vib_cli bench --patch > evidence/task-3-bench-patch-error.txt 2>&1; code=$?; test "$code" -ne 0; grep -E "unrecognized arguments|invalid choice|usage:" evidence/task-3-bench-patch-error.txt
    Expected: Command exits nonzero and reports invalid/unrecognized `--patch`.
    Evidence: evidence/task-3-bench-patch-error.txt
  ```

  Commit: YES | Message: `feat(bench): remove patch accuracy mode` | Files: [`vibelign/cli/cli_command_groups.py`, `vibelign/commands/vib_bench_cmd.py`, `vibelign/commands/bench_fixtures.py`, `vibelign/commands/vib_manual_cmd.py`, `tests/test_bench_patch_command.py`, `tests/benchmark/test_patch_suggester_baseline.py`, `tests/benchmark/patch_accuracy_baseline.json`, `tests/benchmark/scenarios.json`, `tests/benchmark/user_requests.json`]

- [ ] 4. Remove GUI patch command/card/help surface

  What to do: Remove patch command metadata, accessors, card component, advanced-card render case, manual-list legacy assertions, and help/search entries. Sanitize persisted advanced `cardOrder` so existing users with `"patch"` saved do not render blanks or throw. Update settings/API-key copy that names `vib patch --ai`. Keep non-patch AI cards such as Ask/Explain/Export if still supported.
  Must NOT do: Do not remove unrelated GUI “legacy” references for backup data, API-key migration, or planning persona fallback.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/lib/commandData.ts:503` - patch command metadata block.
  - Pattern:  `vibelign-gui/src/lib/commands.ts:16` - `getPatchCommand`.
  - Pattern:  `vibelign-gui/src/lib/commands.ts:24` - `PATCH_COMMAND`.
  - Pattern:  `vibelign-gui/src/components/home/AdvancedHomeCards.tsx:24` - `PatchCard` import.
  - Pattern:  `vibelign-gui/src/components/home/AdvancedHomeCards.tsx:111` - patch render case.
  - Pattern:  `vibelign-gui/src/components/cards/ai/PatchCard.tsx:1` - patch card component.
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:147` - patch help entry.
  - Pattern:  `vibelign-gui/src/pages/Settings.tsx:409` - settings copy mentions `vib patch --ai`.
  - Test:     `vibelign-gui/src/lib/legacySurface.test.ts:1` - currently expects patch to be legacy; rewrite to expect absence.
  - Test:     `vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx:33` - manual legacy command badges currently include patch.
  - Test:     `vibelign-gui/src/pages/__tests__/Home.simple.test.tsx:60` - beginner surface already asserts patch terms hidden.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: rewritten GUI tests assert patch metadata/accessors/cards are absent and fail before implementation. Save output to `evidence/task-4-gui-patch-red.txt`.
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/components/home/__tests__/ManualCommandList.test.tsx src/pages/__tests__/Home.simple.test.tsx src/lib/helpData.test.ts` passes. Save output to `evidence/task-4-gui-patch-tests.txt`.
  - [ ] `rg -n "PatchCard|getPatchCommand|PATCH_COMMAND|vib patch|patch_get|patch_apply|CodeSpeak|target_anchor" vibelign-gui/src` returns no active matches except tests that assert absence or unrelated lower-case generic text approved by the executor. Save output to `evidence/task-4-gui-patch-static.txt`.
  - [ ] A small Vitest or unit assertion proves saved `cardOrder` containing `"patch"` is filtered out without throwing. Save output to `evidence/task-4-gui-patch-cardorder.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: GUI metadata has no patch command and preserved commands remain
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts
    Expected: Tests pass; command metadata/search no longer exposes patch and still exposes current commands.
    Evidence: evidence/task-4-gui-patch-tests.txt

  Scenario: stale saved patch card id is ignored
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/components/home/__tests__/ManualCommandList.test.tsx src/pages/__tests__/Home.simple.test.tsx
    Expected: Tests pass with no rendered patch card, no blank card, and no thrown missing metadata error.
    Evidence: evidence/task-4-gui-patch-cardorder.txt
  ```

  Commit: YES | Message: `feat(gui): remove patch command surface` | Files: [`vibelign-gui/src/lib/commandData.ts`, `vibelign-gui/src/lib/commands.ts`, `vibelign-gui/src/components/home/AdvancedHomeCards.tsx`, `vibelign-gui/src/components/cards/ai/PatchCard.tsx`, `vibelign-gui/src/lib/helpData.ts`, `vibelign-gui/src/pages/Settings.tsx`, `vibelign-gui/src/lib/legacySurface.test.ts`, `vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx`, `vibelign-gui/src/pages/__tests__/Home.simple.test.tsx`, `vibelign-gui/src/lib/helpData.test.ts`]

- [ ] 5. Remove active patch workflow guidance from docs and exported project rules

  What to do: Replace active instructions that tell AIs/users to call `patch_get`, `patch_apply`, `vib patch`, CodeSpeak, `target_file`, or `target_anchor` with the supported direct-read workflow: read `.vibelign/project_map.json`, use MCP `project_map_get` / `anchor_read_content` when available, edit the relevant file/anchor directly, run `guard_check`, and create a checkpoint. Update generated-export templates so future `AGENTS.md` files no longer regenerate removed patch instructions. Update quickstart and manual command sections so `vib patch` is removed, not marked legacy.
  Must NOT do: Do not mass-delete historical release notes/research docs. Do not remove generic “smallest safe patch” language.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `AGENTS.md:40` - active safe mode says to call `patch_get`.
  - Pattern:  `AGENTS.md:60` - CLI fallback says `vib patch`.
  - Pattern:  `vibelign/commands/export_cmd.py:70` - exported AGENTS template says to call `patch_get`.
  - Pattern:  `vibelign/commands/export_cmd.py:172` - setup workflow says `vib patch`.
  - Pattern:  `AI_DEV_SYSTEM_SINGLE_FILE.md:90` - active rules reference `vib patch`/CodeSpeak targeting.
  - Pattern:  `AI_DEV_SYSTEM_SINGLE_FILE.md:128` - patch-specific rules section.
  - Pattern:  `VibeLign_QUICKSTART.md:161` - quickstart recommends `vib patch`.
  - Pattern:  `VibeLign_QUICKSTART.md:252` - quickstart command table lists `vib patch`.
  - Pattern:  `docs/MANUAL.md:462` - manual `vib patch` section.
  - Pattern:  `docs/wiki/command-guide.md:63` - active wiki command map lists `vib patch`.
  - Pattern:  `README.md:368` - active README release note says CLI `vib patch` is unchanged; update because PR8 changes it.
  - Pattern:  `README.ko.md:368` - Korean README equivalent.
  - Test:     `tests/test_beginner_surface_docs.py:7` - docs tests currently only check first-flow and legacy marking; strengthen for hard removal in active docs.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: strengthened docs/export tests fail before docs/rules implementation because active guidance still mentions removed patch workflow. Save output to `evidence/task-5-docs-patch-red.txt`.
  - [ ] `uv run pytest tests/test_beginner_surface_docs.py tests/test_vib_start.py` passes. Save output to `evidence/task-5-docs-patch-green.txt`.
  - [ ] `rg -n "patch_get|patch_apply|CodeSpeak|target_file|target_anchor|vib patch" AGENTS.md AI_DEV_SYSTEM_SINGLE_FILE.md VibeLign_QUICKSTART.md docs/MANUAL.md docs/wiki vibelign/commands/export_cmd.py` returns no active guidance matches except tests or explicitly approved historical notes. Save output to `evidence/task-5-docs-patch-static.txt`.
  - [ ] `uv run python - <<'PY'` exports tool files into a temp project and asserts generated AGENTS text contains `project_map_get`, `anchor_read_content`, `guard_check`, `checkpoint_create` and omits `patch_get`, `CodeSpeak`, `vib patch`. Save output to `evidence/task-5-export-rules.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: exported project rules use direct-read workflow
    Tool:     bash
    Steps:    uv run pytest tests/test_vib_start.py -k "export or rule or ensure_rule_files" > evidence/task-5-export-rules.txt 2>&1
    Expected: Export/start rule tests pass and generated rules omit removed patch workflow.
    Evidence: evidence/task-5-export-rules.txt

  Scenario: active docs no longer instruct users to run vib patch
    Tool:     bash
    Steps:    uv run pytest tests/test_beginner_surface_docs.py > evidence/task-5-docs-patch-green.txt 2>&1
    Expected: Active README/quickstart/manual/wiki docs tests pass with no current `vib patch` recommendation or section.
    Evidence: evidence/task-5-docs-patch-green.txt
  ```

  Commit: YES | Message: `docs(rules): remove patch workflow guidance` | Files: [`AGENTS.md`, `AI_DEV_SYSTEM_SINGLE_FILE.md`, `VibeLign_QUICKSTART.md`, `README.md`, `README.ko.md`, `docs/MANUAL.md`, `docs/wiki/command-guide.md`, `docs/wiki/getting-started.md`, `docs/wiki/core-workflow.md`, `docs/wiki/index.md`, `vibelign/commands/export_cmd.py`, `tests/test_beginner_surface_docs.py`, `tests/test_vib_start.py`]

- [ ] 6. Replace supported hidden dependencies on patch internals

  What to do: Before deleting `patch_suggester`, replace supported imports that use it for non-patch features. Create a small non-patch alias module such as `vibelign/core/token_aliases.py` for Korean/English token aliases, and update anchor intent generation to use it. Remove recovery’s dependency on patch target prediction by returning no patch-derived target or by using project-map/intent-zone data already available to recovery; tests must prove recovery still produces read-only plans. Update tests that currently import tokenizer helpers from `patch_suggester` to import the new supported module or delete them if they only validate removed patch targeting.
  Must NOT do: Do not reintroduce CodeSpeak, patch suggestion, or natural-language file targeting under a new name. Do not break `vib recover`, MCP recovery, or anchor auto-intent.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [7, 13] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/core/anchor_tools.py:765` - `_get_reverse_aliases` imports `_TOKEN_ALIASES` from `patch_suggester`.
  - Pattern:  `vibelign/core/recovery/planner.py:8` - recovery imports `suggest_recovery_level2_patch`.
  - Pattern:  `vibelign/core/recovery/planner.py:216` - `_recovery_level2_target` calls patch suggester.
  - Test:     `tests/test_anchor_alias_index.py:146` - tests import patch-suggester helpers for anchor scoring/aliases.
  - Test:     `tests/test_ui_label_index.py:5` - imports `tokenize` from patch_suggester.
  - Test:     `tests/test_recovery_agent.py` - recovery behavior should remain read-only.
  - Test:     `tests/test_mcp_recovery_handlers.py` - MCP recovery must remain.
  - Test:     `tests/fixtures/tokenizer_goldens/_regenerate.py:21` - tokenizer goldens currently import patch_suggester.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: tests updated to import/use non-patch alias or recovery behavior fail before implementation. Save output to `evidence/task-6-hidden-deps-red.txt`.
  - [ ] `uv run pytest tests/test_anchor_alias_index.py tests/test_ui_label_index.py tests/test_recovery_agent.py tests/test_mcp_recovery_handlers.py tests/test_memory_recovery_schemas.py` passes. Save output to `evidence/task-6-hidden-deps-green.txt`.
  - [ ] `rg -n "from vibelign.core.patch_suggester|import vibelign.core.patch_suggester|suggest_recovery_level2_patch|_TOKEN_ALIASES" vibelign tests` returns no active matches except removed tests pending Task 7. Save output to `evidence/task-6-hidden-deps-static.txt`.
  - [ ] `PYTHONPATH=. uv run python - <<'PY'` imports `vibelign.core.anchor_tools` and builds a recovery plan from an empty `RecoverySignalSet` without importing `vibelign.core.patch_suggester`. Save output to `evidence/task-6-hidden-deps-import.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: anchor alias generation no longer imports patch_suggester
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              import sys
              import vibelign.core.anchor_tools as anchor_tools
              _ = anchor_tools._get_reverse_aliases()
              assert "vibelign.core.patch_suggester" not in sys.modules
              print("ok")
              PY
    Expected: Prints `ok`; `patch_suggester` is not imported.
    Evidence: evidence/task-6-hidden-deps-import.txt

  Scenario: recovery plan remains usable without patch-derived targeting
    Tool:     bash
    Steps:    uv run pytest tests/test_recovery_agent.py tests/test_mcp_recovery_handlers.py tests/test_memory_recovery_schemas.py > evidence/task-6-recovery-green.txt 2>&1
    Expected: Recovery tests pass and no recovery code imports patch-suggester.
    Evidence: evidence/task-6-recovery-green.txt
  ```

  Commit: YES | Message: `refactor(core): remove patch dependencies from supported helpers` | Files: [`vibelign/core/token_aliases.py`, `vibelign/core/anchor_tools.py`, `vibelign/core/recovery/planner.py`, `tests/test_anchor_alias_index.py`, `tests/test_ui_label_index.py`, `tests/test_recovery_agent.py`, `tests/test_mcp_recovery_handlers.py`, `tests/test_memory_recovery_schemas.py`, `tests/fixtures/tokenizer_goldens/_regenerate.py`, `tests/fixtures/tokenizer_goldens/*.expected.json`]

- [ ] 7. Remove CodeSpeak and patch core modules

  What to do: Delete CodeSpeak, AI CodeSpeak, patch suggester, strict patch contract/apply modules, and the `vibelign/patch/` package after Tasks 1, 2, 3, and 6 have removed active consumers. Update `vibelign/core/__init__.py` exports and any type models that only exist for removed patch contracts. Delete or rewrite tests that only validate CodeSpeak/patch targeting; keep only tests for preserved anchor/project-map/guard/recovery behavior.
  Must NOT do: Do not leave compatibility shims named `codespeak`, `patch_suggester`, `strict_patch`, or `vibelign.patch`. Do not remove `IntentIR` if `vib plan` or another supported flow still imports it.

  Parallelization: Can parallel: NO | Wave 2 | Blocks: [8, 12, 13] | Blocked by: [1, 2, 3, 6]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/core/codespeak.py:433` - `CodeSpeakResult` model.
  - Pattern:  `vibelign/core/codespeak.py:717` - `build_codespeak`.
  - Pattern:  `vibelign/core/ai_codespeak.py:6` - imports CodeSpeak types.
  - Pattern:  `vibelign/core/patch_suggester.py:1601` - `suggest_patch`.
  - Pattern:  `vibelign/core/strict_patch.py:276` - `apply_strict_patch`.
  - Pattern:  `vibelign/core/patch_contract.py:1` - patch contract model.
  - Pattern:  `vibelign/core/patch_validation.py:1` - strict patch validation helpers.
  - Pattern:  `vibelign/patch/patch_builder.py:9` - patch package imports CodeSpeak.
  - Pattern:  `vibelign/core/__init__.py:7` - exports `PatchContract`.
  - Test:     `tests/test_codespeak.py:1` - remove with feature.
  - Test:     `tests/test_ai_codespeak.py:1` - remove with feature.
  - Test:     `tests/test_edge_patch_codespeak.py:1` - remove with feature.
  - Test:     `tests/test_patch_accuracy_scenarios.py:1` - remove with feature.
  - Test:     `tests/test_patch_suggester_score_candidates.py:1` - remove with feature.
  - Test:     `tests/test_patch_validation_strict.py:1` - remove if strict patch has no supported consumers.
  - Test:     `tests/test_checkpoint_router_consumers.py:182` - update if strict patch checkpoint consumer is removed.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: static absence test fails before deletion because CodeSpeak/patch modules still exist. Save output to `evidence/task-7-codespeak-core-red.txt`.
  - [ ] `uv run pytest tests/test_core_model_exports.py tests/test_anchor_alias_index.py tests/test_mcp_tool_snapshot.py tests/test_recovery_agent.py tests/test_mcp_recovery_handlers.py` passes. Save output to `evidence/task-7-codespeak-core-green.txt`.
  - [ ] `PYTHONPATH=. uv run python - <<'PY'` verifies `importlib.util.find_spec()` returns `None` for `vibelign.core.codespeak`, `vibelign.core.ai_codespeak`, `vibelign.core.patch_suggester`, `vibelign.core.strict_patch`, `vibelign.core.patch_contract`, `vibelign.core.patch_validation`, and `vibelign.patch`. Save output to `evidence/task-7-codespeak-imports.txt`.
  - [ ] `rg -n "CodeSpeak|codespeak|patch_suggester|strict_patch|vibelign\\.patch|PatchContract|PatchSuggestion" vibelign tests` returns no active matches except historical docs excluded by scope or negative assertions. Save output to `evidence/task-7-codespeak-static.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: removed modules are not importable
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              import importlib.util
              removed = [
                  "vibelign.core.codespeak",
                  "vibelign.core.ai_codespeak",
                  "vibelign.core.patch_suggester",
                  "vibelign.core.strict_patch",
                  "vibelign.core.patch_contract",
                  "vibelign.core.patch_validation",
                  "vibelign.patch",
              ]
              for name in removed:
                  assert importlib.util.find_spec(name) is None, name
              print("ok")
              PY
    Expected: Prints `ok`; all removed modules have no import spec.
    Evidence: evidence/task-7-codespeak-imports.txt

  Scenario: preserved core exports still import
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              import vibelign.core
              assert hasattr(vibelign.core, "IntentIR")
              assert hasattr(vibelign.core, "JsonObject")
              print("ok")
              PY
    Expected: Core package imports without patch-contract exports.
    Evidence: evidence/task-7-core-imports.txt
  ```

  Commit: YES | Message: `feat(core): remove codespeak and patch internals` | Files: [`vibelign/core/codespeak.py`, `vibelign/core/ai_codespeak.py`, `vibelign/core/patch_suggester.py`, `vibelign/core/strict_patch.py`, `vibelign/core/patch_contract.py`, `vibelign/core/patch_validation.py`, `vibelign/core/patch_plan.py`, `vibelign/patch/`, `vibelign/core/__init__.py`, `tests/test_codespeak.py`, `tests/test_ai_codespeak.py`, `tests/test_ai_codespeak_prompt.py`, `tests/test_edge_patch_codespeak.py`, `tests/test_patch_accuracy_scenarios.py`, `tests/test_patch_suggester_score_candidates.py`, `tests/test_patch_validation_strict.py`, `tests/test_patch_contract_gate.py`, `tests/test_checkpoint_router_consumers.py`, `tests/test_core_model_exports.py`]

- [ ] 8. Remove active Python CLI plan-structure command surfaces

  What to do: Rewrite CLI tests to assert `plan-structure` is absent. Remove the `plan-structure` parser block and lazy command target. Delete `vibelign/commands/vib_plan_structure_cmd.py` and `vibelign/core/structure_planner.py` if no supported consumer remains. Remove main help legacy row. Keep `vib plan` parser/runtime unchanged.
  Must NOT do: Do not remove `vib plan`, `plans/*.md` writer/storage, or GUI planning-room command APIs.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [9, 10, 11, 12, 13] | Blocked by: [7]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/cli/cli_command_groups.py:731` - `plan-structure` parser registration.
  - Pattern:  `vibelign/cli/cli_command_groups.py:757` - lazy command target to `vib_plan_structure_cmd`.
  - Pattern:  `vibelign/cli/cli_base.py:131` - main help legacy row.
  - Pattern:  `vibelign/commands/vib_plan_structure_cmd.py:40` - command runtime.
  - Pattern:  `vibelign/core/structure_planner.py:349` - `build_structure_plan`.
  - Pattern:  `vibelign/commands/vib_plan_cmd.py:39` - supported `vib plan` runtime that must remain.
  - Test:     `tests/test_structure_planner.py:11` - legacy plan-structure tests to delete or replace.
  - Test:     `tests/test_vib_start.py:242` - currently asserts parser includes `plan-structure`; rewrite to assert absence.
  - Test:     `tests/cli/test_vib_plan_cmd.py:1` - supported replacement path.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: rewritten CLI tests fail before implementation because `plan-structure` is still registered. Save output to `evidence/task-8-plan-structure-cli-red.txt`.
  - [ ] `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py tests/test_vib_start.py tests/cli/test_vib_plan_cmd.py` passes. Save output to `evidence/task-8-plan-structure-cli-green.txt`.
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli plan-structure "OAuth"` exits nonzero with invalid choice/usage. Save output to `evidence/task-8-plan-structure-error.txt`.
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli plan "예약 앱" --template-only --json` exits 0 and outputs JSON with `"ok": true`. Save output to `evidence/task-8-vib-plan-smoke.json`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: plan-structure command is gone while vib plan remains
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY'
              from typing import Any, cast
              from vibelign.cli.vib_cli import build_parser
              parser = build_parser()
              sub = cast(Any, next(a for a in parser._actions if getattr(a, "choices", None)))
              commands = set(sub.choices)
              assert "plan-structure" not in commands
              assert "plan" in commands
              print("ok")
              PY
    Expected: Prints `ok` and exits 0.
    Evidence: evidence/task-8-plan-structure-choices.txt

  Scenario: supported vib plan still creates template JSON
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python -m vibelign.cli.vib_cli plan "예약 앱" --template-only --json > evidence/task-8-vib-plan-smoke.json 2>&1 && grep -F '"ok": true' evidence/task-8-vib-plan-smoke.json
    Expected: Command exits 0 and JSON includes `"ok": true`.
    Evidence: evidence/task-8-vib-plan-smoke.json
  ```

  Commit: YES | Message: `feat(cli): remove plan-structure command` | Files: [`vibelign/cli/cli_command_groups.py`, `vibelign/cli/cli_base.py`, `vibelign/commands/vib_plan_structure_cmd.py`, `vibelign/core/structure_planner.py`, `tests/test_structure_planner.py`, `tests/test_vib_start.py`, `tests/cli/test_legacy_surface.py`, `tests/test_vib_cli_surface.py`, `tests/cli/test_vib_plan_cmd.py`]

- [ ] 9. Migrate guard/precheck away from legacy structure-plan JSON

  What to do: Remove active reliance on `.vibelign/plans/{id}.json` and `load_active_plan_payload` for guard/precheck if it only exists for legacy `plan-structure`. Keep structure classification helpers such as `WINDOWS_SUBPROCESS_FLAGS`, ignored dirs, generated artifact detection, and production-path classification. Update guard/precheck messages to recommend `vib plan "<work>"` or the GUI planning room for high-structure changes. Keep guard’s ability to flag multi-file/new-production changes, but it must not require or validate legacy JSON plans. Update plan override/close modules/tests: remove them if unregistered dead legacy, or retarget wording only if they are still registered by supported `vib plan` lifecycle.
  Must NOT do: Do not weaken `vib guard` to pass high-risk structure changes silently. Do not delete shared `structure_policy` constants imported by start, doctor, checkpoint, project scan, or Windows subprocess code.

  Parallelization: Can parallel: YES | Wave 3 | Blocks: [11, 12, 13] | Blocked by: [8]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/commands/vib_guard_cmd.py:107` - plan-structure recommendation constant.
  - Pattern:  `vibelign/commands/vib_guard_cmd.py:115` - plan-structure planning messages.
  - Pattern:  `vibelign/commands/vib_guard_cmd.py:445` - guard loads active plan payload.
  - Pattern:  `vibelign/commands/vib_guard_cmd.py:586` - planning-required return path.
  - Pattern:  `vibelign/commands/vib_precheck_cmd.py:16` - imports `load_active_plan_payload`.
  - Pattern:  `vibelign/commands/vib_precheck_cmd.py:121` - tells users to run `vib plan-structure`.
  - Pattern:  `vibelign/core/structure_policy.py:332` - `load_active_plan_payload` legacy JSON loader.
  - Pattern:  `vibelign/mcp/mcp_state_store.py:73` - generic planning session helpers; preserve unless proven unused by supported planning room.
  - Pattern:  `vibelign/commands/vib_plan_override_cmd.py:45` - plan-structure guidance.
  - Pattern:  `vibelign/commands/vib_plan_close_cmd.py:23` - active structure-plan wording.
  - Test:     `tests/test_guard_planning.py:165` - planning-required tests currently expect `vib plan-structure`.
  - Test:     `tests/test_vib_precheck.py:208` - precheck expects `vib plan-structure`.
  - Test:     `tests/test_structure_policy.py:7` - legacy active-plan payload loader tests.
  - Test:     `tests/test_plan_lifecycle_cmds.py:1` - plan close/override tests.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: guard/precheck tests updated to expect `vib plan`/planning-room guidance and no legacy JSON validation fail before implementation. Save output to `evidence/task-9-guard-plan-red.txt`.
  - [ ] `uv run pytest tests/test_guard_planning.py tests/test_vib_precheck.py tests/test_structure_policy.py tests/test_plan_lifecycle_cmds.py` passes after implementation, with deleted legacy tests removed from the command if their files are deleted. Save output to `evidence/task-9-guard-plan-green.txt`.
  - [ ] A guard smoke with a new production file returns `planning_required` and mentions `vib plan`, not `plan-structure`. Save output to `evidence/task-9-guard-planning-required.json`.
  - [ ] `rg -n "plan-structure|load_active_plan_payload|active structure plan|활성 구조 계획|\\.vibelign/plans" vibelign/commands vibelign/core tests` returns no active matches except historical excluded docs or negative assertions. Save output to `evidence/task-9-plan-static.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: guard still flags structural work with replacement guidance
    Tool:     bash
    Steps:    tmp=$(mktemp -d); cp -R tests/benchmark/sample_project "$tmp/project"; cd "$tmp/project"; mkdir -p vibelign/core; printf 'def run():\n    return 1\n' > vibelign/core/new_feature.py; PYTHONPATH=/Users/usabatch/coding/VibeLign uv run --project /Users/usabatch/coding/VibeLign python -m vibelign.cli.vib_cli guard --json > /Users/usabatch/coding/VibeLign/evidence/task-9-guard-planning-required.json 2>&1; grep -F "planning_required" /Users/usabatch/coding/VibeLign/evidence/task-9-guard-planning-required.json; grep -F "vib plan" /Users/usabatch/coding/VibeLign/evidence/task-9-guard-planning-required.json; ! grep -F "plan-structure" /Users/usabatch/coding/VibeLign/evidence/task-9-guard-planning-required.json
    Expected: Guard reports planning required, points to `vib plan`, and does not mention `plan-structure`.
    Evidence: evidence/task-9-guard-planning-required.json

  Scenario: precheck no longer depends on legacy plan JSON
    Tool:     bash
    Steps:    uv run pytest tests/test_vib_precheck.py -k "planning_required or plan" > evidence/task-9-precheck-green.txt 2>&1
    Expected: Precheck tests pass with `vib plan` guidance and no legacy active-plan JSON dependency.
    Evidence: evidence/task-9-precheck-green.txt
  ```

  Commit: YES | Message: `refactor(guard): replace plan-structure gating with vib plan guidance` | Files: [`vibelign/commands/vib_guard_cmd.py`, `vibelign/commands/vib_precheck_cmd.py`, `vibelign/core/structure_policy.py`, `vibelign/commands/vib_plan_override_cmd.py`, `vibelign/commands/vib_plan_close_cmd.py`, `tests/test_guard_planning.py`, `tests/test_vib_precheck.py`, `tests/test_structure_policy.py`, `tests/test_plan_lifecycle_cmds.py`]

- [ ] 10. Remove GUI plan-structure command/card/help surface

  What to do: Remove GUI plan-structure metadata, accessor, card component, manual-list legacy entries, help/search aliases, and any guide lines that suggest `plan-structure` or `vib patch`. Sanitize persisted card-order values containing `"plan-structure"` so old GUI state does not throw or render blanks. Keep planning-room UI and `vib plan` integrations.
  Must NOT do: Do not remove `PlanningPersonaStatus` fallback named `legacyRequested`; that is unrelated compatibility unless a test proves it exposes `plan-structure`.

  Parallelization: Can parallel: YES | Wave 3 | Blocks: [12, 13] | Blocked by: [8]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/lib/commandData2.ts:82` - plan-structure command metadata block.
  - Pattern:  `vibelign-gui/src/lib/commands.ts:26` - `getPlanStructureCommand`.
  - Pattern:  `vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx:6` - imports accessor.
  - Pattern:  `vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx:143` - runs `plan-structure`.
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:195` - plan-structure help entry.
  - Pattern:  `vibelign-gui/src/lib/helpData.ts:360` - plan-structure search aliases.
  - Pattern:  `vibelign-gui/src/lib/commandData2.ts:358` - patch_get workflow line in GUI command data.
  - Pattern:  `vibelign-gui/src/lib/commandData2.ts:443` - target_file/target_anchor wording.
  - Pattern:  `vibelign-gui/src/lib/commandData2.ts:473` - patch_get safe edit flow.
  - Test:     `vibelign-gui/src/lib/legacySurface.test.ts:7` - expects plan-structure legacy metadata.
  - Test:     `vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx:33` - legacy badge expectations.
  - Test:     `vibelign-gui/src/pages/__tests__/Onboarding.input-bar.test.tsx:80` - beginner surface absence tests.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: rewritten GUI tests assert plan-structure metadata/accessors/cards are absent and fail before implementation. Save output to `evidence/task-10-gui-plan-structure-red.txt`.
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/components/home/__tests__/ManualCommandList.test.tsx src/pages/__tests__/Home.simple.test.tsx src/pages/__tests__/Onboarding.input-bar.test.tsx src/lib/helpData.test.ts` passes. Save output to `evidence/task-10-gui-plan-structure-tests.txt`.
  - [ ] `rg -n "PlanStructureCard|getPlanStructureCommand|plan-structure|patch_get|target_file|target_anchor|vib patch" vibelign-gui/src` returns no active matches except negative assertions. Save output to `evidence/task-10-gui-plan-structure-static.txt`.
  - [ ] Planning-room tests still pass. Save output to `evidence/task-10-planning-room-tests.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: GUI plan-structure command is absent and planning room remains
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts src/pages/planning
    Expected: Removed command tests and planning-room tests pass.
    Evidence: evidence/task-10-planning-room-tests.txt

  Scenario: stale saved plan-structure card id is ignored
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- --run src/components/home/__tests__/ManualCommandList.test.tsx src/pages/__tests__/Home.simple.test.tsx
    Expected: Tests pass with no plan-structure card, no blank card, and no thrown missing metadata error.
    Evidence: evidence/task-10-gui-plan-structure-tests.txt
  ```

  Commit: YES | Message: `feat(gui): remove plan-structure surface` | Files: [`vibelign-gui/src/lib/commandData2.ts`, `vibelign-gui/src/lib/commands.ts`, `vibelign-gui/src/components/cards/ai/PlanStructureCard.tsx`, `vibelign-gui/src/lib/helpData.ts`, `vibelign-gui/src/lib/legacySurface.test.ts`, `vibelign-gui/src/components/home/__tests__/ManualCommandList.test.tsx`, `vibelign-gui/src/pages/__tests__/Home.simple.test.tsx`, `vibelign-gui/src/pages/__tests__/Onboarding.input-bar.test.tsx`, `vibelign-gui/src/lib/helpData.test.ts`]

- [ ] 11. Remove active plan-structure guidance from docs and exported project rules

  What to do: Remove or replace active `plan-structure` guidance in quickstart/manual/wiki/readme/exported rules. The replacement is `vib plan "<idea>" --template-only` for deterministic template generation, full `vib plan "<idea>"` for agent-assisted planning, and GUI planning room for users who prefer the app. Update docs tests to assert no active `plan-structure` guidance remains. Keep historical release notes/research docs.
  Must NOT do: Do not remove `vib plan` docs or planning-room docs. Do not delete historical `plans/spec-pr3-*`/`spec-pr7-*` files.

  Parallelization: Can parallel: YES | Wave 3 | Blocks: [12, 13] | Blocked by: [8, 9]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/MANUAL.md:572` - manual `vib plan-structure` section.
  - Pattern:  `vibelign/commands/vib_manual_cmd.py:971` - manual command data for plan-structure.
  - Pattern:  `vibelign/commands/vib_manual_cmd.py:1578` - manual category lists `patch`, `plan-structure`.
  - Pattern:  `AI_DEV_SYSTEM_SINGLE_FILE.md:314` - CLI fallback references `vib patch`; nearby rules also mention patch command flow.
  - Pattern:  `VibeLign_QUICKSTART.md:252` - quickstart command table must point to current commands only.
  - Pattern:  `docs/wiki/command-guide.md:63` - legacy command map.
  - Test:     `tests/test_beginner_surface_docs.py:27` - currently expects manual marks patch/plan-structure as legacy; rewrite to absence/replacement.
  - Test:     `tests/cli/test_vib_plan_cmd.py:1` - supported `vib plan` docs smoke.

  Acceptance criteria (agent-executable only):
  - [ ] TDD RED captured: docs tests expecting no active `plan-structure` fail before implementation. Save output to `evidence/task-11-docs-plan-structure-red.txt`.
  - [ ] `uv run pytest tests/test_beginner_surface_docs.py tests/cli/test_vib_plan_cmd.py` passes. Save output to `evidence/task-11-docs-plan-structure-green.txt`.
  - [ ] `rg -n "plan-structure|vib patch|patch_get|CodeSpeak|target_anchor" AGENTS.md AI_DEV_SYSTEM_SINGLE_FILE.md VibeLign_QUICKSTART.md docs/MANUAL.md docs/wiki vibelign/commands/export_cmd.py vibelign/commands/vib_manual_cmd.py` returns no active matches except negative assertions. Save output to `evidence/task-11-docs-plan-structure-static.txt`.
  - [ ] `PYTHONPATH=. uv run python -m vibelign.cli.vib_cli manual --help` and `rules --help` still run. Save output to `evidence/task-11-manual-rules-help.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: active docs point to vib plan, not plan-structure
    Tool:     bash
    Steps:    uv run pytest tests/test_beginner_surface_docs.py > evidence/task-11-docs-plan-structure-green.txt 2>&1
    Expected: Docs tests pass and active docs contain current `vib plan` guidance without `plan-structure`.
    Evidence: evidence/task-11-docs-plan-structure-green.txt

  Scenario: manual and rules commands remain available
    Tool:     bash
    Steps:    { PYTHONPATH=. uv run python -m vibelign.cli.vib_cli manual --help; PYTHONPATH=. uv run python -m vibelign.cli.vib_cli rules --help; } > evidence/task-11-manual-rules-help.txt 2>&1
    Expected: Both commands exit 0 and display help.
    Evidence: evidence/task-11-manual-rules-help.txt
  ```

  Commit: YES | Message: `docs(plan): replace plan-structure guidance` | Files: [`AGENTS.md`, `AI_DEV_SYSTEM_SINGLE_FILE.md`, `VibeLign_QUICKSTART.md`, `README.md`, `README.ko.md`, `docs/MANUAL.md`, `docs/wiki/command-guide.md`, `docs/wiki/getting-started.md`, `docs/wiki/core-workflow.md`, `docs/wiki/index.md`, `vibelign/commands/export_cmd.py`, `vibelign/commands/vib_manual_cmd.py`, `tests/test_beginner_surface_docs.py`, `tests/cli/test_vib_plan_cmd.py`]

- [ ] 12. Static cleanup of stale tests/imports/fixtures

  What to do: Run a full static search for removed names and resolve remaining active-code matches. Delete obsolete tests/fixtures that exclusively covered removed patch/CodeSpeak/plan-structure behavior. Update import-resolver examples only if they are active expectations rather than historical examples. Keep historical docs excluded by scope and unrelated generic `patch` terminology.
  Must NOT do: Do not paper over remaining active imports with broad ignores. Do not delete test coverage for preserved workflows.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [13] | Blocked by: [7, 8, 9, 10, 11]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `tests/test_import_resolver.py:77` - uses `vibelign.core.codespeak` as resolver fixture; decide whether to update to a current module.
  - Pattern:  `vibelign/core/import_resolver.py:49` - docstring uses CodeSpeak example.
  - Pattern:  `vibelign/core/memory/freshness.py:83` - patch_apply count heuristic may be stale after MCP removal.
  - Pattern:  `tests/test_memory_freshness.py:227` - patch_apply memory freshness tests.
  - Pattern:  `tests/test_gui_cli_contracts.py:267` - mentions `mcp patch_apply`.
  - Pattern:  `tests/fixtures/tokenizer_goldens/*.expected.json` - source fields point at `patch_suggester.py`.
  - Pattern:  `vibelign/core/structure_policy.py:186` - may still classify `vibelign/patch/` as production after package removal.
  - Test:     `tests/test_mcp_tool_snapshot.py:73` - final MCP snapshot.
  - Test:     `vibelign-gui/src/lib/helpData.test.ts:6` - GUI help surface.

  Acceptance criteria (agent-executable only):
  - [ ] `rg -n "patch_get|patch_apply|doctor_patch|CodeSpeak|codespeak|patch_suggester|strict_patch|vibelign\\.patch|plan-structure|target_file|target_anchor|PatchCard|PlanStructureCard|getPatchCommand|getPlanStructureCommand" vibelign tests vibelign-gui/src AGENTS.md AI_DEV_SYSTEM_SINGLE_FILE.md VibeLign_QUICKSTART.md docs/MANUAL.md docs/wiki README.md README.ko.md` has no active matches except negative assertions or explicitly listed historical notes. Save output to `evidence/task-12-static-cleanup-scan.txt`.
  - [ ] `uv run pytest tests/test_import_resolver.py tests/test_memory_freshness.py tests/test_gui_cli_contracts.py tests/test_mcp_tool_snapshot.py` passes. Save output to `evidence/task-12-static-cleanup-pytest.txt`.
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/helpData.test.ts src/lib/legacySurface.test.ts` passes. Save output to `evidence/task-12-static-cleanup-gui.txt`.
  - [ ] `PYTHONPATH=. uv run python - <<'PY'` walks all importable `vibelign` modules excluding optional GUI/runtime bundles and fails on any import error caused by removed modules. Save output to `evidence/task-12-import-walk.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: no active references to removed names remain
    Tool:     bash
    Steps:    rg -n "patch_get|patch_apply|doctor_patch|CodeSpeak|codespeak|patch_suggester|strict_patch|vibelign\\.patch|plan-structure|target_file|target_anchor|PatchCard|PlanStructureCard|getPatchCommand|getPlanStructureCommand" vibelign tests vibelign-gui/src AGENTS.md AI_DEV_SYSTEM_SINGLE_FILE.md VibeLign_QUICKSTART.md docs/MANUAL.md docs/wiki README.md README.ko.md > evidence/task-12-static-cleanup-scan.txt || true
    Expected: Output contains only negative assertions or explicitly approved historical notes recorded in the evidence file header.
    Evidence: evidence/task-12-static-cleanup-scan.txt

  Scenario: import walk catches stale deleted-module imports
    Tool:     bash
    Steps:    PYTHONPATH=. uv run python - <<'PY' > evidence/task-12-import-walk.txt 2>&1
              import importlib, pkgutil, vibelign
              failures = []
              for mod in pkgutil.walk_packages(vibelign.__path__, vibelign.__name__ + "."):
                  name = mod.name
                  if "vib-runtime" in name or name.startswith("vibelign._bundled"):
                      continue
                  try:
                      importlib.import_module(name)
                  except Exception as exc:
                      failures.append((name, repr(exc)))
              if failures:
                  for item in failures:
                      print(item)
                  raise SystemExit(1)
              print("ok")
              PY
    Expected: Prints `ok`; no stale import of removed modules.
    Evidence: evidence/task-12-import-walk.txt
  ```

  Commit: YES | Message: `chore(cleanup): remove stale legacy references` | Files: [`vibelign/core/import_resolver.py`, `vibelign/core/memory/freshness.py`, `vibelign/core/structure_policy.py`, `tests/test_import_resolver.py`, `tests/test_memory_freshness.py`, `tests/test_gui_cli_contracts.py`, `tests/fixtures/tokenizer_goldens/`, `tests/NOTES.md`, `vibelign-gui/src/lib/helpData.test.ts`, `vibelign-gui/src/lib/legacySurface.test.ts`]

- [ ] 13. End-to-end preserved-workflow regression sweep

  What to do: Run the preserved CLI, MCP, docs, and GUI smoke matrix after all removals. Fix only regressions caused by PR8. Capture a single evidence bundle summarizing command outputs, test logs, and static scans. Ensure current branch diff contains only PR8 removal files and no unrelated `.omo/**` or `.omc/**` churn unless produced intentionally as evidence outside commit scope.
  Must NOT do: Do not re-add removed legacy shims to make tests pass. Do not broaden scope into unrelated GUI redesign or historical docs cleanup.

  Parallelization: Can parallel: NO | Wave 4 | Blocks: [final] | Blocked by: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `pyproject.toml:32` - supported entry points: `vibelign`, `vib`, `vibelign-mcp`.
  - Pattern:  `vibelign/cli/vib_cli.py:73` - parser construction for supported command smoke.
  - Pattern:  `tests/test_mcp_tool_snapshot.py:73` - final MCP tool list.
  - Pattern:  `tests/cli/test_vib_plan_cmd.py:20` - `vib plan` JSON output test.
  - Pattern:  `vibelign-gui/src/App.tsx:61` - GUI pages include home/manual/docs/code/doctor/backups/settings/planning.
  - Test:     `tests/test_mcp_anchor_read_content.py` - preserve anchor read content.
  - Test:     `tests/test_mcp_project_map_get.py` - preserve project map MCP tool.
  - Test:     `tests/test_mcp_checkpoint_handlers.py` - preserve checkpoint tools.
  - Test:     `tests/test_checkpoint_cmd_wrapper.py` - preserve checkpoint CLI.
  - Test:     `tests/test_doctor_cmd_wrapper.py` - preserve doctor CLI.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest tests/cli/test_legacy_surface.py tests/test_vib_cli_surface.py tests/cli/test_vib_plan_cmd.py tests/test_beginner_surface_docs.py tests/test_mcp_tool_snapshot.py tests/test_mcp_anchor_read_content.py tests/test_mcp_project_map_get.py tests/test_mcp_checkpoint_handlers.py tests/test_checkpoint_cmd_wrapper.py tests/test_doctor_cmd_wrapper.py tests/test_guard_planning.py tests/test_vib_precheck.py tests/test_recovery_agent.py tests/test_mcp_recovery_handlers.py` passes. Save output to `evidence/task-13-python-regression.txt`.
  - [ ] `cd vibelign-gui && npm test -- --run src/lib/legacySurface.test.ts src/lib/helpData.test.ts src/pages/__tests__/Home.simple.test.tsx src/pages/__tests__/Onboarding.input-bar.test.tsx src/components/home/__tests__/ManualCommandList.test.tsx` passes. Save output to `evidence/task-13-gui-regression.txt`.
  - [ ] Direct CLI smoke for `start --help`, `checkpoint --help`, `undo --help`, `history --help`, `doctor --help`, `guard --help`, `anchor --help`, `manual --help`, `rules --help`, `plan "예약 앱" --template-only --json` passes. Save output to `evidence/task-13-cli-smoke.txt`.
  - [ ] Direct negative smoke for `patch`, `plan-structure`, `bench --patch` exits nonzero. Save output to `evidence/task-13-negative-smoke.txt`.
  - [ ] Final static scan shows no active removed names. Save output to `evidence/task-13-static-scan.txt`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: preserved CLI workflows still respond
    Tool:     bash
    Steps:    { for cmd in start checkpoint undo history doctor guard anchor manual rules; do PYTHONPATH=. uv run python -m vibelign.cli.vib_cli "$cmd" --help >/dev/null || exit 1; done; PYTHONPATH=. uv run python -m vibelign.cli.vib_cli plan "예약 앱" --template-only --json; } > evidence/task-13-cli-smoke.txt 2>&1
    Expected: All help commands exit 0; `vib plan` emits JSON with `"ok": true`.
    Evidence: evidence/task-13-cli-smoke.txt

  Scenario: removed CLI workflows fail
    Tool:     bash
    Steps:    { set +e; for args in 'patch x' 'plan-structure x' 'bench --patch'; do PYTHONPATH=. uv run python -m vibelign.cli.vib_cli $args >/tmp/pr8-neg.out 2>&1; code=$?; echo "$args -> $code"; test "$code" -ne 0 || exit 1; cat /tmp/pr8-neg.out; done; } > evidence/task-13-negative-smoke.txt 2>&1
    Expected: All removed commands/flags exit nonzero.
    Evidence: evidence/task-13-negative-smoke.txt
  ```

  Commit: YES | Message: `test(regression): verify legacy removal and preserved workflows` | Files: [`tests/**`, `vibelign-gui/src/**/*.test.ts`, `vibelign-gui/src/**/*.test.tsx`, `evidence/task-13-*`]

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
- Reference the plan file path in the final commit footer: `Plan: plans/pr8-legacy-removal.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
