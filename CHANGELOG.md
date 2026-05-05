# Changelog

본 파일은 VibeLign 의 주요 변경사항을 기록합니다.
포맷은 [Keep a Changelog](https://keepachangelog.com/) 를 따르며,
버전 체계는 [Semantic Versioning](https://semver.org/) 을 준수합니다.

---

## [Unreleased]

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
