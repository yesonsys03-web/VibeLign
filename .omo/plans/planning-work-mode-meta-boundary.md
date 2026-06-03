# Planning Work Mode Meta Boundary

## TODOs

- [x] Split PlanningRoom mode metadata out of `PlanningModeSelector.tsx`.

### Acceptance Criteria

- Planning mode definitions live in a focused module.
- Full mode derives persona ids from the centralized PlanningRoom persona metadata.
- `PlanningModeSelector.tsx` keeps rendering and selection event wiring only.
- Existing default Instant mode and full mode chip selection behavior stays unchanged.
- Every touched TypeScript/TSX file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/pages/planning/PlanningModes.test.ts src/pages/__tests__/PlanningRoom.mode.test.tsx src/pages/__tests__/PlanningRoom.mentions.test.tsx src/pages/planning/PlanningPersonas.test.ts`
- `./node_modules/.bin/eslint src/pages/planning/PlanningModes.ts src/pages/planning/PlanningModes.test.ts src/pages/planning/PlanningModeSelector.tsx src/pages/planning/PlanningPersonaComposer.tsx`
