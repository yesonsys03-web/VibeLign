# planning-work-plan-structure-command-accessor

## TODOs

- [x] Replace the `plan-structure` command metadata non-null assertion with a named safe accessor.

## Evidence

- RED: `npm test -- --run src/lib/legacySurface.test.ts` failed because `getPlanStructureCommand` did not exist.
- GREEN: `npm test -- --run src/lib/legacySurface.test.ts` passed 2 tests after adding the accessor.
- Regression: focused legacy/Home suite passed 5 files and 18 tests.
- Lint: `npm run lint` passed.
- Manual QA: Vite on `127.0.0.1:5202` returned HTTP 200 for `/`, `commands.ts`, and `PlanStructureCard.tsx`.
- Cleanup: Vite PID 9452 was killed and `lsof -ti :5202` returned no process.
