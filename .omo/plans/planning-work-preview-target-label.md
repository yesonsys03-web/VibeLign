# Planning Work Preview Target Label

## Goal

Make the planning instruction preview panel show which instruction target is currently selected: common, Chloe, Gio, or Mina.

## TODOs

- [x] Add a current preview target label to the instruction preview panel.

## Acceptance Criteria

- Existing generic copy, persona copy, persona preview, and current-preview copy behaviors remain intact.
- Opening the preview shows a current target label for the common instruction.
- Choosing Gio preview updates the target label to `지오 Codex`.
- The label is plain React text and does not affect generated instruction content.

## Evidence

- Baseline test pins current-preview copy before changes.
- RED test proves the current target label is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
