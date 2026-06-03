# Planning Work Mode Target Label Boundary

## TODOs

- [x] Derive PlanningRoom mode target labels from persona metadata.

### Acceptance Criteria

- Instant and draft mode target labels read from centralized persona metadata.
- Full mode still uses the group label `모두`.
- `PlanningModes.ts` no longer hardcodes Chloe/Gio Korean target labels.
- Existing default Instant mode, full mode chip selection, and mention behavior stay unchanged.
- Every touched TypeScript file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/pages/planning/PlanningModes.test.ts src/pages/__tests__/PlanningRoom.mode.test.tsx src/pages/__tests__/PlanningRoom.mentions.test.tsx src/pages/planning/PlanningPersonas.test.ts`
- `./node_modules/.bin/eslint src/pages/planning/PlanningModes.ts src/pages/planning/PlanningModes.test.ts`
