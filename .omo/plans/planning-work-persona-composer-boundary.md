# Planning Work Persona Composer Boundary

## TODOs

- [x] Split persona composer state helpers out of `PlanningPersonaComposer.tsx`.

### Acceptance Criteria

- `PlanningPersonaComposer.tsx` keeps UI rendering and event wiring only.
- Mention insertion, persona toggling, pending user message, and pending assistant message composition live in a focused module.
- Existing PlanningRoom mention and mode behavior stays unchanged.
- The composer file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/pages/planning/PlanningPersonaComposerState.test.ts src/pages/__tests__/PlanningRoom.mentions.test.tsx src/pages/__tests__/PlanningRoom.mode.test.tsx`
- `npm run lint -- src/pages/planning/PlanningPersonaComposer.tsx src/pages/planning/PlanningPersonaComposerState.ts src/pages/planning/PlanningPersonaComposerState.test.ts`
