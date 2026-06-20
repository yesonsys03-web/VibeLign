# Task 9 Evidence Matrix

| Scenario | Invocation | Binary observable | Artifact | Status | Note |
| --- | --- | --- | --- | --- | --- |
| CLI sparse preflight | uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --emit-model --json | JSON ok:true, quality warning/block, missing_evidence finding | .omo/evidence/report-writing-quality/task-9-cli-sparse-preflight.json | PASS | observable matched |
| CLI complete preflight | uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --emit-model --json | JSON ok:true, quality readiness ready | .omo/evidence/report-writing-quality/task-9-cli-complete-preflight.json | PASS | observable matched |
| CLI sparse assist | uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --assist-missing --json | JSON ok:true, assistance has user-visible suggestions/questions | .omo/evidence/report-writing-quality/task-9-cli-sparse-assist.json | PASS | observable matched |
| CLI complete visual cards | uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --visual-cards --json | JSON ok:true, 3-6 cards, prompts include no readable text in image | .omo/evidence/report-writing-quality/task-9-cli-complete-visual-cards.json | PASS | observable matched |
| GUI complete generate | (cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx -t 'quality_complete sourcePath opens ReportComposer and generates preview') | Vitest reports a passed complete sourcePath preview test | .omo/evidence/report-writing-quality/task-9-gui-complete-generate.txt | PASS | vitest reports passed tests |
| GUI sparse assistance confirmation | (cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ExportReportModal.quality.test.tsx src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx) | Vitest reports passed assistance confirmation tests | .omo/evidence/report-writing-quality/task-9-gui-sparse-assist-confirmation.txt | PASS | vitest reports passed tests |

All matrix entries were refreshed during Todo 9 execution. Vitest logs must report passed tests; skipped-only logs are not accepted.
