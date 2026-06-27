# Global Review Lane - Security Rerun After Fixes

Status: PASS

codeQualityStatus: WATCH
recommendation: APPROVE
reportPath: .omo/evidence/report-writing-quality/global-review-security-rerun.md
blockers: []

## Scope Audited

- Fix doneclaim: `.omo/evidence/report-writing-quality/global-review-security-fix-doneclaim.txt`
- Boundary parser: `vibelign/core/reporting_cli/model_json.py`
- Render payload CLI path: `vibelign/commands/vib_report_cmd.py`, `vibelign/commands/vib_report_render_payload.py`
- Focused tests: `tests/core/reporting_cli/test_model_json.py`, `tests/cli/test_vib_report_render_payload.py`
- Visual-card prompt/provider path: `vibelign/core/reporting_cli/report_visual_cards.py`, `tests/core/reporting_cli/test_report_visual_cards.py`, `tests/cli/test_vib_report_visual_cards_cmd.py`, `vibelign-gui/src/lib/vib/reportVisualCards.ts`, `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx`
- Render-payload GUI bridge spot-check: `vibelign-gui/src/lib/vib/reportRenderPayload.ts`, `vibelign-gui/src/lib/vib/report.ts`, `vibelign-gui/src-tauri/src/commands/report_render_payload.rs`

## Skill-Perspective Check

- `remove-ai-slops` perspective: ran by loading `/Users/topsphinx/.codex/plugins/cache/sisyphuslabs/omo/4.11.1/skills/remove-ai-slops/SKILL.md`. Focused tests are not deletion-only, not requested-removal-only, and not tautological. The malformed-payload tests mutate observable JSON payloads and assert the CLI boundary contract rather than mirroring implementation constants. No blocking slop violation found.
- `programming` perspective: ran by loading the main skill plus Python, TypeScript, and Rust references. The fix now parses untrusted render payload JSON at the boundary before constructing report models. No blocking parse-boundary violation remains. LOW residual: `model_json.py` still uses raw `dict`/`object` annotations at the JSON boundary (`vibelign/core/reporting_cli/model_json.py:9`, `vibelign/core/reporting_cli/model_json.py:47`), which is below blocker level for this security rerun because runtime checks reject malformed input before rendering.

## CRITICAL

None.

## HIGH

None.

## MEDIUM

None.

## LOW

1. Stale historical visual-card evidence still contains fake-provider output and the old `Korean report companion card` prompt wording.
   - Current source is clean: `vibelign/core/reporting_cli/report_visual_cards.py:274` builds fixed English scene prompts with `no readable text in image`, and `vibelign/core/reporting_cli/report_visual_cards.py:285` falls back if Hangul appears.
   - Current focused tests enforce no Hangul/fake-provider leakage in prompts: `tests/core/reporting_cli/test_report_visual_cards.py:116`, `tests/cli/test_vib_report_visual_cards_cmd.py:58`.
   - Residual: older artifacts such as `.omo/evidence/report-writing-quality/task-8-post-fix-visual-cards.json`, `.omo/evidence/report-writing-quality/task-8-visual-dom-snapshot.json`, and `.omo/evidence/report-writing-quality/task-8-provider-fix-visual-cards.json` should not be cited as current proof.

2. Rust/Tauri render-payload path has no focused Rust unit test under the checked filter.
   - `cargo test -q --manifest-path vibelign-gui/src-tauri/Cargo.toml report_render_payload` reported zero tests.
   - Manual inspection found the path guard confined removal to `.vibelign/reports/render-payloads` and filename prefix/suffix checks: `vibelign-gui/src-tauri/src/commands/report_render_payload.rs:11`.
   - Existing TS wrapper tests cover env handoff and cleanup: `vibelign-gui/src/lib/vib/__tests__/reportRenderPayload.test.ts:69`.

3. Two focused files are in the programming skill warning band, not over the 250 pure-LOC defect limit.
   - `vibelign/core/reporting_cli/report_visual_cards.py`: 240 pure LOC.
   - `tests/cli/test_vib_report_render_payload.py`: 244 pure LOC.
   - No split is required for this rerun, but future feature work should avoid growing these files.

## Verification Results

- Model boundary: PASS. `model_from_dict()` rejects non-dict models, missing required fields, non-list sections, non-dict sections, non-string headings, non-list blocks, non-dict blocks, invalid/non-string kinds, non-string block text, non-list items, and non-string item entries before constructing `ReportModel` (`vibelign/core/reporting_cli/model_json.py:47`).
- CLI JSON malformed payload contract: PASS. Real subprocess probe returned exit `1`, stdout `{"ok": false, "error": "render payload 형식이 잘못됐어요: text 는 문자열이어야 합니다"}`, and `stderr_bytes=0`.
- Render payload error conversion: PASS. `load_render_payload_models_from_env()` wraps malformed model payloads in `RenderPayloadFormatError` (`vibelign/commands/vib_report_render_payload.py:39`), and `run_vib_report()` converts that to `_fail(..., json)` without traceback (`vibelign/commands/vib_report_cmd.py:189`, `vibelign/commands/vib_report_cmd.py:278`).
- Visual-card prompt/provider: PASS for current code. Production CLI path uses `provider-neutral-draft`; no real provider call, no fake asset URL, and image prompts do not embed Korean report copy (`vibelign/core/reporting_cli/report_visual_cards.py:93`, `vibelign/core/reporting_cli/report_visual_cards.py:129`).
- Path/env leakage: PASS for active render-payload flow. GUI-created payload files are written under the project payload directory, env handoff passes only `VIBELIGN_REPORT_RENDER_PAYLOAD_PATH`, and cleanup runs in `finally` (`vibelign-gui/src/lib/vib/report.ts:259`). Residual evidence hygiene is listed under LOW.
- Evidence secret scan: PASS. Focused PCRE scan for OpenAI/Anthropic/Gemini keys, GitHub tokens, AWS keys, Slack tokens, and private-key headers returned no matches in focused source/evidence.

## Commands Run

- `uv run python -m pytest tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_render_payload.py tests/core/reporting_cli/test_report_visual_cards.py tests/cli/test_vib_report_visual_cards_cmd.py -v` -> 41 passed.
- `uv run ruff check vibelign/core/reporting_cli/model_json.py vibelign/commands/vib_report_render_payload.py vibelign/commands/vib_report_cmd.py vibelign/core/reporting_cli/report_visual_cards.py tests/core/reporting_cli/test_model_json.py tests/cli/test_vib_report_render_payload.py tests/core/reporting_cli/test_report_visual_cards.py tests/cli/test_vib_report_visual_cards_cmd.py` -> all checks passed.
- `uv run python -m compileall vibelign/core/reporting_cli vibelign/commands` -> pass.
- `npm run test -- src/lib/vib/__tests__/reportRenderPayload.test.ts src/lib/vib/__tests__/reportVisualCards.test.ts src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx` from `vibelign-gui/` -> 3 files, 10 tests passed.
- `cargo test -q --manifest-path vibelign-gui/src-tauri/Cargo.toml report_render_payload` -> zero tests matched.
- Manual malformed payload subprocess probe -> exit 1, JSON error on stdout, zero stderr bytes.

## Final Decision

PASS. The prior HIGH blocker is fixed: malformed render payload display fields are rejected at the boundary and `--json` returns a structured error without traceback/stderr. No CRITICAL/HIGH/MEDIUM findings remain. Approval is appropriate with LOW residual evidence hygiene and coverage notes above.
