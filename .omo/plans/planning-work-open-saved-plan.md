# Planning Work Open Saved Plan

## Goal

Add a PlanningRoom action that opens the saved planning Markdown file, matching the PR5 GUI contract for a saved-file open button.

## TODOs

- [x] Add a saved-plan open action to the PlanningRoom action bar.

## Acceptance Criteria

- The open action is hidden until a plan has been saved.
- Clicking the open action calls the existing path-opening bridge with `absoluteOutputPath` when available.
- If only a relative `outputPath` is available, the GUI resolves it against `projectDir`.
- Existing save, markdown preview, and AI-work actions remain intact.
- The change stays in the PlanningRoom/action-bar component boundary and does not expose raw CLI/model terminology.

## Evidence

- Baseline test pins the existing saved-plan action buttons before changes.
- RED test proves the saved-plan open button is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
