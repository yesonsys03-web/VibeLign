<p align="center">
  <img src="https://raw.githubusercontent.com/yesonsys03-web/VibeLign/main/assets/banner.svg" alt="VibeLign Banner" width="100%"/>
</p>

<p align="center">
  <b>🇰🇷 한국어</b> &nbsp;|&nbsp; <a href="https://github.com/yesonsys03-web/VibeLign/blob/main/README.md">🇺🇸 English</a>
</p>

<p align="center">
  <video src="https://github.com/user-attachments/assets/1bbcb1da-3c61-48e3-abd4-94ec9d66ecb7"
         autoplay loop muted playsinline width="100%">
  </video>
</p>

<p align="center">
  <a href="https://pypi.org/project/vibelign/"><img src="https://img.shields.io/pypi/v/vibelign?color=7c3aed&label=vibelign" alt="PyPI"/></a>
  <a href="https://github.com/yesonsys03-web/VibeLign/releases/latest"><img src="https://img.shields.io/github/v/release/yesonsys03-web/VibeLign?color=22c55e&label=%EB%8D%B0%EC%8A%A4%ED%81%AC%ED%86%B1%20%EC%95%B1" alt="GitHub Release"/></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/지원-Claude%20Code%20%7C%20Cursor%20%7C%20Codex-orange" alt="AI Tools"/>
</p>

---

# 🎮 VibeLign — AI 코딩의 안전장치

VibeLign(`vibelign`)은 바이브 코딩 작업을 더 안전하게 해주는 AI 코딩 안전 **CLI + 데스크톱 GUI** 예요.
프로젝트 구조 보호, 체크포인트 저장, 되돌리기, 앵커 관리, 커밋 전 비밀정보 차단을 도와줘요.

> **🆕 v2.0**: macOS / Windows 데스크톱 앱, 문서별 AI 요약, 앵커 intent 재생성. [CHANGELOG](https://github.com/yesonsys03-web/VibeLign/blob/main/CHANGELOG.md) · [마이그레이션 가이드](https://github.com/yesonsys03-web/VibeLign/blob/main/MIGRATION_v1_to_v2.md) 참고.

문서: `https://yesonsys03-web.github.io/VibeLign/`  
저장소: `https://github.com/yesonsys03-web/VibeLign`  
이슈: `https://github.com/yesonsys03-web/VibeLign/issues`  
릴리즈: `https://github.com/yesonsys03-web/VibeLign/releases`

> ### 이런 적 있나요?
>
> - AI한테 간단한 기능을 추가해달라고 했더니 **파일 전체를 다시 썼어요**
> - 모든 코드가 `main.py` 한 파일에 들어있어요 — **1000줄 넘음, 관리 불가능**
> - AI가 다른 파일을 건드려서 이제 아무것도 안 돼요
> - 되돌리려고 하는데 방법을 몰라요
>
> **이거를 위해 만들었어요!**

**데스크톱 앱 (macOS / Windows)** — [📥 최신 릴리즈 다운로드](https://github.com/yesonsys03-web/VibeLign/releases/latest)

**Mac / Linux (CLI)**
```bash
pip install vibelign
vib start
```

**Windows** (PowerShell, CLI)
```powershell
# 1단계: uv 설치 — 최초 1회, PATH 자동 설정, 경고 없음
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# PowerShell 껐다 켜고:
uv tool install vibelign
vib start
```

![퀵 스타트](https://raw.githubusercontent.com/yesonsys03-web/VibeLign/main/assets/quickstart_kr.jpeg)

---

## 🤔 VibeLign이 뭔가요?

AI 코딩 도구(Claude Code, Cursor 등)는 코드를 빨리 작성해요. 하지만 **문제**가 있어요:

| 문제 | VibeLign이 해결해줌 |
|------|---------------------|
| 모든 코드가 `main.py`에 들어감 | AI가 **알아서 정리**하게 함 |
| AI가 요청한 것과 다른 걸 함 | **정확한 수정 요청**을 만들어줌 |
| 코드가 망가졌는데 되돌릴 수 없음 | **세이브 & 되돌리기** 기능 제공 |

**어떤 AI 도구와도 함께 쓸 수 있어요**: Claude Code · Cursor · Codex · OpenCode

---

## 📝 딱 3가지만 기억하세요

```
AI가 코딩하기 전  →  vib checkpoint "작업 전"     # 세이브
AI가 망쳤어       →  vib undo                      # 되돌리기
괜찮아졌어        →  vib checkpoint "완료"          # 다시 세이브
```

> Git 몰라도 돼요. 그냥 `vib`만 치면 돼요.

---

## 🚀 3단계로 시작하기

**Mac / Linux**
```bash
# 1. 설치
pip install vibelign

# 2. 프로젝트 폴더로 이동
cd my-project

# 3. 시작!
vib start
```

**Windows** (PowerShell)
```powershell
# 1. uv 설치 — 최초 1회 (PATH 자동 설정, 경고 없음)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# PowerShell 껐다 다시 켜고:

# 2. vibelign 설치
uv tool install vibelign

# 3. 프로젝트 폴더로 이동 후 시작!
cd my-project
vib start
```

---

## 📚 모든 명령어

### 기본 (꼭 알아두기)

| 명령어 | 하는 일 |
|--------|---------|
| `vib start` | 처음 한 번만! 프로젝트 세팅 |
| `vib checkpoint "메시지"` | 지금 상태 저장 (게임 세이브처럼) |
| `vib checkpoint` | 저장할 때 메시지 입력하라고 뜸 |
| `vib undo` | 마지막 세이브 지점으로 돌아감 |
| `vib history` | 세이브 목록 보기 |

### AI한테 코딩 요청할 때

| 명령어 | 하는 일 |
|--------|---------|
| `vib patch "버튼 추가해줘"` | AI에게 어떻게 수정할지 알려줌 (한국어 OK!) |
| `vib anchor` | AI가 수정해도 되는 곳을 표시해줌 |
| `vib scan` | 파일 정리 + 최신 상태 확인 |

### VibeLign patch 규칙

- 복합 요청은 `intent / source / destination / behavior_constraint`로 먼저 분해한다.
- `삭제`와 `이동`이 같이 나오면, 사용자가 분명히 삭제를 원하지 않는 한 이동 + 보존으로 본다.
- `source`와 `destination`은 같은 규칙으로 처리하지 말고 역할별로 따로 해석한다.
- patch contract나 codespeak 구조가 바뀌면 테스트와 문서도 같이 갱신한다.
- 용어는 공통 문서와 glossary 기준으로 맞춘다.

### 확인하고 검증할 때

| 명령어 | 하는 일 |
|--------|---------|
| `vib doctor` | 프로젝트 건강 상태 확인 |
| `vib explain` | 뭐가 바뀌었는지 쉬운 말로 설명 |
| `vib guard` | 코드가 망가지지 않았는지 확인 |
| `vib ask 파일명.py` | 파일이 뭘 하는지 설명해달라고 함 |

### 파일 보호

| 명령어 | 하는 일 |
|--------|---------|
| `vib protect 파일명.py` | 중요한 파일 잠금 (AI가 못 건드림) |
| `vib protect --list` | 잠근 파일 목록 보기 |
| `vib protect --remove 파일명.py` | 잠금 해제 |
| `vib secrets --staged` | 지금 커밋할 내용에서 API 키, 토큰, `.env` 파일 차단 |

### 설정 & 내보내기

| 명령어 | 하는 일 |
|--------|---------|
| `vib config` | API 키 설정 |
| `vib export claude` | Claude Code용 설정 파일 만들기 |
| `vib export cursor` | Cursor용 설정 파일 만들기 |
| `vib export opencode` | OpenCode용 설정 파일 만들기 |

### 기타 유용한 것들

| 명령어 | 하는 일 |
|--------|---------|
| `vib watch` | 파일 변경 실시간 감시 |
| `vib bench` | 앵커가 얼마나 효과적인지 테스트 |
| `vib manual` | 상세 사용 설명서 보기 |
| `vib rules` | AI 개발 규칙 전체 보기 |
| `vib transfer` | AI 도구 전환용 `PROJECT_CONTEXT.md` 생성 |
| `vib transfer --handoff` | Session Handoff 블록 추가 — 새 AI가 바로 이어서 작업 가능 |
| `vib transfer --handoff --session-summary "작업 요약" --first-next-action "다음 할 일"` | handoff 요약과 다음 작업을 직접 지정 |
| `vib transfer --handoff --dry-run` | 파일 저장 없이 handoff 내용 미리 보기 |
| `vib completion` | 탭 누르면 자동완성되게 설정 |
| `vib install` | 설치 방법을 단계별로 알려줌 |

---

## 💡 추천하는 흐름

```bash
# 처음 시작할 때
vib start

# AI가 코딩하기 전
vib checkpoint "로그인 기능 추가 전"
vib doctor --strict
vib patch "로그인 버튼 만들어줘"

# AI가 코딩한 후
vib explain --write-report
vib guard --strict --write-report

# 다 됐으면
vib checkpoint "로그인 기능 완성!"

# 실수했으면
vib undo

# 토큰 한도 도달 또는 AI 툴 전환 전에
vib transfer --handoff    # Session Handoff 블록 생성
vib transfer --handoff --no-prompt --print  # 자동 생성 + 콘솔 출력
vib transfer --handoff --session-summary "현재 세션 작업" --first-next-action "테스트 재실행"
vib transfer --handoff --dry-run  # 저장 전 미리 보기
# 새 AI에게: "PROJECT_CONTEXT.md 상단의 Session Handoff 블록 먼저 읽어줘"
```

`transfer` 호환성: `--handoff`는 `--compact` 또는 `--full`과 함께 쓸 수 없습니다.

이제 `vib start`를 실행하면 Git 저장소에서는 비밀정보 커밋 보호도 자동으로 켜져요.
커밋 전에 지금 올리려는 내용에서 API 키, 토큰, 개인키, `.env` 같은 비밀정보 파일을 검사해서 실수 업로드를 막아줘요.

```bash
# 필요하면 수동 검사도 가능
vib secrets --staged
```

---

## 🔧 설치 방법

### 방법 1: uv (추천, 빠름)
```bash
uv tool install vibelign
```

> **설치 후 "is not on your PATH" 경고가 뜨면:**
> ```bash
> uv tool update-shell
> ```
> 그 다음 터미널 껐다 다시 켜면 `vib` 바로 사용 가능해요.
> **bash 쉘**을 쓴다면 bash 안에서 `uv tool update-shell`을 실행하거나:
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
> ```

### 방법 2: pip
```bash
pip install vibelign
```

설치하면 `vib`랑 `vibelign` 둘 다 쓸 수 있어요.

### 방법 3: 데스크톱 앱 (GUI)

최신 `.dmg` (macOS, Apple Silicon) 또는 `.exe` / `.msi` (Windows) 를
[Releases 페이지](https://github.com/yesonsys03-web/VibeLign/releases/latest) 에서 받으세요.
GUI 에는 `vib` 런타임이 함께 번들링 되어 있어서 별도의 CLI 설치가 필요 없어요.

> macOS 첫 실행 시 "앱이 손상되었습니다" 오류가 뜨면 터미널에서 `xattr -rc vibelign-gui.app` 실행
> (Apple 공증(notarization) 없이 배포된 ad-hoc 서명이라 정상적인 Gatekeeper 경고예요).

### Windows — pip으로 설치 후 `vib`가 안 될 때

pip으로 설치하면 `vib.exe`가 Python `Scripts` 폴더에 들어가는데, 이 폴더가 PATH에 없으면 `vib` 명령어를 인식 못해요.
설치할 때 뜨는 경고 메시지에 추가해야 할 경로가 정확히 나와 있어요:

```
WARNING: The scripts vib.exe ... are installed in 'C:\Users\...\Scripts' which is not on PATH.
```

**수동으로 PATH 설정하는 방법:**
1. `Win + R` → `sysdm.cpl` 입력 → 엔터
2. **고급** 탭 → **환경 변수**
3. **시스템 변수**의 `Path` → **편집**
4. **새로 만들기** 클릭 후 경고 메시지에 나온 `Scripts` 경로 붙여넣기
   - 예: `C:\Users\사용자이름\AppData\Local\Programs\Python\Python312\Scripts\`
5. 확인 → PowerShell 완전히 껐다 다시 켜기

> **팁:** `uv tool install vibelign`을 쓰면 이 과정이 필요 없어요 — PATH 자동 설정.

---

## 📖 더 자세히 알고 싶으면

```bash
vib manual          # 상세 사용 설명서
vib manual rules    # AI 개발 규칙만 보기
vib rules           # rules랑 같음
```

---

## 🎯 우리 약속

> *"AI 코딩은 빠르다. 하지만 안전장치 없으면 만든 걸 다 날릴 수 있다."*

VibeLign이 보장하는 것:
- ✅ 1초 만에 세이브 (`vib checkpoint "설명"`)
- ✅ 1초 만에 되돌리기 (`vib undo`)
- ✅ Git 몰라도 됨
- ✅ 초보자도 쉽게 쓸 수 있음

---

⭐ **VibeLign이 코드 저장해줬으면 Star 하나 부탁해요 — 감사합니다!**

---

## 📋 업데이트 내역 (Release Notes)

**다음 버전** — Rust/SQLite 체크포인트 엔진:

- `vib checkpoint`, `vib history`, `vib undo`가 Rust/SQLite 체크포인트 엔진을 기본으로 사용합니다. 번들 엔진을 실행할 수 없으면 Python fallback이 사용자에게 표시됩니다.
- 기존 JSON 체크포인트(`.vibelign/checkpoints/`)는 디스크에 보존하지만 새 SQLite 기반 이력에 자동 import/병합하지 않습니다. 오래된 스냅샷이 필요하면 업그레이드 전에 `.vibelign/checkpoints/`를 백업해두세요.

**v2.0.0** — 데스크톱 GUI + MCP/Patch 모듈화 + AI 옵트인:

- 🖥️ **VibeLign GUI (macOS / Windows)** — Tauri 기반 데스크톱 앱
  - Doctor 페이지: 원클릭 진단 + 자동 적용
  - 앵커카드: 앵커 삽입 + intent/aliases 재생성 (코드 기반 / AI 기반, `--force` 로 기존 AI 결과 덮어쓰기)
  - DocsViewer: 문서별 AI 요약
  - Settings: API 키 관리, AI 옵트인 전역 토글
- 🔌 **MCP 서버 재구성** — `vibelign/mcp/` 아래 dispatch/handlers/tool_specs 분리
- 🧩 **Patch 모듈 분리** — `vibelign/patch/` (builder · handoff · preview · targeting · …)
- 🤖 **AI 옵트인** — consent UI 제거, Settings 전역 토글 하나로 통합. Anthropic / OpenAI / Gemini 자동 선택
- ⚡ **onedir 런타임** — PyInstaller `onefile → onedir` 전환으로 GUI 콜드스타트(1~3초) 제거
- 🏷️ **앵커 `_source` 필드** — `anchor_meta.json` 에 `code / ai / manual / ai_failed` 구분 도입해 AI/수동 결과를 코드 기반 재생성으로부터 보호 (`--force` 로 덮어쓰기 가능)
- ⚠️ **Breaking**: `vibelign.vib_cli` → `vibelign.cli.vib_cli`; `vibelign.mcp_server` → `vibelign.mcp.mcp_server`
- 자세한 내용은 [CHANGELOG.md](https://github.com/yesonsys03-web/VibeLign/blob/main/CHANGELOG.md) · [MIGRATION_v1_to_v2.md](https://github.com/yesonsys03-web/VibeLign/blob/main/MIGRATION_v1_to_v2.md)

**v1.6.0** — MCP 서버 + AI 개발 규칙 시스템:

- `vib mcp` — MCP(Model Context Protocol) 서버 실행 (Claude Desktop 연동)
- `vib start` — Claude Code와 Cursor에 VibeLign MCP 자동 등록 (기존 Cursor MCP 서버는 유지)
- `vib rules` — AI 개발 규칙 전체를 CLI에서 바로 확인
- `vib manual rules` — 개발 규칙 상세 매뉴얼
- Anchor intent system — 앵커에 의도(intent) 정보 저장
- 한국어 토크나이저 — patch 요청을 한국어로도 정확하게 해석
- AI_DEV_SYSTEM — 유지보수성/함수 디자인 규칙 추가 (Section 6-1, 14)
- `vib scan` 버그 수정 — set_intent 속성 누락 해결

**v1.5.32** — 체크포인트/되돌리기 UX 개편 + AI 설정 파일 보호:

- `vib checkpoint` — 메시지 입력 프롬프트 지원
- `vib undo` — 번호 선택 + 취소 옵션 `[0]`
- `vib history` — 초 단위 타임스탬프 표시
- `vib start` — 초보자 온보딩 + 첫 체크포인트 자동 저장
- `vib export` — AGENTS.md, CLAUDE.md, OPENCODE.md, .cursorrules 보호

**v1.5.0** — 멀티 AI 툴 설정 내보내기:

- `vib export claude` — Claude Code용 CLAUDE.md 생성
- `vib export cursor` — Cursor용 .cursorrules 생성
- `vib export opencode` — OpenCode용 OPENCODE.md 생성
- `vib export antigravity` — Codex/에이전트용 AGENTS.md 생성
- 내보낸 파일에 VibeLign 마커 추가 (덮어쓰기 방지)

**v1.1.0** — 코알못을 위한 핵심 기능 추가:

- `vib init` — VibeLign 초기화/리셋
- `vib start` — 처음 사용자 가이드
- `vib checkpoint` / `vib undo` — Git 없이 세이브 & 되돌리기
- `vib protect` — 중요 파일 잠금
- `vib ask` — 파일 설명 AI 프롬프트 생성
- `vib history` — 체크포인트 이력 보기

---

# 라이선스

MIT
