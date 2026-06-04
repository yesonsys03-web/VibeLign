# Planning Work Simple Home

## TODOs

- [x] Replace the beginner Home surface with three simple status blocks and move the existing card grid behind advanced disclosure.

### Acceptance Criteria

- Default Home shows `프로젝트 안전 상태`, `지금 할 일`, and `되돌리기`.
- Default Home does not show `vib patch`, `CodeSpeak`, `plan-structure`, `target_anchor`, `MCP`, or `rules`.
- Existing card grid remains reachable after opening `고급 기능 보기`.
- Guard warn/fail state shows exactly one next action in the beginner surface.
- Existing manual list/detail views remain reachable.
- `Home.tsx` grows only by small wiring; new beginner UI lives under `components/home`.
- Every newly created TypeScript/TSX file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.

### Verification Commands

- `npm test -- --run src/pages/__tests__/Home.simple.test.tsx src/components/home/__tests__/HomePlanningEntry.test.tsx`
- `./node_modules/.bin/eslint src/pages/Home.tsx src/pages/__tests__/Home.simple.test.tsx src/components/home/SimpleHome.tsx`
