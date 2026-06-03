# Planning Work Persona Meta Boundary

## TODOs

- [x] Centralize PlanningRoom persona metadata across planning components.

### Acceptance Criteria

- Chloe, Gio, and Mina labels, roles, mentions, and avatar initials/colors live in one focused module.
- PlanningRoom composer, avatar, message, progress, response summary, and status components read persona metadata from that module.
- Unknown persona fallback behavior stays intact.
- Existing PlanningRoom persona UI behavior stays unchanged.
- Every touched TypeScript/TSX file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/pages/planning/PlanningPersonas.test.ts src/pages/planning/PlanningPersonaComposerState.test.ts src/pages/planning/PlanningMessages.status.test.tsx src/pages/__tests__/PlanningRoom.avatars.test.tsx src/pages/__tests__/PlanningRoom.progress.test.tsx src/pages/__tests__/PlanningRoom.response-summary.test.tsx src/pages/__tests__/PlanningRoom.status-labels.test.tsx src/pages/__tests__/PlanningRoom.mentions.test.tsx src/pages/__tests__/PlanningRoom.mode.test.tsx`
- `./node_modules/.bin/eslint src/pages/planning/PlanningPersonas.ts src/pages/planning/PlanningPersonas.test.ts src/pages/planning/PlanningPersonaComposerState.ts src/pages/planning/PlanningPersonaAvatar.tsx src/pages/planning/PlanningMessages.tsx src/pages/planning/PlanningPersonaProgressSummary.tsx src/pages/planning/PlanningPersonaResponseSummary.tsx src/pages/planning/PlanningPersonaStatus.tsx`
