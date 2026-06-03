# Planning Work Preview Selection State

## Goal

Make preview choice buttons expose which instruction target is currently selected, both visually and through accessible pressed state.

## TODOs

- [x] Add selected state to the current preview choice buttons.

## Acceptance Criteria

- Existing preview target label and current-preview copy behaviors remain intact.
- Opening the preview marks `공통 미리보기` as selected.
- Choosing `지오 미리보기` moves the selected state from common to Gio.
- Selected state is exposed through `aria-pressed` and visible button styling.

## Evidence

- Baseline test pins the current preview target label before changes.
- RED test proves selected state is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
