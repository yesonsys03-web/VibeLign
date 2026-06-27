# Todo 8 Final Confirmation Gate

recommendation: APPROVE

## originalIntent

Decide whether Todo 8 of `.omo/plans/report-writing-quality.md` can be marked complete. Todo 8 asks for optional visual card-news companion output for reports: backend 3-6 source-backed card planning, opt-in CLI JSON sidecar, provider-neutral image boundary with tests using fake providers only, and GUI preview/edit/approve/delete/regenerate controls with Korean copy as editable overlays instead of image prompt text.

## desiredOutcome

The user can keep normal report JSON unchanged, opt into `--visual-cards --json` when card planning is desired, and use the GUI report surface to explicitly request card drafts. The shipped behavior must keep generated-image prompts provider-neutral and text-free, preserve Korean report copy as editable HTML/CSS overlays, exclude deleted/rejected cards from export state, and pass the focused backend/CLI/GUI/build checks.

## userOutcomeReview

Confirmed. Current source and live probes satisfy the user-visible Todo 8 outcome:

- Backend planner returns 6 cards for the complete fixture with source refs and required risk/next-action/evidence coverage.
- Visual prompts include `no readable text in image`, contain no Hangul report copy, and do not hard-code `imagen2`.
- Normal report `--json` has no `visual_cards` sidecar; `--visual-cards --json` adds the sidecar only when requested.
- Production output is provider-neutral (`provider-neutral-draft`) with empty draft asset paths and no fake URLs.
- Fake provider behavior is confined to explicit test injection (`RecordingProvider`) and test payloads.
- GUI production wiring exists in `ReportComposer` via `ReportVisualCardsCompanion`, and the request is click-triggered through `카드뉴스 초안 만들기`.
- `ReportVisualCardsPanel` exposes editable Korean title/body/caption controls plus regenerate, approve/unapprove, and delete buttons; export state uses only approved remaining cards.

## checkedArtifactPaths

- `.omo/plans/report-writing-quality.md`
- `.omo/evidence/todo-8-final-code-review.md`
- `.omo/evidence/todo-8-code-review.md`
- `.omo/evidence/todo-8-post-fix-code-review.md`
- `.omo/evidence/todo-8-provider-fix-code-review.md`
- `.omo/evidence/report-writing-quality/task-8-doneclaim.txt`
- `.omo/evidence/report-writing-quality/task-8-post-fix-doneclaim.txt`
- `.omo/evidence/report-writing-quality/task-8-provider-fix-doneclaim.txt`
- `.omo/evidence/report-writing-quality/task-8-cli-test-split-doneclaim.txt`
- `.omo/evidence/report-writing-quality/task-8-provider-fix-visual-cards.json`
- `.omo/evidence/report-writing-quality/task-8-visual-qa.md`
- `.omo/evidence/report-writing-quality/task-8-manual-qa-matrix.md`
- `.omo/evidence/report-writing-quality/task-8-provider-fix-no-slop-check.txt`
- `.omo/evidence/report-writing-quality/task-8-cli-test-split-no-slop.txt`
- `.omo/evidence/report-writing-quality/task-8-visual-dom-snapshot.json`
- `vibelign/core/reporting_cli/report_visual_cards.py`
- `vibelign/commands/vib_report_cmd.py`
- `vibelign/cli/cli_command_groups.py`
- `tests/core/reporting_cli/test_report_visual_cards.py`
- `tests/cli/test_vib_report_cmd.py`
- `tests/cli/test_vib_report_visual_cards_cmd.py`
- `tests/cli/test_vib_report_assist_cmd.py`
- `vibelign-gui/src/lib/vib/reportVisualCards.ts`
- `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`
- `vibelign-gui/src/components/plan-doc/ReportComposer.tsx`
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx`
- `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx`

## directVerification

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest tests/core/reporting_cli/test_report_visual_cards.py tests/cli/test_vib_report_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/cli/test_vib_report_assist_cmd.py -q -o cache_dir=/tmp/vibelign-pytest-cache-todo8-final-gate` -> `23 passed`.
- `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/reportVisualCards.test.ts src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx --run` -> `2 passed`, `5 passed`.
- Temp live CLI probe using current source: normal JSON `normal_has_visual_cards=false`; opt-in provider `provider-neutral-draft`; `card_count=6`; `has_risk=true`; `has_next_action=true`; `prompt_hangul=false`; `fake_url=false`.
- `cd vibelign-gui && npm run build -- --outDir /tmp/vibelign-gui-todo8-final-gate-build` -> passed; Vite emitted only chunk-size warnings. Temporary output was removed.
- Current pure LOC: `report_visual_cards.py=240`, `test_report_visual_cards.py=73`, `test_vib_report_cmd.py=204`, `test_vib_report_visual_cards_cmd.py=56`, `test_vib_report_assist_cmd.py=66`, `reportVisualCards.ts=113`, `ReportVisualCardsCompanion.tsx=70`, `ReportVisualCardsPanel.tsx=164`, `ReportVisualCardsPanel.test.tsx=130`, `ReportComposer.tsx=191`. Legacy wiring residuals remain in `vib_report_cmd.py=254` and `cli_command_groups.py=849`, accepted/documented as non-blocking legacy wiring.

## slopAndOverfitReview

Direct `remove-ai-slops` / `programming` pass found no remaining Todo 8 blocker:

- No deletion-only test closure: removed shared CLI tests were moved into focused files, and the split-focused suite passes.
- No tautological prompt-only backend coverage: backend and CLI tests assert risk/next-action/evidence text, source refs, provider neutrality, empty/no fake asset URLs, and prompt safety.
- Fake provider is not production default; production no-provider path returns provider-neutral draft metadata.
- Regenerate test is behavior-focused around callback/candidate state and exported approved cards, not just a query-string mutation.
- New focused files are below 250 pure LOC. `report_visual_cards.py` is in the 200-250 warning band and should be split before future feature growth, but it is not over the gate.

## adversarialClasses

- stale_state: addressed by reading prior blocker reports and verifying current source/live probe; old fake-provider JSON artifacts are stale and not used as approval evidence.
- dirty_worktree: broad dirty/untracked worktree remains; user explicitly accepted this residual. Not a functional Todo 8 blocker.
- misleading_success_output: PASS reports were treated as untrusted; direct source inspection and live probes independently confirmed them.
- generated/cached artifacts: screenshots/DOM harness are partially stale for provider naming, but visual/CJK/gradient claims are supported by current component source and focused tests.
- malformed input/prompt safety: parser normalizes unknown/malformed payload fields; tests and live probe confirm text-free prompts, no Hangul prompt copy, no `imagen2`, and source refs.
- visual/CJK: visual QA screenshots and DOM show legible CJK overlays and no gradient; source uses editable inputs/textareas and `resize: "none"`.
- long command risk: GUI helper builds a short fixed `runVib(["report", planPath, "--type", reportType, "--visual-cards", "--json"], cwd)` command and does not pass full document text through React state.

## exactEvidenceGaps

- `.omo/evidence/report-writing-quality/task-8-manual-qa-matrix.md` is stale: it still reports fake-provider CLI output and a gradient/design FAIL from before later fixes.
- `.omo/evidence/report-writing-quality/task-8-visual-dom-snapshot.json` and screenshots use a stale fake-provider harness payload and fake asset paths. They remain useful for layout/CJK/gradient evidence only, not provider-boundary evidence.
- `.omo/evidence/report-writing-quality/task-8-provider-fix-no-slop-check.txt` contains a stale 261 LOC line for `tests/cli/test_vib_report_cmd.py`; the later split artifact and current LOC probe show it is now 204.
- `--visual-cards --json` still renders the normal report file before adding the sidecar. This is an accepted low-risk side effect for the current sidecar contract, not a Todo 8 functional blocker.
- Real image-provider integration is future work. Current production behavior is truthful provider-neutral draft output; tests use fake providers through explicit injection.
- VibeLign strict guard still has anchor/worktree residuals, including the new backend file. The user explicitly accepted proceeding despite this residual.

## blockers

None.

## verdict

confirmed
