# 디자인 미리보기 백그라운드 생성 — 설계 스펙

- 날짜: 2026-06-14
- 대상: `vibelign-gui/src` (프론트 전용, Rust 변경 없음)
- 상태: 설계 확정(사용자 승인 — 1안)

## 1. 배경 / 문제

디자인 미리보기에서 "✦ 클로드에게 그려달라기"를 누르면 스피너(바람개비)가 돌고, 앱이 멈춘 듯한 느낌을 준다. 실제로는:

- 생성은 이미 비동기(`await generateDesignMockup` — 단일 Tauri `invoke`, 스트리밍 아님)라 JS/앱 전체가 진짜 멈추진 않는다. 표시되는 "①②" 단계 메시지는 실제 진행률이 아니라 클라이언트가 찍는 안내문.
- **진짜 문제**: `DesignPreview`는 `{page === "design-preview" && <DesignPreview/>}` 로 조건부 렌더링이라, 다른 탭으로 가면 컴포넌트가 **언마운트**되고 진행 상태(`loading`/`synth`/`html`)가 파괴된다. Rust 쪽 작업은 끝까지 돌지만 **결과가 버려진다**. 그래서 사용자는 "나가면 안 될 것 같은" = 갇힌 느낌을 받는다.

## 2. 목표 / 비목표

**목표**
- 생성 작업 상태를 페이지 바깥(App 레벨)으로 올려 **탭 이동에도 살아남게** 한다. 작업은 백그라운드에서 끝나고, 돌아오면 결과가 그대로 있다.
- 생성 중에도 다른 탭을 자유롭게 쓸 수 있다(앱 사용 가능).
- 다른 탭에 있을 때 **상단 진행 칩**으로 상태를 알리고 한 번에 복귀할 수 있다.
- 디자인 탭에 머물면 진행 패널을 보여주고 그 탭의 생성 입력은 잠근다(중복 생성 방지).

**비목표**
- Rust 백그라운드 태스크/이벤트 스트리밍 진행률(과설계 — 본질은 프론트 상태 수명). 향후 개선으로 보류.
- 생성 도중 취소(사용자 결정: 취소 없음). 작업은 끝까지 돌고, 다시 그리려면 완료 후 새로 요청.
- 동시 다중 생성(한 번에 한 잡).

## 3. 설계 (1안)

### 컴포넌트 경계

**3-1. `useDesignJob(projectDir)` — 신규 훅** (`src/lib/design-preview/useDesignJob.ts`)
- 소유 상태: `status: "idle" | "running" | "done" | "error"`, `phaseMsg: string`, `html: string | null`, `synth: StyleSpec | null`, `error: string | null`.
- 공개 액션:
  - `run(params: DesignRunParams): void` — 내부에서 `synthesizeStyle`(필요 시)→`generateDesignMockup` 호출. `status`를 running→done/error로 전이하며 `phaseMsg`를 단계별로 갱신.
  - `recolor(key, value): void` — 합성 스타일 색 토큰 변경 + 결과 HTML 의 :root 변수만 교체(LLM 재호출 없음). synth+html 을 함께 만지므로 job 에 응집. `job.synth` 가 없으면 no-op.
  - `reset(): void` — idle 로 초기화.
  - (내부 `setHtml`/`setSynth`는 비공개 — 뷰는 위 액션만 호출.)
- `DesignRunParams` (판별):
  - `{ kind: "describe"; description: string; baseStyle?: StyleSpec }` → synthesize 후 mockup. 성공 시 `synth` 세팅.
  - `{ kind: "style"; style: StyleSpec; feedback?: string; previousHtml?: string }` → mockup 직접(synth 안 함; `synth`는 호출자가 넘긴 style이 합성본일 수 있으나 여기선 건드리지 않음).
- **App.tsx에서 인스턴스화** → 상태 수명 = 앱(프로젝트) 수명.
- **projectDir 변경 시 자동 reset**(useEffect 의존성 `[projectDir]`): 프로젝트 전환/종료 시 이전 잡 잔여 제거.
- **언마운트 후 setState 가드**: 훅은 App에 살아 언마운트되지 않지만, projectDir 변경으로 진행 중 잡 결과가 늦게 도착할 때를 대비해 `run` 내부에 시퀀스(증가하는 ref) 기반 stale-결과 무시 가드를 둔다(가장 최근 `run`의 결과만 반영).

**3-2. `DesignPreview` — `job` props를 받는 뷰**
- 시그니처에 `job: DesignJob` 추가(App이 주입). 기존 props(projectDir/planPath/isLikelyWeb/onBack/onConfirm) 유지.
- 폼/로컬 상태는 그대로 컴포넌트 로컬: `describe`, `feedback`, `selectedId`, `custom`, `savedMsg`. (이들은 탭 복귀 시 초기화돼도 무방 — 결과 html/synth 는 job 에 있으므로 보존됨.)
- 기존 `loading`/`loadingMsg`/`error`/`synth`/`html` 로컬 상태 제거 → `job.status`/`job.phaseMsg`/`job.error`/`job.synth`/`job.html` 로 대체.
  - `loading` 으로 쓰이던 disabled 게이트는 `job.status === "running"`.
  - 진행 패널 표시는 `job.status === "running"`, 메시지는 `job.phaseMsg`.
  - 목업/피드백 영역 표시는 `job.html` 존재.
- `createFromDescription`/`generate` → `job.run({kind:"describe"|"style", ...})` 호출로 대체.
- `recolor` → `job.recolor(key, value)` 호출만(로직은 §3-1 액션으로 응집; `replaceRootBlock`/`tokensToCssVars` 는 훅 내부에서 사용).
- `confirm()` → `job.synth ?? selected` + `job.html` 사용, 기존 `saveDesignMockup`→`onConfirm` 흐름 유지.

**3-3. `DesignJobChip` — 신규 셸 컴포넌트** (`src/components/nav/DesignJobChip.tsx`)
- App 셸에서 `GuideStrip` 아래에 렌더.
- 표시 조건/라벨은 순수 함수 `designChipState(status, page)` (`src/lib/nav/designChip.ts`)로 분리해 테스트:
  - `running` → `{ visible: true, tone: "busy", label: "🎨 디자인 생성 중…" }`
  - `done` & page ≠ "design-preview" → `{ visible: true, tone: "done", label: "✓ 디자인 완성 — 보기" }`
  - `error` & page ≠ "design-preview" → `{ visible: true, tone: "error", label: "⚠ 디자인 생성 실패 — 보기" }`
  - 그 외(또는 page === "design-preview") → `{ visible: false }`
- 클릭 → `navigate("design-preview")`. (running 중 디자인 탭에선 페이지 내 진행 패널이 이미 보이므로 칩 숨김.)

### 데이터 흐름

1. 디자인 탭에서 "그려달라기" → `job.run(...)` → `status: running`, `phaseMsg` 갱신. 디자인 탭 생성 버튼 disabled.
2. 다른 탭 이동 → `DesignPreview` 언마운트(폼 로컬 상태 소멸), `useDesignJob` 상태는 App 에 생존. `DesignJobChip` 등장.
3. 작업 완료 → `status: done`, `job.html` 세팅. 칩이 "완성"으로.
4. 칩 클릭 → `navigate("design-preview")` → `DesignPreview` 재마운트, `job.html` 그대로 표시. 칩 숨김.

## 4. 엣지 / 위험

- **동시 다중 생성 방지**: 디자인 탭 생성 버튼은 `running` 중 disabled. 다른 탭엔 생성 진입점이 없고 칩은 복귀만 함 → 새 잡 시작 불가.
- **stale 결과**: projectDir 전환 중 늦게 도착한 결과 → run 토큰 가드로 무시.
- **에러 방치**: 다른 탭에서 잡 실패 시 칩이 "실패 — 보기"로 노출 → 사용자가 모른 채 방치되지 않음.
- **프로젝트 종료**(onExitProject)/projectDir 변경 → job reset.
- **recolor 응집**: synth+html 동시 갱신이 job 액션에 모여 뷰는 단순 호출.
- **접근성**: 칩은 `role="status"`(busy) 또는 클릭 가능한 `button`. busy 상태엔 `aria-live="polite"`.

## 5. 테스트

- **`useDesignJob` (renderHook + vitest)**: `synthesizeStyle`/`generateDesignMockup` 모킹.
  - describe 흐름: idle→running→done, `html`/`synth` 세팅, generate가 synth 결과로 호출됨.
  - style 흐름: feedback/previousHtml 전달.
  - 에러: generate reject → `status: error`, `error` 메시지.
  - projectDir 변경 → reset(idle).
  - recolor: synth 토큰 변경 + html 의 :root 교체(LLM 재호출 없음).
- **`designChipState` (순수 단위)**: running/done(타페이지)/error(타페이지)/design-preview페이지/ idle 각 케이스의 visible·label.
- **`DesignPreview` (기존 4 테스트 이전)**: `useDesignJob`을 쓰는 작은 하네스 컴포넌트로 렌더(`render(<Harness .../>)`)해 기존 행동(스타일 선택→생성→iframe, 피드백 재생성, 비웹 배너, 확정 시 motion 바인딩) 유지. 모킹은 동일.
- **통합(수동)**: 그려달라기 → 다른 탭 이동(칩 등장 확인) → 완료 후 칩 클릭 복귀 → 결과 표시 확인.

## 6. 범위 / 파일

- Create `src/lib/design-preview/useDesignJob.ts` — 훅 + `DesignJob`/`DesignRunParams` 타입.
- Create `src/lib/nav/designChip.ts` — `designChipState` 순수 함수 + 타입.
- Create `src/components/nav/DesignJobChip.tsx` — 칩 컴포넌트.
- Modify `src/pages/DesignPreview.tsx` — `job` props 화, 로컬 잡 상태 제거.
- Modify `src/App.tsx` — `useDesignJob` 인스턴스화, DesignPreview 에 `job` 주입, 셸에 `DesignJobChip` 렌더.
- Tests: `src/lib/design-preview/__tests__/useDesignJob.test.ts`, `src/lib/nav/__tests__/designChip.test.ts`, `src/components/nav/__tests__/DesignJobChip.test.tsx`(선택), `src/pages/__tests__/DesignPreview.test.tsx`(하네스로 이전).
- 무변경: Rust(`generate_design_mockup` 등), 생성 invoke 래퍼(`src/lib/vib/design.ts`).
