# planning-work-help-primary-legacy-commands

## TODOs

- [x] Remove legacy commands from the beginner help primary command overview.

## Evidence

- RED: `npm test -- --run src/lib/helpData.test.ts` failed because the primary command overview still contained `patch` and `plan-structure`.
- GREEN: `npm test -- --run src/lib/helpData.test.ts` passed after removing those commands from the overview sentence.
- Regression: focused help/legacy/Home suite passed 5 files and 18 tests.
- Lint: `npm run lint` passed.
- Manual QA: Vite on `127.0.0.1:5203` returned HTTP 200 for `/`, `helpData.ts`, and `commands.ts`.
- Cleanup: Vite PID 29515 was killed and `lsof -ti :5203` returned no process.
