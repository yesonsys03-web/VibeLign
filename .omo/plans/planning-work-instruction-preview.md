# Planning Work Instruction Preview

## Goal

Allow users to inspect the saved-plan AI work instruction before copying it, while keeping the Code Explorer planning context component small and structured.

## TODOs

- [x] Extract planning instruction actions into a component and add an explicit preview path.

## Acceptance Criteria

- The saved planning context keeps the existing generic copy and persona-specific copy actions.
- A visible `작업 지시 미리보기` action opens the generated work instruction without requiring clipboard failure.
- The new preview path renders the same generated instruction content used for copy.
- The existing planning context wrapper stays focused on saved-plan display and delegates action state to a child component.

## Evidence

- Baseline test pins existing persona-specific copy behavior before changes.
- RED test proves preview is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures the live Vite app returning HTTP 200.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
