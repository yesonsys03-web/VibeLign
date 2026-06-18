# Changelog

본 파일은 VibeLign 의 주요 변경사항을 기록합니다.
포맷은 [Keep a Changelog](https://keepachangelog.com/) 를 따르며,
버전 체계는 [Semantic Versioning](https://semver.org/) 을 준수합니다.

---

## [Unreleased]

---

## [2.5.1] — 2026-06-18

**삿갓 specimen 보고서팩 + Claude 안내 복원** — v2.5.0 보고서 내보내기 위에 satgat 스타일 specimen 테마 13종을 추가하고, 취소된 Claude 정책 변경 대응 문구를 되돌렸다. 기획방 기본 우선순위도 기존 흐름인 클로이(Claude) → 지오(Codex) 순서로 복원했다.

### Added

- **삿갓 specimen 보고서 테마 13종** — satgat 데모팩 전수 specimen처럼 바로 비교할 수 있는 보고서 양식을 theme catalog와 GUI 드롭다운에 추가 (`theme_catalog.py`, `reportThemes.ts`).

### Changed

- **기획방 기본 응답 모드 복원** — 기본 선택을 `초안 · 클로이`로 되돌리고, `Instant · 지오`는 두 번째 선택지로 유지 (`PlanningModes.ts`, `PlanningRoom.mode.test.tsx`).
- **Claude 크레딧/차감 경고 제거** — 취소된 `claude -p` 정책 변경 대응 문구를 기획방 칩, 페르소나 설정, 작업방, 디자인 미리보기에서 제거 (`PlanningPersonaComposer.tsx`, `PlanningPersonaSettings.tsx`, `WorkRoom.tsx`, `DesignPreview.tsx`).

### Verified

- GUI 기획방/디자인 테스트 22개 통과, 변경 파일 ESLint 통과, `npx tsc --noEmit` 통과, `npx vite build` 통과. 보고서 테마 테스트는 13종 specimen 테마 ID와 GUI theme metadata를 검증.

---

## [2.5.0] — 2026-06-18

**보고서 작성 대폭 강화** — 기획방에서 만든 기획안(또는 임의 문서)을 직장에서 바로 쓰는 보고서로 내보내는 흐름을 처음부터 끝까지 다듬었다. PDF·Word·PPT 출력, 50여 종 테마, 한글 무료 폰트 선택, 그리고 Word 한글이 "풀려" 보이던 문제까지 정리했다.

### Added

- **기획안 → 보고서 원클릭** — 저장된 기획안을 **업무 보고 · 제안서 · 결과 보고 · 문서 그대로** 네 종류로 내보낸다 (`ReportComposer.tsx`, `ReportView.tsx`, `vib report`).
- **우클릭으로 보고서 작성** — 문서/코드 탐색에서 우클릭 → "보고서 작성" 진입. 기획 양식이 아닌 임의 `.md` 도 "문서 그대로"(`--type doc`)로 보고서화 (`parse_generic_markdown`).
- **4가지 출력 포맷** — HTML 미리보기 · **PDF** · **Word(.docx)** · **PPT(.pptx)**.
- **PDF 인앱 미리보기 + 2-pane 작성 화면** — 왼쪽 옵션, 오른쪽에 결과 PDF 가 바로 보인다(pdf.js 내장 렌더).
- **디자인 테마 50여 종** — 레이아웃 × 색상 팔레트 × 밀도 조합.
- **폰트 크기 조절** — 제목 · 머리말(종류·날짜·작성자) · 소제목 · 본문 각각.
- **폰트 선택 — 무료 한글 폰트 5종(OFL, 상업적 사용 무료)** — Pretendard · 나눔명조 · 고운바탕 · 고운돋움 · 검은고딕. **제목용·본문용을 따로** 고르며, PDF 에는 폰트가 **파일에 임베딩**되어 폰트가 없는 PC 에서 열어도 동일하게 보인다 (`fonts.py`, `reportFonts.ts`, `ReportFontSelect.tsx`, HTML/Word/PPT 렌더러).
- **AI 어조 다듬기(무료)** — 보고서 어조를 블록 단위로 다듬고 수락/거부 검토. 큰 문서는 소요시간을 미리 경고.
- **페이지 번호**(Word·PDF) 및 **저장 위치 지정/기억**.

### Fixed

- **Word/PPT 에서 한글이 "풀려" 보이던 문제 해결** — macOS 파일명에서 유입된 NFD(자모 분해형) 한글이 Word 에서 자모로 분리돼 보이던 현상을, 출력 직전 NFC(조합형) 정규화로 수정 (`render_job.py`).
- 번들에 폰트 파일이 없어도 크래시 없이 시스템 폰트로 폴백(graceful degrade).
- 일반 문서에 기획 양식 종류(업무/제안/결과)를 고르면 빈 보고서가 나오던 문제 방지.
- "AI 다듬기"가 켜진 상태에서 빈 기획안 화면이 검토 화면을 가리던 버그 수정.

### Changed

- Word/PPT 내보내기 의존성(python-docx/pptx 등)을 기본 설치에 포함 — 별도 설치 불필요.
- 앱 내 확인창을 `window.confirm` → Tauri 네이티브 다이얼로그로 전환(웹뷰 반환값 신뢰성 개선).
- 폰트 자산을 wheel/sdist 패키징과 PyInstaller 번들 양쪽에 포함, 런타임 로딩을 `importlib.resources` 로 전환해 배포본(GUI 사이드카)에서도 안정적으로 동작.

### Verified

- Python reporting + CLI 테스트 통과(폰트/렌더/CLI), `ruff` 클린, GUI `tsc`·`eslint` 클린, vitest 통과. CLI 스모크로 PDF 에 한글 폰트 임베딩 + Word 한글 정상 조합 확인. 다중 에이전트 태스크별 리뷰 + 최종 전체 리뷰 통과.

---

## [2.4.4] — 2026-06-15

**온보딩·기획방 갸리카(자동차) 마스코트** — 처음 쓰는 사람도 친근하게 시작하고, 기다리는 시간도 덜 지루하도록 길잡이 캐릭터를 "운전하는 갸리카"로 바꿨다.

### Added

- **온보딩 갸리카 마스코트** — 첫 화면에서 자동차가 왼쪽 화면 밖에서 운전해 들어와 입력란 아래에서 급정거한 뒤, 잠시 후 환영 말풍선("안녕! 난 바이브라인 길잡이 🚗")을 띄운다. 정지 후엔 제자리에서 바퀴만 도는 idle 루프 (`Onboarding.tsx`, `brutalism.css`, 신규 `gyaricar_ani2.png`).
- **클릭 순환 인터랙션** — 갸리카 클릭 → 말풍선 접기, 다시 클릭 → "부릉부릉" 뒤로 움츠렸다 오른쪽 화면 밖으로 퇴장, 빈 곳 아무 데나 클릭 → 다시 운전해 들어옴(루프).

### Changed

- **기획방 답변 대기 로딩** — 페르소나(클로이/지오/미나/딥시기)가 답변을 준비하는 동안, 밋밋한 대기 텍스트 대신 갸리카가 제자리에서 "부릉부릉" 달리는 로딩 애니메이션을 보여준다 (`PlanningMessages.tsx`).
- **길잡이 마스코트 교체** — 기존 나침반(🧭) 이모지 길잡이를 운전하는 갸리카 캐릭터로 교체(타이틀 정렬·측정 기반 등장 로직 제거).

### Internal

- 다수 GUI/코어 소스·테스트 파일에 `ANCHOR` 경계 주석을 일괄 추가(코드맵·안전 편집 구역 정비). 동작 변경 없음.

### Verified

- GUI 타입체크(`tsc --noEmit`)·기획방 메시지 테스트·`eslint` 통과. 스프라이트 알파(투명 배경)·온보딩 클릭 루프·기획방 로딩 애니메이션 육안 확인.

---

## [2.4.3] — 2026-06-15

**Claude 가격 정책 변경 대응 — 자동 Claude 호출 최소화** — 2026-06-15부터 `claude -p`(헤드리스)·Claude Agent SDK 등 **프로그래밍 방식** Claude 사용이 구독 사용량 풀이 아니라 **별도 월 크레딧/표준 API 요금**으로 청구되도록 정책이 바뀌었다. VibeLign이 사용자 모르게 Claude를 자동 호출해 크레딧을 소모하지 않도록 정리하고, 쓸 때도 비용을 낮췄다. (터미널에서 직접 쓰는 **인터랙티브 Claude Code 사용은 영향 없음**)

### Changed

- **기획방 페르소나** — 자동 폴백 우선순위에서 claude를 맨 뒤로 돌려 codex·opencode를 먼저 쓰고, **클로이(claude)는 기본 OFF(opt-in)**. 컴포저에서 꺼진 페르소나는 선택이 막히고 "꺼짐"으로 표시되며 "모두"는 켜진 도구만 부른다 (`planning_persona.rs`, `planning_chat.rs`, `PlanningPersonaComposer.tsx`, `PlanningPersonaSettings.tsx`).
- **Claude 모델 opus→sonnet** — 켜서 쓰더라도 크레딧 소모를 줄이도록 페르소나·판정(judge)·디자인 생성·Python CLI 전반에서 sonnet으로 고정.
- **디자인 미리보기** — codex 우선 생성, Claude는 클로이가 켜진 경우에만. "클로드"→"AI" 문구로 바꾸고 크레딧 안내 추가 (`pick_generation_cli`, `DesignPreview.tsx`, `useDesignJob.ts`).
- **작업방(WorkRoom)** — 기본 실행 도구를 **Codex**로, Claude Code 선택 시 `claude -p` 크레딧 차감 경고 배너 + 실행 전 확인 노트 (`WorkRoom.tsx`).
- **Python `vib` CLI** — 기본 페르소나 세트(@모두·멘션 없음)에서 클로이 제외(`@클로이`로 명시할 때만 실행), claude→sonnet (`mentions.py`, `cli_adapters.py`).

### Added

- 비활성 페르소나가 호출되면 조용한 무응답 대신 **"꺼짐" 안내 메시지**(status=disabled)를 남긴다.
- 클로이/Claude Code 선택 지점마다 **"크레딧 차감 가능" 경고** 표시.

### Notes

- **영향받지 않음**: 터미널에서 직접 쓰는 인터랙티브 Claude Code, MCP 서버 연동, 사용자 API 키 직접 호출(`vib ask`·docs-enhance).

### Verified

- `cargo test` 93 통과 · `pytest` 1195 통과 · GUI vitest 통과.

---

## [2.4.2] — 2026-06-15

**설치된 AI 도구 감지 정확화 + 설정 화면 가독성 + 기획방 자동 스크롤** — 컴퓨터에 깔려 있는 AI CLI 도구가 설정에서 "설치됨"으로 안 뜨던 문제를 고치고, 설정 카드 텍스트 가독성을 통일했으며, 기획방에서 새 답변으로 자동 스크롤되게 했다.

### Fixed

- **설치된 AI 도구 감지 누락** — 설정 "AI 도구 설정"의 도구 감지가 `zsh -lc`/`bash -lc` 로그인(비대화형) 셸의 `command -v` 에 의존해, `.zshrc`(대화형 셸 전용)에서 PATH를 export 하는 도구(`~/.bun/bin` 의 opencode 등)를 설치돼 있어도 못 찾던 문제. augmented PATH(homebrew·cargo·bun·.local/bin 등)를 직접 탐색하는 `find_executable` 우선 방식으로 변경 — Finder/Dock 실행 시에도 누락 없이 감지되고, 설치된 도구는 느린 셸 spawn 도 건너뛴다 (`vibelign-gui/src-tauri/src/onboarding/macos.rs`, `vibelign-gui/src-tauri/src/onboarding/mod.rs`).

### Changed

- **설치 상태 표시 명확화** — 도구 이름 뒤 모호한 " MCP" 접미사를 또렷한 **"✓ 설치됨"** 배지로 교체. 설치됨/자동설치/직접설치 배지를 초록/앰버/회색으로 구분하고, 선택(파란 버튼) 여부와 무관하게 밝은 배경+진한 글자로 고정해 가독성을 확보 (`vibelign-gui/src/components/ToolSetupSelector.tsx`).
- **설정 카드 텍스트 가독성 통일** — AI 도구 설정·기획방 페르소나·API 키 카드의 설명 문구가 다른 카드보다 작고(11px) 흐린 회색이라 안 읽히던 문제를 표준 카드 스타일(13px·진한색·lineHeight 1.7)로 통일. API 키 제공자 이름의 터미널용 네온 그린(#7DFF6B)도 흰 카드에서 안 읽혀 진한색으로 변경 (`vibelign-gui/src/pages/Settings.tsx`, `vibelign-gui/src/components/PlanningPersonaSettings.tsx`).

### Added

- **기획방 대화창 스마트 자동 스크롤** — 메시지를 보내거나 새 응답이 오면 화면이 페이지 맨 아래가 아니라 그 답변 메시지 위치로 자동 스크롤된다. 사용자가 위에서 이전 대화를 읽는 중이면 가로채지 않는 stick-to-bottom 방식 (`vibelign-gui/src/pages/planning/PlanningMessages.tsx`).

### Verified

- `tsc --noEmit` ✓, `eslint` ✓, GUI 단위 테스트(PlanningMessages 6/6) ✓, `cargo build`(GUI 백엔드) ✓.

---

## [2.4.1] — 2026-06-14

**AI CLI 도구 언인스톨 + dead-code 정리** — opencode/codex/antigravity CLI를 앱 안에서 제거할 수 있게 했다. 클로드코드 언인스톨과 동일하게 **CLI 바이너리만** 제거하고 MCP 설정·도구 config·로그인은 보존한다.

### Added

- **AI CLI 도구 언인스톨** — opencode / codex / antigravity(agy) 를 GUI에서 제거. opencode·codex(macOS)는 제거 명령으로 자동 처리, agy(macOS)는 PATH에서 resolve된 단일 바이너리만 `std::fs::remove_file`(파일 1개·비재귀·셸 미경유) 후 재-probe로 검증해 심링크/중복 PATH 거짓성공을 방지, codex/agy(Windows)는 수동 제거 안내 폴백. `ToolInstallPanel` 에 🗑 제거 버튼 + 확인 + 진행/완료/안내 단계 추가. CLI 바이너리만 제거하고 MCP 설정(`.mcp.json` 등)·도구 config·로그인 상태는 보존 (`vibelign-gui/src-tauri/src/commands/tool_install.rs`, `vibelign-gui/src/lib/tools/installerRegistry.ts`, `vibelign-gui/src/components/tools/ToolInstallPanel.tsx`).

### Fixed

- **`SPAWN_FAIL` dead-code 경고 제거** — `vibelign-gui/src-tauri/src/commands/project_summary.rs` 에서 쓰이지 않던 `const SPAWN_FAIL` 상수를 삭제해 `dead_code` 경고를 없앴다.

### Notes

- **버전 동기화 보정** — `vibelign-core/Cargo.toml` 이 v2.4.0 에서 2.3.1 에 머물던 드리프트를 2.4.1 로 맞춰 6개 버전 소스를 재동기화.

### Verified

- Rust `cargo test --lib tool_install` 11 passed, 프론트 `vitest ToolInstallPanel.test.tsx` 4 passed. 4-task TDD 구현이 각각 스펙+품질 리뷰 + 최종 전체 리뷰를 통과.

---

## [2.4.0] — 2026-06-14

**디자인 미리보기의 도약 + 앱 반응성 대수술** — 일상어로 스타일을 즉석 합성하고, 생성 작업이 탭을 넘나들며 살아남는 백그라운드 잡 시스템을 도입했으며, 동기 Tauri 커맨드가 메인 스레드를 막던 근본 원인을 `async + spawn_blocking`으로 해소한 릴리즈. AI 도구 원클릭 설치, 온보딩 "실행해보기" 흐름, `vib start` 베이스라인 커밋까지 더해 처음 사용자의 데드엔드를 제거했다.

### Added

- **디자인 미리보기 — 자유 입력 스타일 합성** — 일상어나 예시 칩으로 스타일을 설명하면 Claude가 즉석으로 스타일을 합성(`synthesize_style`)하고 결과를 카드로 보여준 뒤 목업까지 자동 렌더한다. 기존 프리셋 5종에서 문자 그대로 무한 조합으로 확장.
- **디자인 미리보기 — 색 스와치 즉시 재색칠** — 합성된 스타일의 색 스와치를 클릭하면 LLM 재호출 없이 즉시 팔레트를 교체할 수 있다.
- **디자인 미리보기 — 커스텀 스타일 저장/목록/삭제** — 자신이 만든 스타일을 저장하고 나중에 불러오거나 삭제한다. 프리셋 변형도 독립적으로 보관 가능.
- **디자인 미리보기 — 단계별 진행 패널** — 생성 중 각 단계(스타일 합성 → 목업 렌더)의 진행 상황을 패널로 실시간 표시.
- **디자인 미리보기 — 백그라운드 잡** — 생성 도중 탭을 이동해도 작업이 살아남아 완료된다. 상단 진행 칩으로 상태를 알리며 클릭하면 즉시 결과 탭으로 복귀(`useDesignJob` 훅으로 잡 상태를 앱 수명으로 승격).
- **AI 도구 원클릭 설치** — opencode / codex / antigravity(agy) 설치를 앱 안에서 바로 진행한다. 설치 레지스트리 + 플랫폼별 명령(Windows/macOS) + 실시간 로그·인증 안내·수동 폴백이 포함된 설치 패널 제공. opencode는 API 키 없이 원클릭 설치로 작업방 "도구 없음" 데드엔드 제거. 초보자는 Claude로 안내.
- **온보딩 — "실행해보기" 버튼 + 작동 검증** — 홈 5단계에 "실행해보기" 버튼을 추가하고, 앱 실행 포트 감지 → WebView 내장 렌더 → `runVerified` 확인까지 자동화해 6단계로 진행된다.
- **온보딩 — 기획 확정 후 디자인 분기 노출** — 기획이 완료되면 "디자인 먼저 정하기" 분기를 안내해 디자인 미리보기의 발견성을 높인다.
- **`vib start` 베이스라인 커밋** — `vib start` 실행 시 초기 git 커밋을 자동 생성해 커밋이 0개인 신규 프로젝트에서도 변경 감지가 정상 작동한다. 기본 `.gitignore`에 `node_modules/`·`.DS_Store` 추가.

### Changed

- **홈 5단계 — 남은 축 동적 표시** — 이미 완료된 단계는 숨기고 남은 항목만 동적으로 보여줘 화면을 간결하게 유지한다.
- **복구 추천 — 백업 대시보드 상단 노출** — 복구 추천 메시지를 백업 대시보드 최상단에 배치해 눈에 바로 띄도록 개선.

### Fixed

- **앱 멈춤(Freeze) — 디자인 생성 중 UI 응답 없음** — `generate` / `synthesize_style` Tauri 커맨드가 동기로 메인 스레드를 점유하던 것을 `async + spawn_blocking`으로 전환. 무거운 생성 작업 중에도 UI가 반응한다.
- **앱 멈춤 — 홈 로딩 중 UI 응답 없음** — `read_project_summary`·git 요약 커맨드가 메인 스레드를 막던 문제를 동일한 패턴으로 해소.
- **앱 멈춤 — 문서 인덱싱 중 UI 응답 없음** — `vib docs-index` 4종 커맨드를 비동기화해 인덱싱 중에도 다른 메뉴를 자유롭게 사용할 수 있다.
- **앱 멈춤 — AI 도구 설치 중 UI 응답 없음** — `install_tool` 커맨드를 `async + spawn_blocking`으로 전환해 설치 중 UI가 얼어붙지 않는다.
- **git 미설치 시 상단 상시 경고** — git이 없는 환경에서 화면 전체를 막는 대신 상단 배너로 비차단 경고를 표시한다.
- **변경 없을 때 스테일 가이드 오버라이드 정리** — `vib start` 후 변경이 없는 상태에서 검증/저장 단계가 오래된 가이드 메시지를 덮어쓰던 문제 수정.

---

## [2.3.1] — 2026-06-09

**기획방 저장 입구 통합** — 기획안 저장을 단 하나의 통제 경로로 모으고, 거기에 접근하는 결정적 입구를 둘(저장 버튼 + `/저장` 슬래시 커맨드)로 정리한 릴리즈. 자연어 의도 추론 없이 명시적 입구만 쓰고, 어느 입구가 실제로 쓰이는지 데이터로 확인할 수 있게 했다.

### Added

- **`/저장` 슬래시 커맨드** — 입력란에 `/저장` 을 치면 페르소나 호출 없이 즉시 기획안을 저장한다. 저장 버튼과 **완전히 같은 통제 저장 경로**(고정 템플릿 + 확정카드 주입 + readiness 헤더 + `output_path` 등록)를 타므로 결과물이 동일하다. 키보드 흐름을 끊고 싶지 않은 사용자를 위한 입구.
- **슬래시 커맨드 힌트 + Tab 자동완성** — 입력란에서 `/` 를 치면 `/저장` 커맨드 힌트가 떠오르고, **Tab 키 또는 클릭**으로 자동완성된다. 새 커맨드를 추가하기 쉬운 구조.
- **저장 출처 로깅** — 각 저장이 버튼에서 왔는지 `/저장` 에서 왔는지 `.vibelign/planning/save-sources.json` 에 누적 카운트한다(개인정보 없음, 횟수만). 두 입구의 실제 사용 비율을 보고 입구 구성을 다듬기 위한 가벼운 텔레메트리.

### Changed

- **저장 버튼 항상 노출** — 기획방 액션 바를 하단 고정(sticky)으로 바꿔, 대화가 길어져도 저장 버튼이 스크롤로 사라지지 않는다.

### Fixed

- **Windows 한글 입력 대응** — `/저장` 매칭과 커맨드 힌트가 한글 IME 조합 중에는 끼어들지 않도록 가드를 두고, NFC 정규화로 NFD 분해형 붙여넣기(특히 macOS産 텍스트)도 동일하게 인식한다. 윈도/맥 양쪽에서 오발동 없이 동작한다.

---

## [2.3.0] — 2026-06-08

**기획방(Planning Room) 도입** — 코드를 쓰기 전에 여러 AI 페르소나와 대화하며 막연한 아이디어를 기획안으로 구체화·검증하는 멀티 AI 기획 공간을 새로 추가한 주요 릴리즈. 페르소나 역할 배정과 모델 자동 폴백, 온보딩 개편을 함께 담았다.

### Added

- **기획방 — 멀티 AI 페르소나 대화** — 네 명의 페르소나가 각자의 AI 모델로 기획 대화에 참여한다: **클로이**(claude · 설계) · **지오**(codex · 검토) · **미나**(agy · 탐색) · **딥시기**(opencode · 조교). 설계자가 아이디어를 화면·흐름으로 구체화하고, 검토자가 빠진 조건·위험한 가정을 짚고, 탐색자가 실제 사용 상황을 묻고, 조교가 알기 쉽게 풀어 준다.
- **역할 1:1 재배정** — Settings의 "기획방 페르소나"에서 각 AI가 맡을 역할(설계/검토/탐색/조교)을 고를 수 있다. 한 명의 역할을 바꾸면 그 역할을 갖고 있던 AI와 서로 맞바뀌어 항상 네 역할이 모두 채워진다. 페르소나의 이름과 모델은 한 덩어리로 고정(이름이 모델 작명: 클로이=Claude, 딥시기=DeepSeek)이라 이름↔모델 정합성이 유지된다.
- **모델 자동 폴백** — 페르소나의 모델이 설치돼 있지 않거나 로그인이 만료되면, 설치된 다른 모델로 자동 대체해 답한다. 대체가 일어나면 메시지에 **"○○로 대체됨 · 로그인 필요/미설치"** 배지로 이유까지 안내한다.
- **페르소나 ON/OFF** — 기획방에서 특정 페르소나를 끄고 켤 수 있다.
- **기획 세션 관리** — 여러 기획 세션을 만들고, 목록에서 불러오거나 이어서 진행한다. 홈 화면에 기획방 진입점을 추가했다.
- **기획 카드** — 대화에서 도출된 결정을 카드로 모으고 동의·보류·빼기 버튼으로 상태를 관리한다. 확정 카드는 시각적으로 강조되며, 마감 준비도(readiness) 게이트로 기획 완성도를 확인한다.
- **계획서 저장** — 기획 대화를 마크다운 계획서로 저장한다(프로젝트 source 폴더 연동).
- **온보딩 개편** — Claude Code 설정 패널, 설치된 AI 도구 자동 감지·선택, 기능별 색상 코딩(MCP=청록 · Claude=주황 · 시스템 상태=초록), WSL 설치 안내.
- **대화 최하단 이동 버튼** — 대화가 길어질 때 맨 아래로 내려가는 ↓ 버튼을 기존 ↑ 버튼과 함께 제공한다.

### Changed

- **기획방 백엔드 단일화** — 페르소나↔역할·모델 해석과 자동 폴백을 전역 설정(`~/.vibelign/gui_config.json`)을 단일 소스로 통일했다. 대화 경로(Rust)와 계획서 생성 경로(Python)가 동일한 규칙을 따른다.
- **Code Explorer 즉시 로드** — `project_map` 로딩 경로를 개선했다.

### Fixed

- **Windows에서 `.cmd`/`.bat` CLI 셔임 인식** — 윈도에서 codex/claude 등이 npm 셔임(`.cmd`)으로 설치된 경우 기획방 대화 경로가 모델을 못 찾던 문제를 해결. `.exe` 만이 아니라 `.exe`/`.cmd`/`.bat`/`.com` 을 찾고, 직접 실행할 수 없는 무확장 git-bash 셔임은 건너뛴다. (rustc ≥ 1.77.2 의 `Command` 가 `.cmd`/`.bat` 를 cmd.exe 경유로 안전 실행)
- **Settings 마지막 카드 잘림** — Settings 맨 아래 "기획방 페르소나" 카드의 하단 테두리·그림자가 WKWebView 에서 잘리던 문제를 카드 하단 여백으로 해결.
- 그 외 기획방·온보딩 관련 다수 수정.

---

## [2.2.25] — 2026-05-29

Code Explorer 사이드바에 설정·데이터 파일이 보이지 않던 문제를 바로잡은 수정 릴리즈.

### Fixed

- **`.toml`/`.yaml`/`.yml` 파일이 사이드바에 노출** — 트리 표시용 화이트리스트(`EXPLORER_FILE_EXTENSIONS`)에 `toml`/`yaml`/`yml` 이 빠져 있어, 읽기(`CODE_READ_EXTENSIONS`)는 지원하면서도 사이드바 트리에는 안 보이던 비대칭을 해소. `pyproject.toml`·`Cargo.toml`·`*.yaml` 등이 이제 트리에 나타난다. 설정/데이터 파일은 새 `data` 카테고리로 분류돼 사이드바에서 소스 코드(녹색)와 구분되는 `other`(회색)로 표시된다. 회귀 테스트 추가 (`vibelign-gui/src-tauri/src/code_access.rs`). (`json` 은 대용량 데이터 파일·읽기 캡 초과 우려로 의도적으로 제외)

---

## [2.2.24] — 2026-05-29

Windows 에서 Code Explorer 가 느리고 파일 클릭마다 콘솔 창이 깜빡이던 두 가지 플랫폼 이슈를 바로잡은 수정 릴리즈. (macOS/Linux 동작 불변)

### Fixed

- **Windows Code Explorer 로딩 지연 해소** — Code Explorer 의 4개 Tauri 커맨드(`read_code_file`/`list_code_files`/`read_code_file_diff`/`list_changed_files`)가 동기 `#[tauri::command] fn` 이라 Tauri 메인 스레드에서 서로 직렬 실행됐다. `git status --untracked-files=all`·`git show` 의 프로세스 spawn 비용이 큰 Windows 에서 git 을 타지 않는 빠른 코드 본문 읽기(`read_code_file`)까지 그 뒤에 줄 서서 막혀 UI 가 멈췄다(맥은 spawn/status 가 싸서 체감 안 됨). 다른 커맨드들이 이미 쓰는 `async` + `spawn_blocking` 패턴으로 통일해 메인 스레드를 막지 않고 4개가 실제로 병렬 실행되게 했다. 코드 본문은 즉시 뜨고 변경 배지/diff 는 뒤따라 채워진다 (`vibelign-gui/src-tauri/src/commands/code.rs`).
- **Windows 콘솔 창 깜빡임 제거** — 코드 파일을 클릭할 때 `git show`(`code_diff.rs`)·트리 새로고침 시 `git rev-parse`/`git status`(`git_status.rs`) 의 git spawn 에 `CREATE_NO_WINDOW` 플래그가 빠져 있어 GUI 가 콘솔 자식을 띄울 때 Windows 콘솔 창이 깜빡였다 사라졌다. 코드베이스의 다른 spawn 들과 동일한 패턴(`apply_no_window`)을 적용해 제거 (`vibelign-gui/src-tauri/src/code_diff.rs`, `git_status.rs`).

### Changed

- **GUI CI 에 OS 선택 입력 추가** — `gui.yml` 의 `workflow_dispatch` 에 `target`(all/windows/macos) 입력을 두고 매트릭스를 동적으로 구성해, 수동 실행 시 특정 OS 만 빌드할 수 있게 했다. push/PR 등 입력이 없는 이벤트는 기존대로 양쪽 모두 빌드 (`.github/workflows/gui.yml`).

---

## [2.2.23] — 2026-05-28

Code Explorer Diff 뷰의 **체크포인트 기준선(baseline) 선택 정합성**을 바로잡은 수정 릴리즈.

### Fixed

- **체크포인트 baseline 폴백 + 비-체크포인트 디렉터리 필터** — git 기준선이 없을 때 Diff 뷰가 사용하는 체크포인트 baseline 선택을 두 가지 면에서 수정. ① 가장 최근 체크포인트 하나만 확인하고 그 안에 해당 파일이 없으면(예: 삭제 후 재생성) 기준선 없음으로 처리하던 것을 *파일을 가진 가장 최근 체크포인트로 폴백*하도록, ② `.vibelign/checkpoints/` 아래 timestamp 형식이 아닌 디렉터리가 사전순 정렬상 끼어들어 baseline 을 가로채던 것을 *timestamp 디렉터리만 후보로 제한*하도록 변경. 회귀 테스트 2건 추가 (`vibelign-gui/src-tauri/src/code_diff.rs`).

### Changed

- **내부 정리** — `CodeFileTree` 에서 카테고리 색(`categoryColor`) 중복 조회를 이미 바인딩된 지역변수 재사용으로 정리(동작 불변) (`vibelign-gui/src/components/code-explorer/CodeFileTree.tsx`).

---

## [2.2.20] — 2026-05-27

Code Explorer 사이드바를 코드 전용에서 **문서 포함**으로 확장하고, 카테고리별 색상 구분을 추가한 GUI 가독성 릴리즈. 추가로 `vib/*.ts` 도메인 모듈과 DocsViewer 테스트에 누락돼 있던 ANCHOR 마커를 일괄 보강.

### Added

- **Code Explorer 사이드바에 `docs/` 트리 + `.md` 미리보기** — 엔진 `project_scan`(코드 분석 파이프라인과 공유) 대신 Tauri 전용 `list_code_files` 스캐너를 신설해 docs/superpowers/specs/wiki/release_notes 의 `.md` 파일이 사이드바에 노출되고 뷰어에서 Markdown 언어로 열림. anchor_tools/patch_suggester/doctor_v2/risk_analyzer 등의 코드 도메인 정책은 영향 없음 (`vibelign-gui/src-tauri/src/code_access.rs` + `commands/code.rs` + `lib.rs`, `vibelign-gui/src/lib/vib/code.ts`).
- **카테고리 자동 분류 + 4색 탭 컬러** — code(녹 `#22c55e`) / docs(주 `#f97316`) / tests(보라 `#a855f7`) / other(회 `#9ca3af`). 파일은 확장자·경로로, 디렉터리는 하위 파일의 다수결로 자동 판정. 사이드바 행에 4px 왼쪽 액센트 바 + 카테고리 색 배경 틴트(디렉터리 ~40%, 파일 ~25%) + 8px 도트(폴더 채움/파일 외곽선) 3중 표지로 가독성 강화 (`vibelign-gui/src/lib/code-explorer/tree.ts`, `components/code-explorer/CodeFileTree.tsx`).

### Changed

- **`vibelign-gui/src/lib/vib/*.ts` ANCHOR 마커 일괄 보강** — anchor/apiKeys/backup/code/core/docs/errorLogs/guard/index/memory/normalizers/onboarding/recovery/system/types/watch 16 모듈 + DocsViewer epoch/performance 테스트 2건에 `// === ANCHOR: NAME_START === / _END ===` 추가. `vib guard --strict` 의 앵커 경계 검증이 GUI 도메인 코드에도 일관 적용됨.
- **`opencode.json` / `vibelign-core/examples/bench_tokenizer.rs` / `vibelign-gui/src/components/ScrollToTopButton.tsx` / `vibelign/core/docs_html_visualizer.py` / `vibelign-gui/src/test/setup.ts` / `vitest.config.ts`** 소소한 보강 함께 묶음.

### Verified

- Rust `code_access` 단위 테스트 10/10 (신규 explorer scan/markdown read 2건 추가). 프런트 code-explorer vitest 5/5 (카테고리 분류 + 디렉터리 다수결 테스트 추가). `tsc --noEmit` 0 errors. Windows 호환성 점검 (UNC 경로/심볼릭 스킵/예약 디바이스명 거부) 통과.

---

## [2.2.19] — 2026-05-27

VibeLign GUI 에 **Code Explorer** 탭 추가. 프로젝트 소스 트리를 폴더 단위로 탐색하고 선택한 파일을 read-only 로 미리볼 수 있다. 파일 목록은 기존 Rust `project_scan` IPC 를 재사용하고, 코드 읽기는 별도 Tauri `read_code_file` command + `code_access.rs` 보안 가드로 처리한다. DocsViewer 의 문서 read 정책은 건드리지 않고 코드 전용 도메인으로 분리.

### Added

- **GUI `CODE EXPLORER` 탭** — 좌측 폴더 트리(1단계 기본 펼침 + 검색 시 자동 펼침) / 우측 read-only 코드 뷰어(라인 번호, 언어·줄수·바이트 표시). 검색은 경로·카테고리·import 매칭. page/layout/tree/viewer/toolbar/line 단위로 컴포넌트를 분리해 `App.tsx` 는 탭 wiring 만, `CodeExplorer.tsx` 는 page state/데이터 로딩만 담당.
- **Rust `read_code_file` command + `code_access.rs` 보안 가드** — 프로젝트 루트 밖 탈출(`..`, 절대경로, Windows UNC/드라이브, symlink) 거부, hidden/generated 디렉터리(`.git`, `node_modules`, `target` 등) 제외, Windows 예약 디바이스명(`NUL`, `CON`, `COM1`…) 차단, 지원 확장자 allowlist, 바이너리/비-UTF-8 거부, 코드 1MB·데이터(json/yaml/toml) 5MB 크기 캡. BOM strip + CRLF 정규화 후 SHA-256 해시 반환.
- **Diff 확장 seam (`CodeDiffViewer`)** — red/green diff 렌더링 컴포넌트를 미리 분리해 둠. 실제 diff 데이터 소스가 붙기 전까지 v1 에서는 비활성(미마운트).

### Verified

- Rust `code_access` 가드 단위 테스트 8건 통과(전체 src-tauri crate 60건 통과). 프런트 tree/filter 유틸 vitest 4건 통과. `tsc && vite build` 통과. `vib guard --strict` 앵커/보호경로 위반 0건.

---

## [2.2.18] — 2026-05-19

기획/스펙 문서가 실제 코드와 어긋난 채 남아 있던 위험을 차단하기 위한 docs 동기화 릴리즈. 추가로 vibelign-gui 의 production TypeScript 빌드가 vitest 픽스처를 끌어가 type error 를 뱉던 노이즈를 정리.

### Changed

- **superpowers plan/spec 5건 헤더에 "현재 구현 대조 메모 (2026-05-14)" 추가**: 문서가 비전을 담은 미래 설계인지, 이미 shipped 된 사실 기록인지를 첫 화면에서 분리해 읽도록.
  - `docs/superpowers/plans/2026-05-13-mcp-host-llm-pivot-plan.md`: `anchor_read_content`/`project_map_get` MCP primitive 와 baseline lock, `user_requests.json` 데이터셋이 이미 mainlined 됐음을 명시 — 남은 결정은 도구 추가가 아니라 Gemini/`vib patch --ai` 경로 deprecation 또는 host-LLM 중심 full migration 의 순서.
  - `docs/superpowers/plans/VibeLign-규칙수정안-3.md`: pre-commit 외에 post-commit 기록 블록도 있고, 줄수 enforcement 는 별도 스크립트가 아니라 `vib guard --strict` 안으로 들어가야 함. 300/500 줄수 차단 + legacy baseline 동결은 아직 미반영, `risk_analyzer.py` 도 500/800/1000 단계.
  - `docs/superpowers/plans/VibeLign-원클릭설치-기획안_초안.md`: `claude doctor` 가 non-TTY/Ink raw-mode 한계로 v1 성공 조건에서 제외, PTY 기반 "첫 응답 토큰 수신" 검증은 장기 목표. v1 현실 기준은 `claude --version` + 대표 셸 PATH + 로그인 안내.
  - `docs/superpowers/plans/VibeLign-지식저장고-기획안.md`: `vib knowledge`, `docs/knowledge/`, `/know` slash, knowledge-기반 patch 주입 모두 미구현. MVP 1단계 = 수동 저장 + docs viewer 노출 + 원본 보존 정책으로 범위 축소, 의미 검색/자동 주입/export 는 후속 RFC.
  - `docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`: 사용자 실요청 자연 분포 측정 결과 (rule-based `0/6`, host-LLM flow `6/6`) 가 v2.2.10 changelog 에 이미 기록됐고 `tests/benchmark/user_requests.json` 도 추가됐음.
- **`vibelign-gui/tsconfig.json` 에 test exclude 추가**: `src/**/__tests__/**`, `src/**/*.test.ts`, `src/**/*.test.tsx`, `src/test/**` 를 제외. `tsc && vite build` 가 vitest 픽스처를 production 타입체크에 끌어가 가짜 에러를 뿜던 회귀 정리. vitest 자체 실행은 영향 없음.

### Verified

- 디버그 세션에서 발견된 회귀 추적 결과는 v2.2.13 sidecar `RUST_ENGINE_INTEGRITY_FAILED` 가 원인이었음을 재확인 — v2.2.14+ self-heal 적용 환경에서 `vib checkpoint` 8회 + GUI "지금 저장" 2회 + GUI 재시동 모두 audit trigger 가 `DELETE FROM checkpoints` 0건을 기록. 신규 코드 변경 없음, 기존 fix 가 그대로 유효함이 확인됨.

---

## [2.2.17] — 2026-05-19

PyPI publish 워크플로의 macos-13 runner 큐 적체 (시간당 1개 슬롯 정도) 로 v2.2.12 이후 PyPI 배포가 4시간 넘게 묶이던 회귀를 차단. macOS wheel 빌드 runner 를 Apple Silicon (macos-latest) 로 교체.

### Changed

- **`publish.yml` macos-13 → macos-latest** (Apple Silicon arm64): macos-13 (Intel x86_64) runner pool 이 GitHub-hosted Actions 에서 만성적으로 큐 적체. v2.2.12-v2.2.16 publish 가 1-4 시간 단위로 묶임. macos-latest (Apple Silicon, 큐 거의 즉시) 로 교체해 publish 회복. sdist build 도 macos-latest 로 이동.

### Notes

- macOS x86_64 (Intel Mac) 사용자는 PyPI wheel 미제공 → sdist 로 설치 (Rust 툴체인 필요). 사용자 본인은 이미 `npm run tauri build` 환경이라 Rust 보유. 다른 Intel Mac 사용자가 생기면 `pip install vibelign --no-binary vibelign` 또는 GUI 의 v2.2.14+ self-heal 기반 로컬 빌드 권장.
- 큐에 박혀있던 v2.2.12-v2.2.16 publish 워크플로 5개 모두 수동 취소 — v2.2.17 부터 깨끗한 큐로 진행.

---

## [2.2.16] — 2026-05-19

Phase 9 cross-platform CI 가 v2.2.11 이전부터 빨간색이던 회귀 2건을 제거. Rust 엔진 migration 부수효과로 깨졌던 MCP checkpoint handler 테스트 페어 동기화.

### Fixed

- **`handle_checkpoint_create` 가 file_count=0 도 blocked 로 audit** (`vibelign/mcp/mcp_checkpoint_handlers.py`): Rust 엔진은 빈 workspace 에서도 file_count=0 summary 를 반환해서 handler 가 잘못 `success` 로 audit 하던 회귀. `summary is None or summary.file_count == 0` 둘 다 "변경사항 없음" 으로 통일.
- **`tests/test_mcp_checkpoint_handlers.py` 가 router.list_checkpoints 사용** (`tests/test_mcp_checkpoint_handlers.py`): 옛 `vibelign.core.local_checkpoints.list_checkpoints` (filesystem) 가 Rust 엔진의 SQLite 결과를 못 봐서 `len(list_checkpoints) == 0` 으로 실패하던 회귀. `router.list_checkpoints` 로 import 갱신해 엔진 추상화 너머의 실제 데이터 검증.

### Verified

- `tests/test_mcp_checkpoint_handlers.py` 12 통과 (이전 2 실패 → 0 실패)
- `tests/test_cross_platform_paths.py` + `tests/test_checkpoint_cmd_wrapper.py` + `tests/test_mcp_checkpoint_handlers.py` (Phase 9 의 정확한 매트릭스) 21 전부 통과
- macOS + Windows GitHub Actions Phase 9 다음 빌드에서 첫 green 예상

### Notes

- v2.2.11 부터 Phase 9 가 빨갛던 원인 — Rust 엔진 migration 시 테스트가 옛 Python checkpoints API 를 그대로 참조하고 있었던 잔재.

---

## [2.2.15] — 2026-05-19

v2.2.13 의 post-commit hook v4 가 OpenCode 등 일부 LLM commit tool 에서 자동 백업이 누락되는 회귀를 일으켜 (원인 미특정), v3 의 분기 순서를 복구.

### Fixed

- **post-commit hook v5 — 분기 순서 복구** (`vibelign/core/git_hooks.py`): v4 에서 절대 경로 분기를 최우선으로 두는 구조가 OpenCode + GPT-5.5 환경에서 자동 백업을 전부 누락시키던 회귀 (`vib history` 가 commit 이후 갱신되지 않음). v3 의 PATH 기반 분기 순서를 다시 앞으로 옮기고, 절대 경로 분기는 마지막 fallback 으로 강등 — PATH 가 빈약한 GUI commit tool 케이스만 커버하도록 범위 축소. marker v5 로 bump, v1-v4 hook 자동 교체.

### Why

`예전 버전에서는 문제 없었다` 는 사용자 신호 + 직접 simulate 시 hook 정상 동작 + 실제 commit 환경에서 7개 commit 연속 백업 누락 (`.git/hooks/post-commit` 발화 자체가 의심) 의 신호 조합. v3 동작을 보존하면 OpenCode 환경 회귀 즉시 해소, 절대 경로 분기는 PATH 가 빈약한 GUI commit tool 케이스만 last-resort 로 커버.

### Verified

- `tests/test_git_hooks_post_commit.py::test_hook_contains_absolute_path_fallbacks_at_top` assertion 을 절대 경로 분기가 PATH 분기보다 **뒤에** 위치하는지 검증하도록 갱신.
- `tests/test_git_hooks*.py` + `tests/test_rust_engine_discovery_integrity.py` 32 통과.

### Notes

- 다음 `vib start` 실행 시 v1-v4 hook 자동으로 v5 로 교체.
- OpenCode/git-master agent 가 git hook 을 우회하던 정확한 원인은 별도 추가 조사 필요. v5 는 그 원인이 무엇이든 v3 와 동일한 분기 순서를 거치므로 회귀 없음 보장.

---

## [2.2.14] — 2026-05-19

v2.2.13 의 CI codesign manifest 보강이 GitHub Actions 빌드만 커버해서, **로컬 빌드 (사용자 직접 `npm run tauri build`)** 에서는 같은 `RUST_ENGINE_INTEGRITY_FAILED` 가 그대로 재발하던 회귀를 차단. integrity 검사를 런타임 self-heal 로 격상.

### Fixed

- **macOS 번들 `vibelign-engine` integrity self-heal** (`vibelign/core/checkpoint_engine/rust_engine/discovery.py`): 매니페스트와 binary hash 가 어긋날 때, `codesign --verify --strict` 가 통과하는 binary 는 정상 codesigned artifact 로 간주하고 매니페스트를 갱신해 회복한다. macOS 한정 — Windows/Linux 는 codesign 신뢰 신호가 없어 기존대로 실패. 로컬 빌드, CI 빌드, 사용자가 직접 재서명한 빌드 모두 동일하게 동작.

### Why

v2.2.13 의 `gui.yml` 수정은 CI 의 `codesign --deep` 직후 매니페스트를 재생성했지만, 사용자가 로컬에서 직접 `npm run tauri build` (혹은 Tauri 의 cargo bundle 단계) 를 실행하면 같은 binary mutation 이 일어나도 manifest refresh step 이 없어 같은 증상 재발. 빌드 경로별 후처리를 강제하기보다 vibelign 자체가 codesign 검증을 통과한 binary 를 신뢰하도록 격상하는 게 robust.

### Verified

- `tests/test_rust_engine_discovery_integrity.py` 8 통과 (darwin self-heal 회귀 테스트 3건 신규 — codesigned 회복, 미서명 실패 유지, non-darwin self-heal 금지).
- `tests/test_git_hooks*.py` 24 통과 (v2.2.13 변경 회귀 없음).

### Notes

- macOS Big Sur+ 의 linker 자동 ad-hoc 서명, Tauri 의 cargo bundle 단계 서명, 사용자 수동 `codesign --deep -s -` 모두 같은 경로로 처리.
- 기존 v2.2.13 GUI 설치본 즉시 우회 (v2.2.14 빌드 받기 전까지):
  ```
  ENGINE="/Applications/vibelign-gui.app/Contents/Resources/vib-runtime/_internal/vibelign/_bundled/vibelign-engine"
  shasum -a 256 "$ENGINE" | awk '{print $1"  vibelign-engine"}' > "$ENGINE.sha256"
  ```

---

## [2.2.13] — 2026-05-19

자동 백업 정합성 hotfix — GUI `RUST_ENGINE_INTEGRITY_FAILED` 폭발과 GUI commit tool 환경의 post-commit 자동 백업 누락 동시에 해소.

### Fixed

- **GUI `vibelign-engine` integrity check 실패** (`.github/workflows/gui.yml`): macOS `codesign --deep` 가 bundled binary 끝에 서명 blob 을 추가해 사전 생성된 `.sha256` 매니페스트와 hash 가 어긋나던 회귀. codesign 직후 매니페스트를 재생성하도록 step 보강. GUI 의 `vib history`, BACKUPS 페이지 등 Rust 엔진 호출이 `RUST_ENGINE_INTEGRITY_FAILED: integrity check failed` 로 폭발하던 issue 해결.
- **post-commit 자동 백업 PATH 의존성** (`vibelign/core/git_hooks.py`): hook 의 모든 fallback 이 `command -v vib` 같은 PATH lookup 에만 의존해서, Sourcetree / VS Code / Tower 처럼 launchd PATH 만 상속해 `~/.local/bin` 이 빠진 commit tool 에서 자동 백업이 통째로 누락되던 회귀. install 시점에 `shutil.which('vib')` / `shutil.which('vibelign')` / `sys.executable` 절대 경로를 캡처해 PATH 분기보다 먼저 시도하도록 hook 구조 변경. marker 를 v4 로 bump 하고 v1-v3 hook 자동 교체.

### Changed

- **CI 매트릭스에서 Linux 제외** (`.github/workflows/publish.yml`, `python.yml`): wheel publish 가 `[macos-13, windows-latest]` 만 build, sdist 는 macos-13 로 이동. `python.yml` 의 smoke build 도 `macos-latest` 로 이동. Linux user 대상 PyPI wheel 제공 중단.

### Verified

- `tests/test_git_hooks.py` + `tests/test_git_hooks_post_commit.py` 24 통과 (절대 경로 분기 회귀 테스트 신규 1건, marker v4 자동 교체 회귀 포함).
- `_build_post_commit_block()` 출력 수동 검증 — 절대 경로 3개 fallback (vib, vibelign, python -m vibelign) 가 PATH 분기 위에 위치.

### Notes

- 사용자는 `vib start` 한 번 다시 돌리거나 GUI 를 새 릴리즈로 업데이트하면 양 issue 자동 해소.
- 기존 v2.2.12 GUI 설치본에서 즉시 우회하려면: `cp ~/.local/share/uv/tools/vibelign/lib/python*/site-packages/vibelign/_bundled/vibelign-engine /Applications/vibelign-gui.app/Contents/Resources/vib-runtime/_internal/vibelign/_bundled/vibelign-engine`.

---

## [2.2.12] — 2026-05-19

vib 의 pre-commit hook 이 사소한 구조 drift 만으로 commit 을 막던 문제를 해소. secrets 차단은 유지하면서 guard 실패는 advisory(경고만) 로 강등.

### Changed

- **pre-commit hook 유연화** (`vibelign/core/git_hooks.py`): hook 템플릿을 `pre-commit-enforcement v3` 로 bump. `vib guard --strict` 가 실패해도 commit 은 통과시키고 stderr 에 한 줄 알림만 출력. `vib secrets --staged` 는 그대로 차단 (시크릿 누출 위험은 비대칭이라 보수적으로 유지).
- **escape hatch 환경변수 추가**:
  - `VIBELIGN_SKIP_HOOK=1 git commit ...` — 1회용 우회 (`--no-verify` 의도-명확 버전, vib 자체가 실행되지 않음).
  - `VIBELIGN_STRICT_GUARD=1` — strict 팀용 opt-in. 옛 차단 동작 복귀.
- **기존 hook 자동 재설치** (`_HOOK_MARKER_RE`): `secrets-pre-commit v1` / `pre-commit-enforcement v1` / `pre-commit-enforcement v2` 어느 marker 든 다음 `vib start` 에서 v3 로 자동 교체. 사용자 수동 정리 불필요.

### Why

사용자 보고: `vib guard --strict` 가 commit 시점에 자잘한 anchor drift 를 잡아 commit 이 여러 차례 실패. secrets 누출 같은 비가역 실수는 차단을 유지해야 하지만, 구조 drift 는 `vib doctor` / 다음 작업에서 다시 잡히므로 commit 차단까지는 과함. (이번 release 자체가 `pre-commit-enforcement v3` 동작 변경이라, 새 marker 가 사용자 환경에 도달하면 즉시 효과 발생.)

### Verified

- `tests/test_git_hooks.py` 13 개 통과 (advisory 동작, STRICT_GUARD opt-in, SKIP env 우회, v1/v2 marker 자동 교체 모두 회귀 테스트).
- `tests/test_git_hooks_post_commit.py` 10 개 통과 (post-commit hook 회귀 없음).
- 전체 스위트 1383 passed, 14 failed — 모든 실패는 main 에서도 동일하게 재현되는 pre-existing 항목 (stash 검증).

### Notes

- 기존 `.git/hooks/pre-commit` 이 `secrets-pre-commit v1` 형태인 사용자도 다음 `vib start` 한 번이면 자동 교체.
- guard 차단이 정말 필요한 팀은 `~/.zshrc` / shell rc 에 `export VIBELIGN_STRICT_GUARD=1` 박아두면 옛 동작 유지.

---

## [2.2.11] — 2026-05-13

v2.2.10 측정 데이터(`vib patch` baseline 0/7 on 사용자 실 자연어 요청) 후속으로, GUI 의 Patch 카드를 노출에서 제거. CLI `vib patch` 는 변경 없음.

### Removed

- **GUI Patch 카드 노출** (`vibelign-gui/src/hooks/useCardOrder.ts`): `DEFAULT_CARD_ORDER` 에서 `"patch"` 토큰 제거. 신규/기존 사용자 모두 Home 카드 목록에서 더 이상 보이지 않음. 기존 사용자의 saved card-order 는 `useCardOrder.ts:26` 의 filter 가 자동 정리.

### Why

v2.2.10 데이터셋 7 entries 전부에서 `vib patch` 가 무관한 파일을 지목 (keyword trap):
- user-004: `--json` 키워드 → `vib_docs_build_cmd.py` (오답)
- user-007: `--preview` 키워드 → `vibelign-core/src/backup/restore/preview.rs` (오답, 무비판 실행 시 vib 의 `recover --preview` 기능 회귀 가능)

GUI 사용자가 이 카드의 부정확한 출력을 무비판적으로 따를 위험이 가장 큼. CLI 는 사용자가 직접 검토 후 적용하는 흐름이라 risk 가 다름.

### Notes

- CLI `vib patch` 명령: 변경 없음. 다음 마일스톤에서 별도 deprecation 검토.
- `PatchCard.tsx` import + `Home.tsx:115` 의 `case "patch":` 는 dead code 로 보존 — trivial re-enable 옵션 유지.
- `commandData.ts` 의 patch 명령 정의 + `Manual` / `Help` 페이지의 patch 문서는 보존됨.

### Verified

- `npm run build` (vibelign-gui) — 통과.
- `npm test` — pre-existing DocsViewer 2 fail 동일, patch-hide 무관.
- macOS/Windows GitHub Actions CI — 모두 SUCCESS (PR #8).

---

## [2.2.10] — 2026-05-13

VibeLign 정체성 pivot 시작점 — **host LLM(Claude Code/Cursor)이 MCP 도구로 직접 file:anchor 매핑**할 수 있는 PoC 인프라 mainlined. 부수로 BACKUPS 페이지네이션 + Explain 카드 옵션 정리.

### Added

- **MCP `anchor_read_content` 도구** (`vibelign/mcp/mcp_anchor_handlers.py`): host LLM 이 패치 전 앵커 내부 텍스트를 정확한 경계로 read. path traversal 방지(`fp.relative_to(root)`), `minLength: 1` 스키마 가드, `_START`/`_END` 접미사 자동 정규화 포함.
- **MCP `project_map_get` 도구** (`vibelign/mcp/mcp_misc_handlers.py`): 프로젝트 카테고리/파일/앵커 인덱스를 raw JSON 으로 반환. host LLM 이 자연어 요청을 정확한 파일에 매핑하기 위한 전역 컨텍스트 도구. non-dict shape 거부 + OSError 메시지 경로 누출 방지.
- **BACKUPS 탭 + DB Viewer rows pagination** (`FileHistoryTable.tsx`, `BackupDbRowList.tsx`): 페이지당 10개, "이전 / X / Y 페이지 · M–N / TOTAL / 다음" 푸터. 리스트가 누적되면 예전 항목 접근이 어려웠던 문제 해결. FileHistoryTable 은 검색어 변경 시 1페이지 리셋, 선택 항목이 다른 페이지에 있으면 자동 점프.
- **Baseline 회귀 락** (`tests/benchmark/test_patch_suggester_baseline.py`): rule-based `patch_suggester` 의 file/anchor 매칭 수치(14/20 file, 0/19 anchor) 락. sentinel-driven 검증으로 silent regression 방지.
- **수동 평가 runbook** (`docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`): host LLM 정확도 측정 절차 + 의사결정 트리 (성공/부분/실패별 다음 단계 명시).
- **User requests dataset** (`tests/benchmark/user_requests.json`): 사용자 실 자연어 수정 요청 6 entries (ambiguous case 의 plausible set 확장 포함).
- **PoC plan + decision artifacts** (`docs/superpowers/plans/2026-05-13-mcp-host-llm-pivot-plan.md`).

### Removed

- **Explain 카드의 `--write-report` / `--json` 옵션** (`vibelign-gui/src/lib/commandData.ts`): GUI 카드 flags 배열에서 두 bool 옵션 제거. CLI 의 동일 플래그는 그대로 지원 (다른 명령 - doctor, guard, patch - 도 영향 없음).

### Measured

- `vib patch` baseline vs host-LLM-driven flow 자연 분포 측정: **6 사용자 실 요청 중 baseline 0/6 (0%), fresh blind subagent 6/6 (100%)**. sample_project 인공 시나리오(baseline 14/20) 보다 자연 분포에서 gap 이 훨씬 큼이 입증됨.
- `vib patch "gui 익스플레인 카드에서 --write-report --json 옵션은 제거해줘"` → `vibelign/commands/vib_docs_build_cmd.py` (오답, JSON 키워드 함정 명시) vs host LLM 은 정답 `commandData.ts` 즉시 짚음. dogfooding 증거 (PR #5 description 부록 참조).

### Verified

- `cargo test --lib` (vibelign-core) — 회귀 없음.
- `cargo check` (vibelign-gui/src-tauri) — 0 errors.
- `npx tsc --noEmit` (vibelign-gui) — No errors found.
- `npm run build` (vibelign-gui) — Vite bundle 정상 생성.
- `pytest tests/test_mcp_*` — 41 passed (anchor handlers + read content + misc + project_map_get + dispatch + tool snapshot + baseline lock).
- macOS/Windows GitHub Actions CI — 모두 SUCCESS (PR #4 / #5 / #7).

### Notes

- Gemini 경로 (`vib patch --ai`, `vibelign/core/ai_codespeak.py`) 는 본 릴리즈에서 변경 없음. 평가 결과(0% vs 100% gap)가 일관됨에 따라 다음 마일스톤에서 deprecation 검토.
- 신규 MCP 도구는 Claude Code/Cursor 가 vibelign-mcp 등록 시 자동 노출. CLI/GUI 동작은 변경 없음.

---

## [2.2.9] — 2026-05-13

v2.2.8 의 scroll-to-top floating 버튼이 mac/Windows 양쪽에서 안 보이던 issue 의 패치 릴리즈.

### Fixed

- **scroll-to-top 버튼 — 실제 scroll container 인식** (`ScrollToTopButton.tsx`): `brutalism.css` 의 `.app-layout { height: 100vh; overflow: hidden }` + `.page-content { flex: 1; overflow-y: auto }` 구조라 실제 scroll container 는 `window` 가 아닌 `.page-content`. v2.2.8 의 listener 가 `window.addEventListener("scroll")` + `window.scrollY` 만 사용 → inner container 의 scroll 못 잡아 버튼 visibility toggle 미발동. 수정: `document.addEventListener("scroll", ..., { capture: true })` 추가 (scroll event 는 bubble 안 하지만 capture phase 에서 받음). `getActiveScrollContainer()` helper 로 `.page-content` element 찾고, `container?.scrollTop ?? window.scrollY` 로 visibility 판정, click 시 container scrollTo 우선.

### Verified

- `npx tsc --noEmit` (vibelign-gui) → No errors found.

---

## [2.2.8] — 2026-05-13

GUI 의 두 UX issue 수정 — "복구 후보 추천 보기" 의 후보별 차이 정보 누락 + "CANVAS / RAW HTML" 화면의 iframe 잘림. 추가로 모든 페이지에 scroll-to-top floating 버튼.

### Added

- **scroll-to-top floating 버튼** (`ScrollToTopButton.tsx`): `window.scrollY > 300` 시 우하단에 표시되는 buttons (브루탈리즘 스타일, ↑ glyph). 클릭 시 `window.scrollTo({ top: 0, behavior: "smooth" })`. App root level 에 한 번 render 되어 모든 page (Home / Doctor / DocsViewer / BackupDashboard / ErrorLogs / Settings / Onboarding) 공통 사용.

### Fixed

- **GUI 복구 후보 추천 — AI candidate-specific reason 추가 표시 + 문구 친화화** (`RecoveryOptionsCard.tsx`): 3 후보가 모두 동일한 "근거" 문구를 보이던 issue. 진짜 차이를 표현하는 LLM `candidate.reason` 필드가 GUI 에 표시 안 됨이 원인. `<div>AI 설명: {candidate.reason}</div>` 추가로 candidate-specific 설명 표시 (한국어 phrase 시 LLM 이 한국어 reason 반환). rule-based 5 항목 문구도 기술용어 제거 ("커밋 직후 저장" → "코드 저장 직후 만든 백업" / "최근 검증 기록 없음" → "확인 안 한 시점" 등).
- **GUI CANVAS / RAW HTML 화면 — content-aware iframe 높이 + viewport-fit** (`CanvasViewPane.tsx`, `RawHtmlCanvasPane.tsx`): 두 view mode 의 iframe 이 markup 휴리스틱 추정에 의존하던 fixed-height 사용 → 추정 부족 시 content 잘리고 iframe 내부 스크롤바 생성. `sandbox="allow-same-origin"` 추가 (scripts/forms 여전히 disabled) + `onLoad` 핸들러로 `contentDocument.documentElement.scrollHeight + body.scrollHeight max + 24px margin` 측정 → height state 갱신. `minHeight: calc(100vh - 200px)` 추가로 short content 도 app window viewport 만큼 차지. 결과: content 가 짧으면 viewport-fit, 길면 page natural scroll (왼쪽 사이드처럼). iframe 안 별도 스크롤바 없음.

### Verified

- `cargo test --lib` (vibelign-core) → 145 passed.
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `npx tsc --noEmit` (vibelign-gui) → No errors found.
- `pytest test_recovery_*` → 32 passed, 0 회귀 (recovery 변경 없음, agent.py 의 prompt 축소는 v2.2.7 의 변경).

### Notes

- 본 릴리즈는 모두 user-facing UX fix — 측정/lessons 적용보다 직접 보고된 issue 의 정직한 수정.
- CanvasViewPane 와 RawHtmlCanvasPane 가 같은 iframe + fixed-height anti-pattern 이었음 — 두 component 모두 동일 fix 적용.

---

## [2.2.7] — 2026-05-13

GUI 의 "복구 후보 추천 보기" (Recovery 패널) 첫 호출 wall 25s → 13.6s (~46% 가속). `_compact_candidate_payload` 의 `commit_message` 가 LLM prompt 의 49% (28KB 중 13.8KB) 를 차지하던 것을 subject + 200자 cap 으로 축소. 추가로 score_path Rust port 트랙의 Session 1 probe artifacts (`score_path.rs::meaningful_overlap` + 5 parity tests + ipc variant) 가 dormant library 로 보존됨 — 트랙 자체는 §9 retraction 으로 종료.

### Performance

- **Recovery 후보 추천 wall ~46% 단축**: `vib recover --recommend --phrase ...` 의 첫 호출 (cache miss) wall **25s → 13.6s** 측정 확인. 원인은 LLM prompt 크기 (28KB) 의 49% 가 commit_message 본문이었던 것 — `_compact_candidate_payload` 가 commit 의 subject 첫 줄 + 200자 cap 으로 보내도록 변경. prompt 28,203 → 15,381 chars (-46%), Gemini Flash 응답 시간이 input 크기에 ~linear 라 wall 도 동일 비율로 감소. quality 영향 없음 (LLM 추천 결정은 source/created_at/evidence_score/commit_boundary 등 metadata 필드에 의존, commit body 의 verbose handoff/plan 세부는 unused).

### Added

- **`vibelign-core/src/score_path.rs::meaningful_overlap`** (dormant library): Python `_meaningful_overlap` 의 1:1 port + 5 parity unit tests. score_path 트랙 §9 retraction 후 dormant 로 보존 — 미래 score_path 통째 port 시도 시 재사용 가능 + Python 측 코드 변경 시 cargo test 가 drift 감지.
- **`EngineRequest::MeaningfulOverlap` ipc variant** + handler dispatch: GUI/외부 consumer 가 호출 가능. 현재 default-off 의 routing 은 없음 (Python wire 는 retraction 시 revert 됨).

### Verified

- `cargo test --lib` (vibelign-core) → **145 passed** (이전 140 + 신규 score_path parity 5 tests).
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `pytest test_recovery_agent + test_recovery_planner + test_memory_recovery_schemas` → 32 passed, 0 회귀.
- Wall warm 측정 (cache invalidate 후 fresh phrase): `vib recover --recommend` 25.18s → **13.60s**.
- prompt 크기 capture: 28,203 chars → **15,381 chars (-46%)**, commit_message 합 13,800 → 1,204 (-91%).

### Notes

- 두 retraction lessons (tokenizer 트랙 §9 + score_path 트랙 §9) 의 측정-주도 룰이 본 가속의 prerequisite — cProfile/pyinstrument cumtime 신뢰 X, stub-patch wall diff + apples-to-apples harness + skip-rate measurement 가 진짜 leverage 식별. 자세한 기록은 `docs/superpowers/plans/2026-05-13-patch-suggester-tokenizer-rust-port-plan.md` §9 + `docs/superpowers/plans/2026-05-13-score-path-rust-port-plan.md` §9 참조.

---

## [2.2.6] — 2026-05-13

GUI 의 메모리 요약 카드를 Python sidecar 호출에서 in-process Rust 직결로 전환하여 마운트 지연을 제거하고, 향후 score_path 최적화 트랙의 토대로 한국어 토큰 분해 Rust 모듈 (`vibelign-core/src/tokenizer.rs`) 과 102 case × 6 함수 = 612 record 의 parity fixtures 를 dormant library 로 추가했습니다. `_normalize_korean_token` 의 hot loop 에서 매 호출마다 재실행되던 sort 도 module-level pre-sort 로 정리했습니다.

### Added

- **GUI memorySummary direct bridge** (Phase 3 PoC consumer #13): `SessionMemoryCard` mount 시 `runVib(["memory","show","--json"])` 호출이 in-process `callEngineDirect({command:"memory_summary_read"})` 로 전환. Python sidecar ~80ms 호출 제거. audit logging parity 완전 유지 (`project_root_hash` SHA256[:16] / 마이크로초 timestamp / sequence number / `.create_new(true)` 파일 락).
- **`vibelign-core/src/tokenizer.rs`**: `vibelign.core.patch_suggester` 의 6 leaf 토큰 함수 (`_decompose_korean_compound` / `_split_identifier_parts` / `_normalize_korean_token` / `_expand_token` / `tokenize` / `_intent_tokens`) 와 const table 113 entries 를 Rust 로 1:1 포팅. 현재 dormant library — score_path multi-session 트랙 진입 시 ipc 노출 예정.
- **`tests/fixtures/tokenizer_goldens/`**: 102 case × 6 함수 = 612 expected record JSON fixtures + `_regenerate.py` (Python source-of-truth 재캡처 스크립트, `uv run python ...` 으로 호출). cargo test 의 byte-equal parity assertion 으로 Rust 포팅 정확성 검증 + Python alias drift 자동 감지.
- **`vibelign-core/examples/bench_tokenizer.rs`**: isolated 1M iter bench. 향후 score_path Rust port 시 floor 측정 reference.

### Changed

- **`_normalize_korean_token` pre-sort**: `sorted(_KOREAN_PARTICLE_SUFFIXES, key=len, reverse=True)` 가 매 호출 (recover preview 시 609k 회) 마다 재실행되던 것을 module-level `_KOREAN_PARTICLE_SUFFIXES_SORTED` tuple 한 번에 고정. direct 1M iter 27% 가속 (1.97μs → 1.44μs / call), wall noise (caller-side set 처리가 wall dominate). 결정성/순서는 byte-equal 유지.

### Verified

- `cargo test --lib` (vibelign-core) → **140 passed** (이전 134 + 신규 tokenizer parity 6 tests / 612 assertion).
- `cargo check` (vibelign-gui/src-tauri) → 0 errors, 0 warnings.
- `npx tsc --noEmit` (vibelign-gui) → No errors found.
- `pytest tests/test_patch_*.py tests/test_recovery_planner.py` → 30 passed, 20 subtests passed.
- `cargo run --release --example bench_tokenizer` → 1M iter floor (intent_tokens 3,021 ns / expand_token 1,036 ns / decompose 5 ns per call).
- **Windows GNU cross-compile pre-flight** (`cargo check --target x86_64-pc-windows-gnu`, mingw-w64 mac local): vibelign-core 0 errors / vibelign-gui/src-tauri 0 errors + 5 cfg(unix) dead_code warnings (의도됨). 어제/오늘 신규 코드 (memory_audit / memory_state / sha2 / tokenizer / bench / pre-sort) 모두 Windows 호환 확인.

### Notes

- 사용자 체감 가속은 **memorySummary direct bridge** 에서. 나머지 변경 (tokenizer Rust 모듈 / fixtures / bench / pre-sort) 은 dormant library + tooling 으로 다음 트랙 (score_path 통째 Rust port) 의 토대.
- patch_suggester tokenizer 트랙 의 측정/디자인 + 단계 1/2 진척, 단계 3 retraction lessons (cProfile/pyinstrument cumtime over-attribution / cache hit ratio 가 wall 단축으로 직결되지 않음) 의 자세한 기록은 `docs/superpowers/plans/2026-05-13-patch-suggester-tokenizer-rust-port-plan.md` §9 참조.

---

## [2.2.5] — 2026-05-12

v2.2.4 GUI release build 에서 발견된 npm lockfile dependency metadata 오염을 복구한 패치 릴리즈입니다. Desktop GUI release 는 v2.2.5 로 재시도합니다.

### Fixed

- **GUI package-lock dependency metadata**: release version bump 가 dependency `json5@2.2.3` tarball URL 까지 바꾸지 않도록 lockfile 을 정상 재생성했습니다. `npm ci` 가 `json5-2.2.4.tgz` 를 찾다가 404 로 실패하던 문제를 해결합니다.

### Verified

- `npm ci` (vibelign-gui) → passed.
- `npm run build` (vibelign-gui) → passed.
- `npm run test` (vibelign-gui) → 2 files / 9 tests passed.
- `python3 -m build --sdist --wheel` → passed.
- Bridge contract check → `command string diff: missing=[] extra=[]`.

---

## [2.2.4] — 2026-05-12

v2.2.3 GUI release build 에서 드러난 legacy `backupCreate` import 호환성 누락을 복구한 패치 릴리즈입니다. PyPI v2.2.3 는 정상 publish 되었지만 Desktop GUI release 는 v2.2.4 로 재시도합니다.

### Fixed

- **GUI backup bridge compatibility**: 기존 `src/lib/vib` public API 의 `backupCreate` export 를 복구해, 아직 `backupCreate` 를 import 하는 GUI 화면도 domain module refactor 이후 정상 build 됩니다.

### Verified

- `npm run build` (vibelign-gui) → passed.
- Bridge contract check → `command string diff: missing=[] extra=[]`, `backupCreate export restored`.
- Branch GUI CI after fix → macOS + Windows passed.

---

## [2.2.3] — 2026-05-12

GUI bridge 구조를 domain module 로 분리하고, 개발 실행 로그의 Rust warning 을 정리한 패치 릴리즈입니다. 사용자-facing 동작은 유지하면서 이후 GUI 기능 확장 시 회귀 위험을 낮췄습니다.

### Changed

- **GUI vib bridge modularization**: `vibelign-gui/src/lib/vib.ts` 의 1,700+줄 command bridge 를 `core`, `docs`, `backup`, `onboarding`, `settings/API key`, `memory/recovery`, `guard/watch`, `errorLogs` domain module 로 분리했습니다.
- **Root import compatibility 유지**: 기존 GUI import 경로 `src/lib/vib` 는 compatibility barrel 로 유지되어 command card, docs, backup, onboarding, settings flow 의 import 변경 없이 동작합니다.

### Fixed

- **Rust dev warning cleanup**: Tauri dev 실행 시 보이던 `PathBuf` unused import warning 과 CAS prune wrapper dead-code warning 을 정리했습니다.

### Verified

- `npm run build` (vibelign-gui) → passed.
- `npm run test` (vibelign-gui) → 2 files / 9 tests passed.
- `cargo check --no-default-features` (vibelign-gui/src-tauri) → passed, Rust warnings cleared.
- Export/import snapshot → `exports=134`, `needed=99`, `missing=[]`.
- Tauri command string diff → `missing=[]`, `extra=[]`.

---

## [2.2.2] — 2026-05-10

DocsViewer 의 HTML 문서 보기 경험과 Windows 경로 안정성을 보강한 패치 릴리즈입니다.

### Added

- **DocsViewer Raw HTML artifact mode**: 선택한 문서를 sandboxed iframe 안의 읽기 쉬운 article-style HTML 로 렌더링합니다. scripts, same-origin, forms 권한은 열지 않아 원문 HTML 을 안전하게 확인합니다.
- **DocsViewer Split mode**: Source 와 Canvas 를 함께 보는 split 탭을 제공하며, 좁은 창에서도 탭 버튼은 항상 표시되고 내부 레이아웃만 1열로 반응합니다.
- **Canvas body preview**: `VisualSection.body_preview` 를 추가해 bullet/checklist/ordered/table row 일부를 원문 순서대로 보존하고, 기존 `heuristic-v2` cache 를 `heuristic-v3` 로 stale 처리합니다.

### Changed

- **Canvas visual renderer**: Canvas 를 문서 원문을 그대로 반복하는 화면이 아니라 `Document Control Map` 으로 재구성했습니다. Outline Source Order → Flow → Decisions → Actions → Risks → Glossary 순서로 보여줍니다.
- **DocsViewer tab affordance**: Source/Easy/Canvas/Raw HTML/Split 중 현재 선택된 탭을 검은 배경과 오렌지 그림자로 강조해 현재 위치를 즉시 알 수 있게 했습니다.
- **Iframe height behavior**: Canvas/Raw HTML/Split 의 고정 세로 제한을 제거하고 artifact 내용량에 따른 높이 추정으로 내부 iframe 스크롤을 줄였습니다.
- **Raw HTML readability**: heading/list/table/code block 스타일을 문서 읽기용으로 정리했습니다.

### Fixed

- **Windows extra doc source picker**: `C:\Repo` 와 `c:\repo\...` 처럼 드라이브/경로 대소문자가 다른 Windows 경로를 프로젝트 밖으로 오판하지 않도록, Windows식 absolute/UNC path 에서만 case-insensitive prefix 비교를 적용했습니다.
- **Split tab visibility regression**: UI 폭이 작아져도 Split 탭 버튼이 사라지지 않도록 수정했습니다.
- **Canvas source omission**: bullet 중심 섹션에서 summary 가 비어 Canvas 에 원문 preview 가 빠지던 문제를 backend artifact contract 로 해결했습니다.

### Verified

- `rtk npm run test -- --reporter verbose` (vibelign-gui) → 9 passed.
- `rtk npm run build` (vibelign-gui) → passed.
- `python3 -m unittest tests.test_doc_sources_cmd tests.test_docs_build_cmd tests.test_docs_visualizer` → 67 passed.
- `cargo test docs` (vibelign-gui/src-tauri) → 28 passed.

---

## [2.2.1] — 2026-05-10

릴리즈 파이프라인 수정 패치 릴리즈입니다. 코드 동작은 v2.2.0 과 동일합니다.

### Fixed

- **GitHub Actions release job 가드**: build job의 마지막 `Post Cache Rust build artifacts` 단계가 실패하면 자산이 다 만들어졌는데도 release job이 `needs:build` fail로 skip 되어 release에 자산 0개로 publish 되던 회귀 — release job 조건에 `always()` 추가로 cache 단계 실패와 무관하게 자산 업로드 진행.
- **Dead config 정리**: `vibelign-gui/src-tauri/tauri.updater.conf.json` 삭제. 워크플로우가 빌드 시점에 `tauri.updater.generated.conf.json` 을 만들어 `--config` 로 머지하므로 이 파일은 어디에도 참조되지 않는 dead config 였음.

---

## [2.2.0] — 2026-05-10

VibeLign 2.2.0 은 **GUI direct bridge (Phase 0+3 PoC) · 통합 에러 로그 뷰 · 자동 백업 가시성 · 다수의 silent 회귀 fix** 를 묶은 마이너 릴리즈입니다. macOS / Windows 모두 자동 혜택을 받는 cross-platform 변경입니다.

### Added

- **vibelign-core 라이브러리 노출 (Phase 0)**: `[lib] crate-type=["rlib"]` + `pub mod ipc` surface 만 노출. 기존 `vibelign-engine` 1-shot 바이너리는 그대로 유지하면서 라이브러리 소비자가 직접 `ipc::handler::handle()` 호출 가능.
- **Tauri ↔ vibelign-core direct bridge (Phase 3 PoC)**: 신규 Tauri command `run_engine_request_direct(request_json)` 가 in-process `handle()` 호출. JSON-in/JSON-out 단일 dispatch 로 모든 EngineRequest variant 처리. GUI 의 `checkpointList`/`undoCheckpoint`/`backupDbViewerInspect`/`backupGraphSummary`/`backupDbMaintenance`/`backupCleanup` 6개 consumer 가 Python `vib` 서브프로세스 없이 엔진 직접 호출. trivial 명령 wall time ~80ms → <5ms.
- **Rust secret_scan pure-function 이전 (Phase 2)**: `vibelign-core/src/secret_scan.rs::scan_unified_diff()` 가 Python `scan_unified_diff_for_secrets` 와 1:1 parity. 환경변수 `VIBELIGN_SECRET_SCAN_RUST=1` 옵트인 시 사용. 골든 fixture 10개 (HC rule 양성 / placeholder skip / allow-marker / multi-`@@` / removed-line / `\ No newline` / HC-wins-keyword / 한글+이모지) 로 parity 보장.
- **GUI 통합 에러 로그 뷰**: 새 "에러로그" 탭 (`pages/ErrorLogs.tsx`). `.vibelign/logs/{cli,gui}-error-*.jsonl` 통합 표시. 종류 필터 (전체/CLI/GUI), 행 클릭 시 raw JSON 상세 모달, **🐛 GitHub 이슈로 보고** 버튼 (단일/다중 선택 — 한 이슈로 묶기 또는 각각 별도 탭), **🗑 정리** 버튼으로 수정 완료된 에러 즉시 클리어.
- **자동 백업 실패 가시화**: post-commit hook (`internal_post_commit_cmd.py`) 이 더 이상 silent skip 하지 않음. 실패 시 stderr 출력 + 통합 에러 로그 (`record_cli_error`) 기록. 사용자가 `vib history` 가 stale 임을 즉시 인지.

### Changed

- **post-commit hook 마커 v2 → v3**: 쉘 템플릿이 `>/dev/null 2>&1` → `>/dev/null` 로 변경되어 stderr 가 git terminal 에 보임. 기존 v1/v2 설치는 다음 `vib start` 시 자동 v3 으로 갱신.
- **3-writer DB concurrency 입증**: WAL + busy_timeout=5000ms 가 (a) Tauri direct in-process write, (b) Python vib subprocess 1-shot, (c) Rust daemon 동시 접근에서 contention 흡수함을 확인 (500 ops 0 errors).
- **백업 카드 라벨**: `cleanBackupNote` 가 git commit 본문 전체 대신 첫 줄 + 80자로 truncate. RestorePreviewPanel 은 hover tooltip 으로 풀 메시지 보존.
- **plan §3 lever 2 ROI 표 측정 기반 갱신**: scan_cache (json 1ms 로드), watch_state (4ms 로드), anchor_tools (<0.2ms/file), strict_patch (cross-cutting 의존) 모두 실측 결과 incremental Rust 포팅 무가치 확정.

### Fixed

- **`vib memory show` FileNotFoundError**: `save_memory_state` 의 tmp path 가 두 프로세스 동시 호출 시 race 로 사라지는 문제 — pid + uuid 로 unique 화. (이전 에러 로그 누적 10건의 주범).
- **`vib doctor | head` BrokenPipeError**: CLI main 에 `signal.SIGPIPE = SIG_DFL` 등록 (Unix 표준 도구 동작). Windows 는 SIGPIPE 미존재로 no-op.
- **RUST_ENGINE_INTEGRITY_FAILED: integrity manifest missing**: `target/{debug,release}` dev 빌드 경로에서 `.sha256` 매니페스트 누락 시 자동 재생성. Windows NTFS case-preserving 대비 case-insensitive 매칭. 번들/설치본 경로는 기존대로 명시 실패 (빌드/배포 누락 신호 보존).
- **GUI unhandledrejection (`listeners[eventId].handlerId`)**: CodemapCard 의 `listen()` cleanup 패턴이 React StrictMode + Vite HMR 의 double cleanup 시 race — Onboarding.tsx 의 idempotent 패턴 (`let unlisten; ...; unlisten?.()`) 으로 통일.
- **홈 카드 그리드 1fr 1fr 불균형**: SortableCardWrapper 에 `width:100%` + `minWidth:0` 추가. dnd-kit transform + 카드별 다른 콘텐츠 폭이 합쳐지면 좌/우 컬럼이 불균형하게 보이던 회귀 수정.

### Verified

- `cargo test --manifest-path "vibelign-core/Cargo.toml"` → 90 passed (이전 74 대비 +16: secret_scan parity 10 + handler/protocol 2 + module unit 4).
- `pytest` 영향 받는 15 suite → 188 passed, 1 skipped.
- `cargo build --manifest-path "vibelign-gui/src-tauri/Cargo.toml"` → 0 errors.
- `npx tsc --noEmit` (vibelign-gui) → No errors.
- `cargo run --release --example concurrency_smoke` → 500 ops PASS, 0 contention errors.
- 실 엔진 e2e 스모크: 6 GUI consumer 모두 raw response 의 모든 parser 필드 정상 라운드트립. secret_scan ASCII / 한글+이모지 path 양쪽 동일 finding.

### Migration

- 기존 사용자: 자동 적용. post-commit hook 은 `vib start` 또는 hook reinstall 시 v3 으로 자동 갱신됨.
- 옵션 `VIBELIGN_SECRET_SCAN_RUST=1`: 명시 ON 시에만 Rust secret scan. 기본 Python.
- 환경변수 `VIBELIGN_PROJECT_SCAN_RUST=0`: Python/fd fallback 강제. 기본 Rust.

---

## [2.1.11] — 2026-05-08

VibeLign 2.1.11 은 **Rust project_scan 기본 라우팅, GUI Explain 분류 보정, CLI help/manual 정합성 개선**을 포함한 릴리즈입니다.

### Added

- Rust 엔진에 `project_scan` IPC를 추가하고 Python CLI가 기본적으로 Rust scan 결과를 사용하도록 연결했습니다.
- `iter_source_file_records()`를 추가해 Rust scan의 `category/imports` metadata를 `scan_cache`가 재사용할 수 있게 했습니다.
- `vib -h`와 `vib manual`에 최근 추가된 `backup-*`, `show`, `doc-sources`, `docs-enhance`, `bench`, `manual` 안내를 빠짐없이 노출합니다.

### Changed

- `scan_cache.incremental_scan()`이 Rust scan metadata를 우선 사용하되, 실패 시 기존 Python/fd fallback을 유지합니다.
- GUI Tauri command 모듈에 anchor 경계를 추가해 VibeLign Explain/CodeMap에서 backend command 파일을 더 명확하게 식별합니다.

### Fixed

- GUI Explain Report에서 `vibelign-gui/src-tauri/src/commands/*.rs`가 `화면`으로 잘못 표시되던 문제를 `명령/설정`으로 보정했습니다.
- stale `.vibelign/project_map.json`이 명확한 command 경로를 `ui`로 덮어쓰지 못하도록 우선순위를 조정했습니다.
- `.mcp.json`, `pyproject.toml`, `vib.spec`, `/commands/`, `/cli/` 경로가 Explain에서 명령/설정 파일로 분류됩니다.

### Verified

- Rust project_scan consumer/fallback focused tests 통과.
- Explain/GUI contract focused tests 통과.
- CLI help/manual coverage tests 통과.
- `GIT_MASTER=1 git diff --check` 통과.

---

## [2.1.10] — 2026-05-05

VibeLign 2.1.10 은 **Gemini 무료 등급 429 에러 안내 개선** 핫픽스입니다.

### Changed

- `vib docs-enhance` 가 Gemini HTTP 429 (분당 한도 초과) 를 만나면, 이제 무료 등급 한도와 유료 전환 안내, 그리고 자동 재시도를 늘리는 환경변수(`GEMINI_HTTP_MAX_ATTEMPTS`, `GEMINI_HTTP_RETRY_CAP`) 사용법을 함께 보여줍니다.
- 동일 메시지가 GUI 의 AI 요약 버튼 에러 영역에도 그대로 표시되며, Google AI Studio 업그레이드 URL 은 클릭 가능한 버튼으로 자동 변환됩니다 (GUI 측 코드 변경 없음).

### Verified

- `_format_http_error` 합성 429 입력으로 메시지 포맷 검증.
- GUI 의 `whiteSpace: pre-wrap` + URL 링크화 기존 로직이 새 메시지를 그대로 처리.

---

## [2.1.9] — 2026-05-05

VibeLign 2.1.9 는 **BACKUPS 탭 즉시 로딩과 복원 미리보기 시각 개선**을 담은 GUI QoL 릴리즈입니다.

### Changed

- BACKUPS 탭 재방문 시 마지막 로드된 백업 목록을 메모리 캐시로 즉시 렌더하고, 백그라운드에서 새 데이터를 받아 자동 갱신합니다 (stale-while-revalidate).
- 프로젝트를 여는 즉시 백업 목록을 백그라운드 프리페치하여 BACKUPS 첫 클릭에서도 서브프로세스 콜드 스타트 지연이 보이지 않습니다.
- 복원 미리보기 카드의 텍스트 한 줄을 칩 3개(상대시간 / 파일 수 / 안전 상태)로 시각화했습니다.
- `formatRelativeTime` 헬퍼 추가 (방금 / N분 전 / N시간 전 / N일 전, 7일 이후 절대시간 fallback).

### Verified

- TypeScript 타입 체크 통과.
- BACKUPS 탭 즉시 렌더 / 저장·복원 후 목록 갱신 수동 검증.

---

## [2.1.8] — 2026-05-05

VibeLign 2.1.8 은 **GUI/CLI API 키 동기화와 복구 후보 AI 추천 안정성**을 보강한 핫픽스입니다.

### Fixed

- GUI와 CLI가 같은 `api_keys.json` 저장소를 기준으로 API 키 저장/삭제 상태를 일관되게 반영합니다.
- 삭제한 키는 VibeLign 삭제 override로 기록되어 외부 환경 변수에 남아 있어도 GUI/CLI에서 삭제된 상태로 취급됩니다.
- 새로 저장한 Gemini 키가 오래된 `GEMINI_API_KEY` 환경 변수보다 우선되도록 key precedence를 조정했습니다.
- GUI `복구 후보 추천 보기`가 Settings에 저장된 AI 키를 `vib recover --recommend`에 전달해 Gemini 추천이 즉시 붙도록 했습니다.
- Windows에서 `%APPDATA%`가 없는 실행 환경에서도 GUI가 CLI와 동일하게 `%USERPROFILE%\AppData\Roaming\vibelign\api_keys.json` fallback을 사용합니다.

### Security

- `vib config` 임시 저장 모드가 실제 API 키를 터미널에 출력하지 않도록 막았습니다.
- GUI 마이그레이션 후 레거시 `gui_config.json`에 남은 API 키 복사본을 제거합니다.
- Settings 화면에서 저장된 키 앞부분도 노출하지 않고 `값 숨김`으로만 표시합니다.

### Verification

- Focused key/recovery tests passed locally.
- GUI production build passed locally.
- Tauri key-command compile check passed locally.
- Diff/working-tree secret pattern scans found no real API keys.

---

## [2.1.7] — 2026-05-05

VibeLign 2.1.7 은 **패키징된 GUI의 초기 저장이 Rust/SQLite 엔진을 확실히 사용하도록 고친 핫픽스**입니다.

### Fixed

- Windows GUI에서 “초기 프로젝트 시작하기”를 눌렀을 때 번들된 `vibelign-engine.exe`를 찾지 못해 Python legacy 백업으로 fallback될 수 있던 경로를 수정했습니다.
- PyInstaller onedir 구조의 `_internal/vibelign/_bundled/vibelign-engine(.exe)`를 Tauri GUI와 Python CLI 양쪽에서 Rust engine 후보로 인식합니다.

### Verification

- CLI `vib start` smoke에서 `.vibelign/vibelign.db`와 `.vibelign/rust_objects/` 생성 확인.
- CLI `vib checkpoint --json` smoke에서 legacy checkpoint 파일 생성 없이 Rust object 저장 확인.
- Focused Python checkpoint/start tests and Tauri `vib_path` tests passed locally.

---

## [2.1.6] — 2026-05-05

VibeLign 2.1.6 은 **Session Memory / Recovery 안내 노출 정리**와 **Windows handoff 안정화**를 담은 릴리즈입니다.

### Added

- GUI Manual 탭에 `세션 메모리`와 `복구 옵션` 항목 카드를 추가했습니다.
- `vib -h`, `vib memory -h`, `vib manual memory`, `vib manual recover`에서 초보자도 이해하기 쉬운 설명을 표시합니다.
- `vib memory <TAB>`에서 `show`, `next`, `proposal-create`, `proposal-accept` 같은 하위 명령과 자주 쓰는 옵션이 자동완성됩니다.
- 자동 추정 handoff 일 때 `PROJECT_CONTEXT.md` 상단에 `work_memory.json` 확인 경고를 표시합니다.

### Changed

- GUI의 AI 이동 카드에서 `--compact`와 `--handoff` 토글을 제거하고, `TRANSFER` 버튼이 항상 handoff 흐름으로 실행되게 했습니다.
- GUI Manual 상세 화면이 실제 CLI 사용법과 서브명령/옵션을 그대로 보여주도록 개선했습니다.

### Fixed

- Windows에서 `vib transfer --handoff` 실행 시 CP949 디코딩과 `stdout=None` 때문에 실패하던 경로를 안정화했습니다.
- `vib manual memory`가 `'memory' 커맨드를 찾을 수 없어요.`로 실패하던 manual registry 누락을 수정했습니다.
- GUI transfer 실패 시 실제 CLI stdout/stderr가 보이도록 해 Windows 디버깅 가능성을 높였습니다.

### Verification

- `86 passed` focused Python regression suite, including Windows-sensitive transfer/handoff tests.
- GUI production build passed with `rtk npm run build`.

### Changed

- **Checkpoint engine cutover**: `vib checkpoint`, `vib history`, and `vib undo` now use the Rust/SQLite checkpoint engine by default, with visible Python fallback for environment failures.
- Legacy JSON checkpoints under `.vibelign/checkpoints/` are preserved on disk, but they are **not automatically imported or merged** into the new SQLite-backed default history/list/restore path. Back up `.vibelign/checkpoints/` before upgrading if you need old checkpoint snapshots.

---

## [2.0.1] — 2026-04-18

PyPI 렌더링 한정 문서 패치.

### Fixed

- README 의 `README.ko.md`, `CHANGELOG.md`, `MIGRATION_v1_to_v2.md` 상대 링크를 PyPI 페이지에서 404 나지 않도록 **절대 GitHub 링크** 로 변경. GitHub 에서는 기존과 동일하게 동작.

### Notes

- 코드 변경 없음. CLI / GUI 동작 동일.
- v2.0.0 의 GUI 바이너리 (`.dmg` / `.exe` / `.msi`) 는 그대로 사용 가능. v2.0.1 은 PyPI 업로드만 의미를 가집니다.

---

## [2.0.0] — 2026-04-18

VibeLign 2.0 은 **데스크톱 GUI 런칭** + **MCP/Patch 모듈화** + **AI 옵트인 체계** 를 담은 메이저 릴리즈입니다.
1.x 사용자는 [MIGRATION_v1_to_v2.md](./MIGRATION_v1_to_v2.md) 를 먼저 확인해주세요.

### Added

- **VibeLign GUI (macOS / Windows)** — Tauri 기반 데스크톱 앱
  - Doctor 페이지: 원클릭 진단·자동 적용 (`vib doctor --apply` 번들)
  - 앵커카드: 앵커 삽입 + intent/aliases 재생성 (코드 기반 / AI 기반, `--force` 로 기존 AI 결과 덮어쓰기)
  - DocsViewer: 프로젝트 문서 AI 보강, 개별 문서별 요약
  - Settings: API 키 관리, AI 옵트인 전역 토글
- **MCP 서버 모듈 재구성** — `vibelign/mcp/` 아래 dispatch/handlers/tool_specs 분리
- **Patch 모듈 분리** — `vibelign/patch/` (builder / handoff / preview / targeting / steps / output / render …)
- **AI 보강 옵트인 체계** — consent UI 제거 → 설정 토글로 일원화
  - 해시 캐시 + 프로그레스바로 진행 상황 가시화
  - Anthropic / OpenAI / Gemini 자동 선택
- **Docs AI enhance 커맨드** — `vib docs-enhance` (문서 요약 래퍼)
- **onedir 런타임 번들링** — PyInstaller `onefile → onedir` 전환으로 GUI 콜드스타트 제거
- **앵커 `_source` 필드** — `anchor_meta.json` 에 `code / ai / manual / ai_failed` 구분 도입, AI/수동 결과를 코드 기반 재생성으로부터 보호

### Changed

- **BREAKING**: `vibelign.vib_cli` → `vibelign.cli.vib_cli` (모듈 경로 이동)
- **BREAKING**: `vibelign.mcp_server` → `vibelign.mcp.mcp_server`
- Doctor 출력 포맷 개선 (score / status / issue 구조 일원화)
- 패치 스위트가 `target_anchor` 기반 소형 패치 우선 — 거대 파일 전면 재작성 방지

### Fixed

- Windows `git` exit 129 회피
- GUI IPC env allowlist + api_keys 파일 권한 강화
- 앱 이동 시 CLI 래퍼 타겟 경로 자동 재검증
- AI 요약 Gemini 기본 모델 503 회피 (`2.0-flash` 로 다운)
- 패치 서제스터 AI 선택 게이트 강화 + 음수 후보 필터

### Performance

- Doctor / DocsViewer 콜드스타트 제거 (PyInstaller onedir)
- `vib` 프리워밍 + `ai-enhance status` 메모리 캐시
- docs visual contract 메모리 캐시 (클릭당 `vib` subprocess 스폰 제거)

### Security

- GUI IPC env allowlist 적용
- `~/.vibelign/api_keys` 파일 권한 제한
- CLI 설치 게이트 추가

---

## [1.7.2] — 2026-03-22

v1.x 의 마지막 CLI-only 릴리즈. 상세 변경사항은 `git log v1.7.2-final` 참고.
