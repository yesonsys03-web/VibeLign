# Planning Work Preview Copy

## Goal

Let users copy the exact instruction currently shown in the preview, including the selected persona-specific instruction.

## TODOs

- [x] Add a copy action for the currently previewed instruction.

## Acceptance Criteria

- Existing generic copy, persona copy, generic preview, and persona preview behaviors remain intact.
- When the preview is open, a `현재 미리보기 복사` action is visible.
- If Gio preview is selected, `현재 미리보기 복사` writes the Gio/Codex instruction to the clipboard.
- Clipboard failure still opens the preview and shows the generated fallback instruction.

## Evidence

- Baseline test pins existing persona preview behavior before changes.
- RED test proves copying the currently selected preview is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
