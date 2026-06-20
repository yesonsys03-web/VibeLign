# Global Review QA - Report Writing Quality

Status: PASS
Timestamp: 2026-06-20 Asia/Seoul
Scope: read-only product QA; wrote only `global-review-qa-*` evidence artifacts under `.omo/evidence/report-writing-quality/`.

## Scenario Brainstorm

1. CLI sparse emit-model returns `ok:true`, quality `warn`, required missing-field findings, and default `assistance:not_requested`.
2. CLI complete emit-model returns quality `ok` and no required missing-field findings.
3. CLI long-source assist returns chunked `source_refs` in middle line ranges, not just head/tail.
4. CLI sparse assist returns `needs_user_input` with user-question or editable suggestion instead of fabricated facts.
5. CLI visual cards returns 3-6 provider-neutral cards with prompt safety and no Korean report copy in image prompts.
6. CLI HTML render creates an existing HTML artifact with expected Korean business content and selected options preserved.
7. CLI DOCX render creates a valid package with expected Korean content.
8. CLI PPTX render creates a valid package with expected Korean content.
9. GUI ReportView complete `sourcePath` opens real composer and reaches preview.
10. GUI ReportView sparse warning blocks preview until generate-anyway.
11. GUI quality panel assistance requires explicit accept/edit/reject before applying.
12. GUI visual-card panel keeps Korean copy as editable overlays and fake image layer separate.
13. GUI PDF wrapper renders HTML first and calls Tauri `export_report_pdf`, never backend `--format pdf`.
14. Current focused Vitest selectors run nonzero tests; stale zero-test selectors are recorded as failure, not pass.
15. `npm run build` confirms the GUI surface compiles after QA-relevant test execution.

## Environment

- `/usr/bin/python3 --version`: Python 3.9.6
- `uv run python --version`: Python 3.11.15
- Python QA used `uv run python` as required because the project uses Python >=3.10 syntax.

## manualQa

### surfaceEvidence

| scenario id | criterion reference | surface | exact invocation | verdict | artifactRefs |
|---|---|---|---|---|---|
| GQA-S01 | Sparse quality preflight | CLI JSON | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type work --emit-model --json > .omo/evidence/report-writing-quality/global-review-qa-cli-sparse-preflight.json` | PASS | A2, A10 |
| GQA-S02 | Complete quality preflight | CLI JSON | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --emit-model --json > .omo/evidence/report-writing-quality/global-review-qa-cli-complete-preflight.json` | PASS | A3, A10 |
| GQA-S03 | Sparse assist user input | CLI JSON | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_sparse.md --type proposal --assist-missing --json > .omo/evidence/report-writing-quality/global-review-qa-cli-sparse-assist.json` | PASS | A4, A10 |
| GQA-S04 | Long-source assist chunk refs | CLI JSON | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_long_2000.md --type work --assist-missing --json > .omo/evidence/report-writing-quality/global-review-qa-cli-long-assist.json` | PASS | A5, A10 |
| GQA-S05 | Visual cards provider-neutral output | CLI JSON | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --visual-cards --json > .omo/evidence/report-writing-quality/global-review-qa-cli-visual-cards.json` | PASS | A6, A10 |
| GQA-S06 | HTML render existence/content | CLI JSON and generated file | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format html --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/global-review-qa-cli-html-render.json` | PASS | A7, A10 |
| GQA-S07 | DOCX render existence/content | CLI JSON and generated package | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format docx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/global-review-qa-cli-docx-render.json` | PASS | A8, A10 |
| GQA-S08 | PPTX render existence/content | CLI JSON and generated package | `uv run python -m vibelign.cli.vib_cli report tests/fixtures/reporting_cli/quality_complete.md --type proposal --format pptx --theme satgat-proposal --author "팀장" --title-font-size 31 --heading-font-size 18 --body-font-size 14 --meta-font-size 10 --no-page-numbers --json --force > .omo/evidence/report-writing-quality/global-review-qa-cli-pptx-render.json` | PASS | A9, A10 |
| GQA-S09 | Relevant Python CLI tests | Python test runner | `uv run python -m pytest tests/cli/test_vib_report_assist_cmd.py tests/cli/test_vib_report_visual_cards_cmd.py tests/cli/test_vib_report_format_parity.py tests/cli/test_vib_report_render_payload.py -v` | PASS, 23 passed | A11 |
| GQA-S10 | Stale zero-test selector check | GUI Vitest/jsdom | `cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx src/components/plan-doc/__tests__/ExportReportModal.test.tsx -t "quality_sparse AI assistance requires user confirmation"` | FAIL_ZERO_TESTS_RAN; not counted as pass | A12 |
| GQA-S11 | GUI ReportView sparse/complete | GUI Vitest/jsdom | `cd vibelign-gui && npm run test -- src/pages/__tests__/ReportView.test.tsx -t "quality_complete sourcePath opens ReportComposer and generates preview|quality panel warning blocks preview until generate-anyway"` | PASS, 2 passed | A13 |
| GQA-S12 | GUI quality panel assist/long refs | GUI Vitest/jsdom | `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportQualityPanel.test.tsx -t "requires confirmation before applying assistance|renders long-source line refs without narrow overflow styles"` | PASS, 2 passed | A14 |
| GQA-S13 | GUI visual-card panel | GUI Vitest/jsdom | `cd vibelign-gui && npm run test -- src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx -t "keeps Korean copy as editable overlays|production ReportComposer requests and previews visual cards"` | PASS, 2 passed | A15 |
| GQA-S14 | GUI PDF wrapper | GUI Vitest/jsdom | `cd vibelign-gui && npm run test -- src/lib/vib/__tests__/report.test.ts -t "generateReportPdf uses html render then export_report_pdf"` | PASS, 1 passed | A16 |
| GQA-S15 | GUI build | npm build | `cd vibelign-gui && npm run build` | PASS with existing large-chunk warning | A17 |

### adversarialCases

| scenario id | criterion reference | adversarial class | expected behavior | verdict | artifactRefs |
|---|---|---|---|---|---|
| GQA-A01 | Python fallback requirement | System `/usr/bin/python3` is Python 3.9.6 while project requires >=3.10 | Use `uv run python` for Python CLI/tests and record versions | PASS | A1, A11 |
| GQA-A02 | Stale evidence rejection | Vitest `-t` selector can exit 0 while all tests are skipped | Do not count zero-test selector as pass; run matching current selectors | PASS_WITH_STALE_SELECTOR_DEFECT | A12, A13, A14 |
| GQA-A03 | Sparse source missing business fields | Missing audience/evidence/risk/next-action should not crash emit; assist should ask/offer draft instead of fabricating | Emit `ok:true` quality warnings and assist `needs_user_input` | PASS | A2, A4, A10 |
| GQA-A04 | Long-source middle evidence | 2,000-line input should use line-ranged chunks, not head/tail truncation | `source_refs` include middle line ranges | PASS | A5, A10 |
| GQA-A05 | Visual prompt text leakage | Korean report copy must not be baked into image prompt/pixels | Prompt includes `no readable text in image`; Korean copy stays in overlay tests | PASS | A6, A15 |
| GQA-A06 | Render existence is not enough | DOCX/PPTX artifacts could exist but lack content | Open package XML and assert expected Korean strings | PASS | A8, A9, A10 |

### artifactRefs

| id | kind | description | path |
|---|---|---|---|
| A1 | terminal transcript | Tool versions and Python fallback evidence | `.omo/evidence/report-writing-quality/global-review-qa-env.txt` |
| A2 | JSON | Sparse emit-model CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-sparse-preflight.json` |
| A3 | JSON | Complete emit-model CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-complete-preflight.json` |
| A4 | JSON | Sparse assist CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-sparse-assist.json` |
| A5 | JSON | Long-source assist CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-long-assist.json` |
| A6 | JSON | Visual-cards CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-visual-cards.json` |
| A7 | JSON | HTML render CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-html-render.json` |
| A8 | JSON | DOCX render CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-docx-render.json` |
| A9 | JSON | PPTX render CLI output | `.omo/evidence/report-writing-quality/global-review-qa-cli-pptx-render.json` |
| A10 | parsed data output | JSON/package validation probe; checks quality fields, source refs, visual prompts, and HTML/DOCX/PPTX content | `.omo/evidence/report-writing-quality/global-review-qa-cli-validation.txt` |
| A11 | terminal transcript | Focused Python CLI tests, 23 passed | `.omo/evidence/report-writing-quality/global-review-qa-python-focused-tests.txt` |
| A12 | terminal transcript | Stale zero-test selector reproduction; 2 files skipped, 18 tests skipped, tests 0ms | `.omo/evidence/report-writing-quality/global-review-qa-zero-selector.txt` |
| A13 | terminal transcript | ReportView sparse/complete focused tests, 2 passed | `.omo/evidence/report-writing-quality/global-review-qa-gui-reportview.txt` |
| A14 | terminal transcript | Quality panel assistance and long-source ref tests, 2 passed | `.omo/evidence/report-writing-quality/global-review-qa-gui-quality-panel.txt` |
| A15 | terminal transcript | Visual-card panel overlay and production composer tests, 2 passed | `.omo/evidence/report-writing-quality/global-review-qa-gui-visual-cards.txt` |
| A16 | terminal transcript | GUI PDF wrapper test, 1 passed | `.omo/evidence/report-writing-quality/global-review-qa-gui-pdf.txt` |
| A17 | terminal transcript | GUI npm build output | `.omo/evidence/report-writing-quality/global-review-qa-npm-build.txt` |
| A18 | parsed data output | Non-empty artifact check for all global review artifacts | `.omo/evidence/report-writing-quality/global-review-qa-artifact-check.txt` |

## Residual Risks

- The stale Vitest selector `quality_sparse AI assistance requires user confirmation` exits 0 while running zero tests. This is recorded as failure evidence and was not counted as a pass.
- CLI invocations emitted a Python `runpy` runtime warning on stderr about `vibelign.cli.vib_cli` already being in `sys.modules`; JSON outputs still parsed and validated. This is a residual warning, not a blocking QA failure for the tested behavior.
- `npm run build` passed with the existing Vite large-chunk warning.
