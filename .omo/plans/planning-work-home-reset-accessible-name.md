# planning-work-home-reset-accessible-name

## TODOs

- [x] Give the advanced Home reset-order icon button a real accessible name without changing its visual label.

## Evidence

- RED: `npm test -- --run src/components/home/__tests__/HomeHeader.test.tsx` failed because the reset button's accessible name was `↺`, not `카드 순서 초기화`.
- GREEN: `npm test -- --run src/components/home/__tests__/HomeHeader.test.tsx` passed 3 tests after adding `aria-label`.
- Regression: focused Home suite passed 10 files and 33 tests.
- Lint: `npm run lint` passed.
- Manual QA: Vite on `127.0.0.1:5201` returned HTTP 200 for `/`, `Home.tsx`, `HomeHeader.tsx`, and `SimpleHome.tsx`.
- Cleanup: Vite PID 3531 was killed and `lsof -ti :5201` returned no process.
