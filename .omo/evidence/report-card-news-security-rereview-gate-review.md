# Report Card News Security Rereview Gate

recommendation: APPROVE

blockers: []

originalIntent: Re-review the card-news export and GUI open-path security fixes after prior blockers. The user specifically wanted verification that card-news output cannot escape the project through symlinked output paths, only literal approved `true` cards export, generated HTML still escapes report text, and the card-news GUI opener call is constrained even though the global opener capability remains broad for existing non-card-news report behavior.

desiredOutcome: Card-news finalize writes JSON/HTML only under the project-owned `.vibelign/reports/card-news` path, fails closed for symlink/path escape and empty/non-literal approval cases, emits escaped static HTML, and calls `openPath` only after checking the returned card-news HTML path belongs to the current project card-news report directory.

userOutcomeReview: PASS for the requested security scope. Current source and fresh probes show the prior symlink/output escape and unconstrained card-news open-path blockers are closed. The broad global opener capability remains present, but the card-news call site now validates before invoking `openPath`.

## Security Findings

None.

## Direct Verification

- Output containment: `vibelign/core/reporting_cli/report_card_news_export.py:35-68` resolves the project root, computes the card-news directory/path, and calls `_assert_inside_root(root, path)` using `path.resolve(strict=False).relative_to(root)` before `mkdir` and before JSON/HTML writes.
- Symlink escape: current loop evidence `.omo/ulw-loop/report-card-news-complete/evidence/C002-empty-approved-cli.txt` records `symlink_exit_status=1` and `outside_dir_empty=yes`. A fresh temp-project probe also returned exit `1`, JSON error `카드뉴스 출력 경로가 프로젝트 밖을 가리켜요.`, and `outside_dir_empty=True`.
- Literal approval: `vibelign/core/reporting_cli/report_card_news_export.py:93-111` sets `approved` with `raw.get("approved") is True`; `tests/cli/test_vib_report_card_news_finalize_cmd.py:108-122` covers string `"false"` failing closed.
- HTML escaping: `vibelign/core/reporting_cli/report_card_news_export.py:180-239` uses `html.escape(...)` for provider/title/body/caption/visual prompt. A fresh malicious-text export probe found `literal_script_present=False`, `literal_img_present=False`, and escaped title text present.
- Card-news opener constraint: `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx:73-88` checks `isProjectCardNewsHtml(...)` before `openPath`; `isProjectCardNewsHtml` requires the normalized path to start with `${cwd}/.vibelign/reports/card-news/`, end in `.html`, and not contain `/../`.
- Global opener context: `vibelign-gui/src-tauri/capabilities/default.json:11-15` still includes broad `opener:allow-open-path`; this is expected by the user for existing non-card-news report open behavior.

## Commands Run

- `uv run pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -q` -> `6 passed`.
- `cd vibelign-gui && npm test -- --run src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx src/lib/vib/__tests__/reportVisualCards.test.ts` -> `2 passed` test files, `11 passed` tests.
- Fresh temp-project symlink/escaping probe via `uv run python` -> symlink failed closed and malicious HTML text was escaped.
- `uv run basedpyright vibelign/core/reporting_cli/report_card_news_export.py vibelign/commands/vib_report_card_news_cmd.py vibelign/cli/cli_report_command_groups.py` -> `0 errors, 0 warnings`.
- TypeScript no-excuse check over focused card-news GUI/library files -> no violations.

## Slop And Programming Pass

Direct `remove-ai-slops` pass over the focused diff, tests, and production code found no unresolved security slop. The new symlink, literal-approval, and invalid-open-path tests assert observable security behavior; they are not deletion-only, tautological, or implementation-mirroring tests. The `_assert_inside_root` helper and card-news opener check are small, security-relevant boundaries rather than speculative extraction.

Direct `programming` pass found no production type-checking blocker in the focused Python exporter/command files and no TypeScript no-excuse violation in the focused GUI files. A broader Python no-excuse run still reports non-security typing debt in the test helper annotations and an existing command-registration `object` annotation; this does not reopen the requested card-news export/open-path security blockers.

## Checked Artifact Paths

- `.omo/ulw-loop/report-card-news-complete/brief.md`
- `.omo/ulw-loop/report-card-news-complete/goals.json`
- `.omo/ulw-loop/report-card-news-complete/evidence/C002-empty-approved-cli.txt`
- `.omo/ulw-loop/report-card-news-complete/evidence/C003-regression-tests.txt`
- `.omo/ulw-loop/report-card-news-complete/evidence/gui-regression-tests.txt`
- `.omo/evidence/card-news-finalize-code-review-postfix.md`
- `.omo/evidence/card-news-finalize-code-review.md`
- `.omo/evidence/card-news-finalize-qa/C002-cli-empty-approved-error.txt`
- `.omo/evidence/card-news-finalize-qa/C003-gui-result-open-targeted-tests.txt`
- `.omo/evidence/card-news-finalize-qa/C004-python-regression-test.txt`
- `vibelign/core/reporting_cli/report_card_news_export.py`
- `vibelign/commands/vib_report_card_news_cmd.py`
- `vibelign/cli/cli_report_command_groups.py`
- `tests/cli/test_vib_report_card_news_finalize_cmd.py`
- `vibelign-gui/src/lib/vib/reportVisualCards.ts`
- `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`
- `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx`
- `vibelign-gui/src-tauri/capabilities/default.json`

## Exact Evidence Gaps

- No unresolved security evidence gap remains for the requested re-review.
- Older `.omo/evidence/card-news-finalize-qa/C002-cli-empty-approved-error.txt` and `C004-python-regression-test.txt` are stale relative to the current fixes: they do not include the symlink proof and still show the earlier 3-test Python run. Current verification uses `.omo/ulw-loop/report-card-news-complete/evidence/C002-empty-approved-cli.txt`, current source, and fresh local reruns instead.
- Older `.omo/evidence/card-news-finalize-code-review.md` is a pre-fix code-review artifact and still records old blockers. It is superseded by `.omo/evidence/card-news-finalize-code-review-postfix.md`, which explicitly covers the programming boundary and overfit/slop checks for the post-fix card-news scope.
