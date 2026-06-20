# API-Free Card-News Finalization

## TL;DR
> Summary:      Finish the card-news flow after draft generation without image APIs: approved cards are persisted under `.vibelign/reports/card-news`, rendered to standalone HTML, and opened from the GUI.
> Deliverables:
> - `vib report-card-news <payload.json> --json` finalization command
> - provider-neutral approved-card JSON + HTML artifacts in `.vibelign/reports/card-news`
> - GUI finalize/open flow from the current card-news draft tab
> - RED-first, CLI/data, browser, regression, and cleanup evidence
> Effort:       Medium
> Risk:         Medium - touches Python report storage, CLI registration, React state, Tauri payload/open plumbing, and dirty GUI files.

## Scope
### Must have
- Preserve the current `vib report --visual-cards --json` draft flow and `provider-neutral-draft` semantics.
- Add an API-free finalization path that consumes edited/approved cards, rejects zero approved cards, writes JSON and HTML under `.vibelign/reports/card-news`, and returns machine-readable paths.
- Add GUI controls after draft generation: finalize approved cards, show saved path/count/error, and open the generated HTML with the existing opener pattern.
- Capture RED-first proof, CLI/data evidence, browser surface evidence, report generation regression, and cleanup receipts under `.omo/evidence/`.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must NOT add image generation, API keys, provider SDKs, network calls, remote assets, or hidden provider fallback.
- Must NOT mark unapproved cards as persisted output.
- Must NOT rewrite current dirty tab work in `ReportComposer.tsx`, `ReportComposerLayout.tsx`, `ReportVisualCardsCompanion.tsx`, `ReportVisualCardsPanel.tsx`, or their tests.
- Must NOT weaken existing report output path containment or overwrite behavior.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest, Vitest, and browser automation against the GUI surface
- QA policy: every task has agent-executed scenarios
- Evidence: `.omo/evidence/task-<N>-<slug>.<ext>`

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (no dependencies):
- Task 1: Core finalizer schema, approval filter, storage, HTML renderer
- Task 3: GUI finalization client contract and temporary payload helper
- Task 6: Draft/report no-API regression lock

Wave 2 (after Wave 1):
- Task 2: CLI command registration and runtime wrapper depends [1]
- Task 4: GUI finalize/open controls depends [3]

Wave 3 (after Wave 2):
- Task 5: End-to-end evidence, browser QA, and cleanup receipts depends [2, 4, 6]

Critical path: Task 1 -> Task 2 -> Task 5

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 2, 5   | 3, 6                 |
| 2    | 1          | 5      | 4                    |
| 3    | none       | 4      | 1, 6                 |
| 4    | 3          | 5      | 2                    |
| 5    | 2, 4, 6    | none   | none                 |
| 6    | none       | 5      | 1, 3                 |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Core card-news finalizer

  What to do: Add a focused core module, e.g. `vibelign/core/reporting_cli/report_card_news.py`, that loads `report-visual-cards-v1`, validates card shape, filters `approved is True`, rejects empty approved output, writes approved-only JSON, renders escaped standalone HTML, and uses unique filenames under `.vibelign/reports/card-news`. Start by adding failing tests in `tests/core/reporting_cli/test_report_card_news.py`, then implement the smallest passing module.
  Must NOT do: Do not call `VisualImageProvider.generate`, add provider SDKs, use remote assets, embed unescaped user copy, or mutate the draft builder.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [2, 5] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/core/reporting_cli/report_visual_cards.py:50-68` - existing card payload shape to consume, not replace
  - Pattern:  `vibelign/core/reporting_cli/report_visual_cards.py:93-126` - draft builder/provider-neutral sidecar contract
  - Pattern:  `vibelign/core/reporting_cli/report_visual_cards.py:129-135` - API-free draft image metadata
  - Pattern:  `vibelign/core/reporting_cli/storage.py:13-30` - cross-platform project-relative path rejection
  - Pattern:  `vibelign/core/reporting_cli/storage.py:44-58` - unique output suffix behavior
  - Pattern:  `vibelign/core/reporting_cli/storage.py:61-99` - root containment and no-overwrite policy
  - Pattern:  `vibelign/core/reporting_cli/html_renderer.py:30-44` - escape all report text in HTML
  - Test:     `tests/core/reporting_cli/test_report_visual_cards.py:66-150` - provider-neutral/no prompt leakage assertions
  - Test:     `tests/core/reporting_cli/test_storage.py:78-107` - unsafe path and symlink escape regression pattern

  Acceptance criteria (agent-executable only):
  - [ ] `pytest tests/core/reporting_cli/test_report_card_news.py -q` first fails before implementation and passes after implementation, with RED log saved.
  - [ ] Saved finalized JSON contains only approved cards and `provider: "provider-neutral-draft"`.
  - [ ] Saved HTML contains approved Korean overlay text and contains no `<script`, no `http://`, no `https://`, no `fake://`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: approved cards are saved and rendered
    Tool:     bash
    Steps:    pytest tests/core/reporting_cli/test_report_card_news.py -q | tee .omo/evidence/task-1-core-card-news.txt
    Expected: pytest exits 0 and evidence includes assertions for JSON path, HTML path, approved count, escaped Korean text, and no network/API strings
    Evidence: .omo/evidence/task-1-core-card-news.txt

  Scenario: zero approved cards fail closed
    Tool:     bash
    Steps:    pytest tests/core/reporting_cli/test_report_card_news.py -q -k "empty or zero or approved" | tee .omo/evidence/task-1-core-card-news-error.txt
    Expected: pytest exits 0 and verifies no `.vibelign/reports/card-news` output is created
    Evidence: .omo/evidence/task-1-core-card-news-error.txt
  ```

  Commit: YES | Message: `feat(report): finalize approved card-news artifacts` | Files: [`vibelign/core/reporting_cli/report_card_news.py`, `tests/core/reporting_cli/test_report_card_news.py`]

- [ ] 2. CLI command wrapper and parser registration

  What to do: Add `vibelign/commands/vib_report_card_news_cmd.py` and register top-level `report-card-news` in the report command group using the existing lazy command style. Support `payload` and `--json`; add `--force` only if core storage needs explicit overwrite control. Formalize or update the untracked RED seed `tests/cli/test_vib_report_card_news_finalize_cmd.py`.
  Must NOT do: Do not fold this into `vib report --visual-cards`; draft generation must remain optional sidecar only.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [5] | Blocked by: [1]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/cli/cli_report_command_groups.py:57-99` - report parser and `lazy_command` registration style
  - Pattern:  `vibelign/commands/vib_report_runtime.py:171-180` - JSON success payload style
  - Pattern:  `vibelign/commands/vib_report_runtime.py:196-202` - JSON error + `SystemExit(1)` style
  - Pattern:  `vibelign/cli/vib_cli.py:25-92` - parser build and command registration path
  - Test:     `tests/cli/test_vib_report_visual_cards_cmd.py:29-67` - parser and report visual-card CLI tests
  - Test:     `tests/cli/test_vib_report_card_news_finalize_cmd.py:46-88` - existing untracked RED seed; preserve if user-created and adapt carefully

  Acceptance criteria (agent-executable only):
  - [ ] `pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -q` first proves missing command/import, then passes after implementation.
  - [ ] `python -m vibelign.cli.vib_cli report-card-news cards.json --json` returns `{ok:false,...}` for malformed/missing payload without traceback.
  - [ ] `vib report --visual-cards --json` output remains unchanged and does not create `card-news` artifacts.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: CLI finalizes approved payload
    Tool:     bash
    Steps:    pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -q | tee .omo/evidence/task-2-cli-card-news.txt
    Expected: pytest exits 0; JSON response includes ok, html_path, json_path, approved_count; both files exist under `.vibelign/reports/card-news`
    Evidence: .omo/evidence/task-2-cli-card-news.txt

  Scenario: CLI rejects missing/malformed payload
    Tool:     bash
    Steps:    pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -q -k "rejects or malformed or empty" | tee .omo/evidence/task-2-cli-card-news-error.txt
    Expected: pytest exits 0; errors are JSON `{ok:false}` and no output dir is created for empty approved cards
    Evidence: .omo/evidence/task-2-cli-card-news-error.txt
  ```

  Commit: YES | Message: `feat(cli): add report card-news finalization command` | Files: [`vibelign/commands/vib_report_card_news_cmd.py`, `vibelign/cli/cli_report_command_groups.py`, `tests/cli/test_vib_report_card_news_finalize_cmd.py`]

- [ ] 3. GUI finalization client contract

  What to do: Extend `vibelign-gui/src/lib/vib/reportVisualCards.ts` with a typed finalize result parser and `finalizeReportVisualCards(cwd, payload)` that writes a temporary JSON payload, runs `report-card-news <payload> --json`, parses paths/count/errors, and removes the temp payload in `finally`. If reusing `write_report_render_payload`, widen `vibelign-gui/src/lib/vib/reportRenderPayload.ts` from `EmitPayload` to `unknown` or add a generic wrapper.
  Must NOT do: Do not pass raw JSON as a CLI argument, do not keep temp payloads after success/failure, and do not open files from this library layer.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [4] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/lib/vib/reportVisualCards.ts:98-128` - parser + `runVib` error handling style
  - Pattern:  `vibelign-gui/src/lib/vib/reportVisualCards.ts:110-112` - approved-card filter helper
  - Pattern:  `vibelign-gui/src/lib/vib/report.ts:236-274` - temp payload write/run/remove `finally` style
  - Pattern:  `vibelign-gui/src/lib/vib/reportRenderPayload.ts:1-14` - existing Tauri temp payload bridge
  - Pattern:  `vibelign-gui/src-tauri/src/commands/report_render_payload.rs:31-57` - temp payload creation/removal constraints
  - Test:     `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts:41-76` - existing visual-card client tests

  Acceptance criteria (agent-executable only):
  - [ ] `cd vibelign-gui && npm test -- src/lib/vib/__tests__/reportVisualCards.test.ts --runInBand` passes after RED-first additions.
  - [ ] Tests verify `runVib(["report-card-news", tempPath, "--json"], cwd)` and temp cleanup on both success and error.
  - [ ] Tests verify parser rejects `{ok:false}` and malformed stdout with Korean user-facing error text.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: GUI client finalizes through temp payload
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- src/lib/vib/__tests__/reportVisualCards.test.ts | tee ../.omo/evidence/task-3-gui-client.txt
    Expected: Vitest exits 0 and asserts CLI args, parsed html_path/json_path, approved_count, and temp cleanup
    Evidence: .omo/evidence/task-3-gui-client.txt

  Scenario: GUI client cleans temp payload on failure
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- src/lib/vib/__tests__/reportVisualCards.test.ts -t "cleans" | tee ../.omo/evidence/task-3-gui-client-error.txt
    Expected: Vitest exits 0 and mocked remove helper is called after failed CLI/parse path
    Evidence: .omo/evidence/task-3-gui-client-error.txt
  ```

  Commit: YES | Message: `feat(gui-report): add card-news finalize client` | Files: [`vibelign-gui/src/lib/vib/reportVisualCards.ts`, `vibelign-gui/src/lib/vib/reportRenderPayload.ts`, `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`]

- [ ] 4. GUI finalize/open controls

  What to do: Add a finalize button/status/open result flow to `ReportVisualCardsCompanion.tsx` using the approved edited cards emitted by `ReportVisualCardsPanel`. The button must be disabled or fail with a clear message when zero cards are approved. Reuse the existing `openPath` pattern for the generated HTML. Preserve current tab layout and existing dirty UI changes.
  Must NOT do: Do not restyle the workspace tabs, do not remove regenerate/edit/delete controls, and do not auto-finalize when a draft is generated.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [5] | Blocked by: [3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx:23-46` - draft payload/approved/error state
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx:55-65` - current draft request and approved count surface
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx:59-70` - card state and approved-card export callback
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx:143-152` - approve/delete controls to preserve
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportComposerExportBox.tsx:66-76` - `openPath` error handling pattern
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportComposerLayout.tsx:52-79` - current dirty card-news tab surface
  - Test:     `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx:92-148` - current draft/edit/approve tests
  - Test:     `vibelign-gui/src/pages/__tests__/ReportView.test.tsx:178-188` - report tab entry test

  Acceptance criteria (agent-executable only):
  - [ ] `cd vibelign-gui && npm test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/pages/__tests__/ReportView.test.tsx` passes.
  - [ ] Tests verify editing a card before approve/finalize persists edited title/body/caption into the finalize payload.
  - [ ] Tests verify zero approved cards show/retain a Korean error and do not call finalize/open.
  - [ ] Tests verify clicking open calls `openPath(html_path)`.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: user edits, approves, finalizes, opens
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx -t "finalizes" | tee ../.omo/evidence/task-4-gui-finalize.txt
    Expected: Vitest exits 0 and verifies finalized payload contains edited approved cards and openPath receives returned HTML path
    Evidence: .omo/evidence/task-4-gui-finalize.txt

  Scenario: no approved cards cannot finalize
    Tool:     bash
    Steps:    cd vibelign-gui && npm test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx -t "approved" | tee ../.omo/evidence/task-4-gui-finalize-error.txt
    Expected: Vitest exits 0 and verifies no finalize call when approved count is zero
    Evidence: .omo/evidence/task-4-gui-finalize-error.txt
  ```

  Commit: YES | Message: `feat(gui-report): finalize approved card-news drafts` | Files: [`vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`, `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx`, `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx`, `vibelign-gui/src/pages/__tests__/ReportView.test.tsx`]

- [ ] 5. End-to-end evidence and browser surface

  What to do: Run a real CLI happy path in a temp project, inspect the generated JSON/HTML files, start the GUI dev server, drive the card-news tab in a browser, finalize approved cards, and capture screenshot/action evidence. If no existing route can deep-link the report view, add a temporary QA harness only under `.omo/evidence/` or use component tests plus dev-server page; do not ship test-only UI.
  Must NOT do: Do not commit `.vibelign/reports` artifacts, `.omo/evidence`, or temp QA harness files.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [] | Blocked by: [2, 4, 6]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign-gui/package.json:6-15` - build/test/dev scripts
  - Pattern:  `vibelign-gui/src/lib/vib/core.ts:27-42` - GUI CLI bridge environment
  - Pattern:  `vibelign-gui/src/pages/__tests__/ReportView.test.tsx:178-188` - expected card-news tab user path
  - Pattern:  `.omo/ulw-loop/report-card-news-complete/goals.json:18-38` - prior bootstrap evidence targets for browser, empty-approved, regression
  - Test:     `tests/fixtures/reporting_cli/quality_complete.md` - existing complete report fixture used by current tests

  Acceptance criteria (agent-executable only):
  - [ ] CLI happy path writes `.vibelign/reports/card-news/*.json` and `*.html`, and `grep` confirms approved text is present while unapproved text is absent.
  - [ ] Browser evidence includes a screenshot where card-news finalization status and HTML path are visible.
  - [ ] Evidence includes no network/API dependency proof from generated HTML and command logs.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: real CLI/data artifact
    Tool:     bash
    Steps:    mkdir -p .omo/evidence && pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -q | tee .omo/evidence/task-5-cli-data.txt
    Expected: pytest exits 0 and evidence includes saved JSON/HTML path assertions
    Evidence: .omo/evidence/task-5-cli-data.txt

  Scenario: browser finalize surface
    Tool:     playwright(real Chrome)
    Steps:    cd vibelign-gui && npm run dev -- --host 127.0.0.1; open `http://127.0.0.1:<port>`; navigate to report view for `tests/fixtures/reporting_cli/quality_complete.md`; click `카드뉴스`; click `카드뉴스 초안 만들기`; approve at least one card; click `카드뉴스 확정`; screenshot the visible saved HTML path
    Expected: status contains `카드뉴스 결과물` or equivalent saved-success text, and the visible path ends with `.vibelign/reports/card-news/*.html`
    Evidence: .omo/evidence/task-5-browser-finalize.png and .omo/evidence/task-5-browser-finalize.json
  ```

  Commit: NO | Message: `n/a` | Files: []

- [ ] 6. Regression lock and cleanup receipts

  What to do: Lock adjacent behavior: existing report generation, `--visual-cards` draft JSON, no provider/API usage, and dirty-worktree preservation. Run focused tests and static scans, then save cleanup receipts showing temp payloads removed and generated artifacts not staged.
  Must NOT do: Do not stage or commit `.omo/evidence`, `.vibelign/reports`, `node_modules`, or unrelated dirty tab changes unless they are intentionally part of Tasks 3-4.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [5] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `vibelign/commands/vib_report_runtime.py:151-180` - existing report render + optional visual card sidecar
  - Test:     `tests/cli/test_vib_report_cmd.py:38-55` - report HTML generation regression
  - Test:     `tests/cli/test_vib_report_visual_cards_cmd.py:51-67` - visual-card sidecar regression
  - Test:     `tests/core/reporting_cli/test_report_visual_cards.py:133-150` - no provider/fake/Korean prompt leakage
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportComposer.tsx:47-75` - existing dirty tab-related state to preserve
  - Pattern:  `vibelign-gui/src/components/plan-doc/ReportComposerLayout.tsx:43-79` - existing dirty tab layout to preserve

  Acceptance criteria (agent-executable only):
  - [ ] `pytest tests/cli/test_vib_report_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/core/reporting_cli/test_report_visual_cards.py -q` passes.
  - [ ] `cd vibelign-gui && npm test -- src/lib/vib/__tests__/reportVisualCards.test.ts src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/pages/__tests__/ReportView.test.tsx` passes.
  - [ ] `rg -n "openai|anthropic|replicate|stability|http://|https://|fetch\\(|axios|image generation" vibelign vibelign-gui/src` shows no new API dependency in card-news finalization files.
  - [ ] `git status --short` receipt shows only intended source/test changes plus pre-existing dirty files; no generated report/evidence artifacts are staged.

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: report generation and draft-card regressions pass
    Tool:     bash
    Steps:    pytest tests/cli/test_vib_report_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/core/reporting_cli/test_report_visual_cards.py -q | tee .omo/evidence/task-6-regression.txt
    Expected: pytest exits 0 and existing draft sidecar remains provider-neutral
    Evidence: .omo/evidence/task-6-regression.txt

  Scenario: cleanup and no API dependency receipt
    Tool:     bash
    Steps:    { rg -n "openai|anthropic|replicate|stability|http://|https://|fetch\\(|axios" vibelign/core/reporting_cli vibelign/commands/vib_report_card_news_cmd.py vibelign-gui/src/lib/vib/reportVisualCards.ts vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx || true; git status --short; } | tee .omo/evidence/task-6-cleanup.txt
    Expected: output contains no new card-news API dependency, no temp payload files, and no staged `.vibelign/reports` artifacts
    Evidence: .omo/evidence/task-6-cleanup.txt
  ```

  Commit: YES | Message: `test(report): lock card-news finalization regressions` | Files: [`tests/cli/test_vib_report_cmd.py`, `tests/cli/test_vib_report_visual_cards_cmd.py`, `tests/core/reporting_cli/test_report_visual_cards.py`, `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`, `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx`, `vibelign-gui/src/pages/__tests__/ReportView.test.tsx`]

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
- Reference the plan file path in the final commit footer: `Plan: .omo/plans/api-free-card-news-finalization.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
