# Report Card News Complete Code Review

codeQualityStatus: BLOCK
recommendation: REQUEST_CHANGES
reportPath: .omo/evidence/report-card-news-complete-code-review.md

## Scope Reviewed

- `vibelign/core/reporting_cli/report_card_news_export.py`
- `vibelign/commands/vib_report_card_news_cmd.py`
- `vibelign/cli/cli_report_command_groups.py`
- `vibelign-gui/src/lib/vib/reportVisualCards.ts`
- `vibelign-gui/src/lib/vib/reportRenderPayload.ts`
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`
- `vibelign-gui/src/components/plan-doc/ReportComposerLayout.tsx`
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx`
- Focused Python and Vitest tests named in the review request.

## Skill Perspective Check

- Ran: loaded and applied `omo:programming` plus Python/TypeScript references before judging type safety, maintainability, and tests.
- Ran: loaded and applied `omo:remove-ai-slops` overfit/slop criteria before judging tests and production complexity.
- TypeScript perspective: clear for the focused TS/TSX files. `bun run .../check-no-excuse-rules.ts` with GUI `node_modules` reported no violations in 8 files; direct scan found no `as any`, `@ts-ignore`, or `@ts-expect-error`.
- Python perspective: not clear. The scoped Python test file fails basedpyright, and the Python no-excuse script still reports `object` annotations in focused Python/test files.
- Overfit/remove-ai-slops perspective: no deletion-only, tautological, or implementation-removal-only tests found in the focused tests. The blocker is not overfit hiding the original approved/symlink bugs; it is the remaining type/strictness failure in tests and annotations.

## CRITICAL

None.

## HIGH

1. `tests/cli/test_vib_report_card_news_finalize_cmd.py:54`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:74`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:100`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:117`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:139`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:155` - Scoped basedpyright is not clean when the new test file is included.

   Re-run command:

   `uv run basedpyright vibelign/core/reporting_cli/report_card_news_export.py vibelign/commands/vib_report_card_news_cmd.py vibelign/cli/cli_report_command_groups.py tests/cli/test_vib_report_card_news_finalize_cmd.py`

   Result: 5 errors and 11 warnings. The hard errors are `Namespace` not satisfying `ReportCardNewsArgs` at each direct `run_vib_report_card_news(_args(...))` call. Warnings include unused `write_text` return values and `Any` from `json.loads`/parser namespace access. Production-only basedpyright is clean, but the requested scope includes tests, so the supplied "basedpyright clean" claim is not verified.

2. `tests/cli/test_vib_report_card_news_finalize_cmd.py:11`, `tests/cli/test_vib_report_card_news_finalize_cmd.py:42`, `vibelign/cli/cli_report_command_groups.py:15`, `vibelign/core/reporting_cli/report_card_news_export.py:114` - The programming/no-excuse pass still fails on `object` annotations.

   Re-run command:

   `uv run python /Users/topsphinx/.codex/plugins/cache/sisyphuslabs/omo/4.11.1/skills/programming/scripts/python/check-no-excuse-rules.py vibelign/core/reporting_cli/report_card_news_export.py vibelign/commands/vib_report_card_news_cmd.py vibelign/cli/cli_report_command_groups.py tests/cli/test_vib_report_card_news_finalize_cmd.py`

   Result: 4 violations. This violates the explicit programming perspective requested for this review. `report_card_news_export.py:73` also uses `cast(JsonValue, json.loads(...))`, which is a programming-skill escape hatch at the JSON boundary even though the current runtime checks now prevent the earlier approved-coercion bug.

## MEDIUM

None.

## LOW

None.

## Verification Run

- PASS: `uv run pytest tests/cli/test_vib_report_card_news_finalize_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/core/reporting_cli/test_report_visual_cards.py tests/cli/test_vib_report_cmd.py -q` -> 27 passed.
- PASS: `uv run basedpyright vibelign/core/reporting_cli/report_card_news_export.py vibelign/commands/vib_report_card_news_cmd.py vibelign/cli/cli_report_command_groups.py` -> 0 errors, 0 warnings.
- FAIL: scoped basedpyright including `tests/cli/test_vib_report_card_news_finalize_cmd.py` -> 5 errors, 11 warnings.
- FAIL: Python programming no-excuse script over focused Python/test files -> 4 violations.
- PASS: `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/lib/vib/__tests__/reportVisualCards.test.ts src/pages/__tests__/ReportView.test.tsx` -> 3 files / 16 tests passed.
- PASS: `cd vibelign-gui && npm run build` -> build passed with existing chunk-size warnings.
- PASS: TypeScript no-excuse script over 8 focused TS/TSX files -> no violations.
- PASS: focused `git diff --check`.
- PASS by inspection/evidence: literal `approved is True` behavior, symlinked card-news output rejection, no production API/network calls, temp payload cleanup `finally`, modal and inline card-news surfaces, and browser QA artifact visibility/no-overflow.

## Blockers

- Make the new Python test file basedpyright-clean under the same scoped command used above; do not claim a clean type gate by excluding tests from the reviewed scope.
- Remove the remaining programming/no-excuse violations in the focused Python/test files, especially `object` annotations and the JSON-boundary cast/typing escape hatch.
