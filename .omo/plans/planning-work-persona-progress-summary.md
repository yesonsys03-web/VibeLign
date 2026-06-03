# Planning Work Persona Progress Summary

## Goal

Show a compact planning-room persona progress summary so users can scan Chloe, Gio, and Mina status before reading the conversation.

## TODOs

- [x] Add a persona progress summary component to PlanningRoom.

## Acceptance Criteria

- Existing PlanningRoom message, composer, save, and status-badge behaviors remain intact.
- PlanningRoom shows one compact status chip each for Chloe, Gio, and Mina.
- Personas without assistant output show `준비됨`.
- Pending assistant output shows `검토 중`; ok output shows `완료`; failed output shows `실패`.
- The summary derives only from message metadata and does not expose raw stderr/details.

## Evidence

- Baseline test pins existing message status badge behavior before changes.
- RED test proves persona progress summary is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
