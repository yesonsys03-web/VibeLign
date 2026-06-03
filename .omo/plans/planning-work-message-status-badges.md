# Planning Work Message Status Badges

## Goal

Show each planning-room persona response status directly inside the message bubble, so users can distinguish ready, pending, and failed persona replies without reading the body text.

## TODOs

- [x] Add persona message status badges to planning-room assistant bubbles.

## Acceptance Criteria

- Existing PlanningRoom message, save, markdown view, and follow-up submit behaviors remain intact.
- Persona assistant bubbles show the persona label and a compact Korean status badge.
- Pending persona replies show `준비 중`; failed replies show `실패`; ok replies show `완료`.
- User messages do not show persona status badges.

## Evidence

- Baseline test pins the existing saved chat and persona composer behavior before changes.
- RED test proves persona status badges are missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
