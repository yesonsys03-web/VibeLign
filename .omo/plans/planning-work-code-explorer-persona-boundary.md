# Planning Work Code Explorer Persona Boundary

## TODOs

- [x] Derive Code Explorer planning work persona actions from centralized persona metadata.

### Acceptance Criteria

- Code Explorer copy and preview action labels are derived from `PlanningPersonas.ts`.
- Planning work instruction role labels use centralized persona metadata instead of duplicating Chloe, Gio, and Mina display names.
- CLI names and work-instruction role descriptions remain explicit in the Code Explorer instruction helper.
- Existing generic copy and persona-specific copy/preview behavior stays unchanged.
- Source-level regression tests prevent duplicated Chloe/Gio/Mina label tables in Code Explorer instruction files.
- Every touched TypeScript/TSX file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/lib/code-explorer/planningInstruction.test.ts src/pages/__tests__/CodeExplorer.planning-context.test.tsx src/pages/planning/PlanningPersonas.test.ts`
- `./node_modules/.bin/eslint src/lib/code-explorer/planningInstruction.ts src/lib/code-explorer/planningInstruction.test.ts src/components/code-explorer/PlanningInstructionActions.tsx src/pages/__tests__/CodeExplorer.planning-context.test.tsx`
