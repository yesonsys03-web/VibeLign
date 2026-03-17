<p align="center">
  <img src="assets/banner.svg" alt="VibeLign Banner" width="100%"/>
</p>

---

# VibeLign

**AI coding safety system for vibecoders.**

AI writes code fast.
VibeLign keeps your project safe.

---

# Quick Start

<p align="center">
  <img src="assets/banner.svg" alt="VibeLign Quick Start" width="100%"/>
</p>

---

# Why VibeLign?

AI coding is powerful, but it often creates structural problems:

- giant `main.py`
- random `utils.py` catch-all files
- whole-file rewrites
- mixed UI + business logic
- uncontrolled wide patches
- no way to undo AI changes

These problems are common when using:

- Claude Code
- Cursor
- OpenCode
- GPT coding workflows
- AI coding agents

VibeLign adds **guardrails** so AI edits remain safe — and gives you a simple save/restore system so you can always go back.

---



# Architecture & Design Documents

The full design documents for VibeLign are located in:

Recommended reading order:

1. VibeLign_Ultimate_Vision.md
2. VibeLign_System_Architecture.md
3. VibeLign_CLI_Strategy.md
4. VibeLign_vib_doctor_Final_Design_Spec.md

These documents describe the internal architecture and future roadmap of the project.

---

# CLI Name

The primary CLI command is **`vib`**.

```bash
vib doctor
vib anchor
vib patch "add progress bar"
```

The legacy `vibelign` command is also supported as a backward-compatible wrapper that delegates to `vib`.

---

# AI Coding Workflow

Recommended loop:

```
vib init → checkpoint → patch → AI edit → explain → guard → checkpoint (or undo)
```

| Command | Purpose |
|---------|---------|
| `vib init` | initialize/reset VibeLign metadata |
| `vib start` | guided onboarding — shows 3 rules + saves first checkpoint |
| `vib checkpoint` | save current state; prompts for message if omitted |
| `vib undo` | interactive rollback — pick from numbered list, `[0]` to cancel |
| `vib history` | view all checkpoints with friendly timestamps (seconds precision) |
| `vib protect` | lock important files from AI edits |
| `vib ask` | generate a plain-language explanation prompt |
| `vib doctor` | analyze project structure |
| `vib anchor` | insert safe edit anchors |
| `vib scan` | anchor scan + project map refresh in one command |
| `vib patch` | generate safe AI patch request (Korean supported) |
| `vib explain` | explain recent changes |
| `vib guard` | verify project safety |
| `vib export` | export AI config files (claude / cursor / opencode / antigravity) |
| `vib watch` | real-time monitoring + auto project map refresh |

---

# Core Commands

```bash
# --- Project setup ---
vib init
vib init --tool claude
vib start          # beginner-friendly guided onboarding

# --- Save & restore ---
vib checkpoint "before login feature"
vib undo
vib history

# --- File protection ---
vib protect main.py
vib protect --list
vib protect --remove main.py

# --- Ask AI to explain a file ---
vib ask login.py
vib ask login.py --write
GEMINI_MODEL=gemini-2.5-flash-lite vib ask login.py

# --- API config ---
vib config

# --- AI coding workflow ---
vib doctor
vib anchor
vib scan                            # anchor + project map refresh at once
vib patch "add progress bar"
vib patch "로그인 버튼 추가해줘"    # Korean supported
vib explain
vib guard

# --- Export & monitor ---
vib export claude
vib export opencode
vib export cursor
vib export antigravity
vib watch
```

---

# Install

## Recommended (uv)

```
uv tool install .
```

## Alternative (pip)

```
pip install -e .
```

After installation both `vib` and `vibelign` commands are available.

---

# First Test

Run these commands:

```bash
vib init
vib checkpoint "first save"
vib doctor
vib anchor --dry-run
vib patch "add progress bar" --json
vib explain --json
vib guard --json
```

If these commands work, VibeLign is installed correctly.

---

# Visual Guide (Korean)

<p align="center">
  <img src="assets/banner.svg" alt="VibeLign Visual Guide" width="100%"/>
</p>

---

# Watch Mode (Optional)

Real-time project monitoring.

Install dependency:

```
uv add watchdog
```

or

```
pip install watchdog
```

Run:

```
vib watch
```

---

# Recommended Workflow

```bash
vib init
vib checkpoint "project start"

# --- before AI edit ---
vib doctor --strict
vib anchor
vib patch "your request here"

# --- after AI edit ---
vib explain --write-report
vib guard --strict --write-report

# --- if OK ---
vib checkpoint "done: your task"

# --- if NOT OK ---
vib undo
```

---

# Documentation

Beginner guide:

```
VibeLign_QUICKSTART.md
```

Full documentation:

```
docs/MANUAL.md
```

---

# Release Status

**v1.5.32** — Checkpoint & Undo UX overhaul + AI config file protection:

- `vib checkpoint` — now prompts for a message when none is given (like `git commit`)
- `vib undo` — fully interactive: numbered list with friendly timestamps, cancel option `[0]`
- `vib history` — timestamps show seconds (`오늘 14:30:02`) to distinguish same-minute saves
- `vib start` — new user onboarding now shows "딱 3가지만 기억하세요" and offers first checkpoint
- `vib export` — `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, `.cursorrules` protected by markers; no overwrite if user has customized
- GitHub banner added to README

**v1.5.0** — Multi-tool AI config export:

- `vib export claude` — generates `CLAUDE.md` with safety rules for Claude Code
- `vib export cursor` — generates `.cursorrules` for Cursor
- `vib export opencode` — generates `OPENCODE.md` for OpenCode
- `vib export antigravity` — generates `AGENTS.md` for Codex / any agent
- All exported files protected with VibeLign markers (no accidental overwrite)

**v1.1.0** — Beginner-friendly commands added:

- `init` — initialize/reset VibeLign metadata
- `start` — guided onboarding for first-time users
- `checkpoint` / `undo` — save and restore without Git knowledge
- `protect` — lock files from AI edits
- `ask` — generate plain-language explanation prompts
- `history` — view all checkpoints

---

# Philosophy

AI coding is fast.

But without guardrails, it can break project structure.

VibeLign adds **structure-aware safety** to AI-driven development — and makes save/restore simple enough for anyone.

---

# License

MIT

---

# VibeLign (한글 번역)

<p align="center">
  <img src="assets/banner.svg" alt="VibeLign Banner" width="100%"/>
</p>

**AI 코딩 안전 시스템: 바이브코더를 위한 보호막**

AI는 코드를 정말 빨리 작성하지만, 가끔 프로젝트를 엉망으로 만들기도 합니다.
VibeLign은 여러분의 소중한 프로젝트를 안전하게 지켜줍니다.

---

## CLI 이름

기본 CLI 명령어는 **`vib`** 입니다.

```bash
vib doctor
vib anchor
vib patch "진행 표시바 추가해줘"
```

기존 `vibelign` 명령어도 하위 호환 래퍼로 계속 지원됩니다 (`vibelign` → `vib` 위임).

---

## 퀵 스타트 (빨리 시작하기)

<p align="center">
  <img src="assets/banner.svg" alt="VibeLign 퀵스타트" width="100%"/>
</p>

---

## 왜 VibeLign이 필요한가요?

AI로 코딩을 하면 힘은 세지지만, 가끔 규칙 없는 코드가 생겨서 문제가 됩니다:

- `main.py` 파일 하나에 모든 코드가 다 들어가서 너무 커질 때
- 아무 코드나 다 모아둔 정체불명의 `utils.py` 파일이 생길 때
- AI가 마음대로 파일 전체를 싹 다 새로 써버릴 때
- 화면 디자인(UI)과 실제 기능(로직)이 마구 뒤섞일 때
- AI가 바꾼 코드를 되돌릴 방법이 없을 때

Claude Code, Cursor, OpenCode 같은 AI 도구를 쓸 때 이런 일이 자주 생깁니다. VibeLign은 AI가 안전하게 코드를 고칠 수 있도록 **가이드라인(안전 난간)**을 쳐주고, 언제든 이전 상태로 되돌아갈 수 있는 **세이브 포인트** 기능을 제공합니다.

---

## AI 코딩 작업 순서

VibeLign이 추천하는 안전한 개발 순서:

```
vib init → checkpoint → patch → AI 수정 → explain → guard → checkpoint (또는 undo)
```

| 명령어 | 하는 일 |
|--------|---------|
| `vib init` | VibeLign 메타데이터를 초기화/재설치해요 |
| `vib start` | 신규 사용자 온보딩 — "딱 3가지 규칙" 안내 + 첫 체크포인트 저장 |
| `vib checkpoint` | 현재 상태를 세이브 포인트로 저장 — 메시지 없으면 자동으로 입력 안내 |
| `vib undo` | 인터랙티브 되돌리기 — 번호 목록에서 선택, `[0]`으로 취소 가능 |
| `vib history` | 초 단위 시간으로 저장된 체크포인트 목록 확인 (`오늘 14:30:02`) |
| `vib protect` | 중요한 파일을 AI가 못 건드리게 잠가요 |
| `vib ask` | 파일을 쉬운 말로 설명해 달라는 프롬프트를 만들어요 |
| `vib doctor` | 프로젝트 구조가 괜찮은지 분석해요 |
| `vib anchor` | 안전하게 고칠 수 있는 구역(앵커)을 정해요 |
| `vib patch` | AI에게 보낼 안전한 수정 요청서를 만들어요 |
| `vib explain` | 최근에 바뀐 내용을 알기 쉽게 설명해줘요 |
| `vib guard` | 프로젝트가 여전히 안전한지 검사해요 |
| `vib export` | AI 도구별 설정 파일 생성 (claude / cursor / opencode / antigravity) |
| `vib watch` | 실시간으로 파일 변화를 감시해요 |

---

## 핵심 명령어

```bash
# --- 프로젝트 세팅 ---
vib init
vib init --tool claude
vib start          # 처음 쓰는 사람용 가이드 온보딩

# --- 저장 & 되돌리기 ---
vib checkpoint "로그인 기능 추가 전"
vib undo
vib history

# --- 파일 보호 ---
vib protect main.py
vib protect --list
vib protect --remove main.py

# --- 파일 설명 요청 ---
vib ask login.py
vib ask login.py --write

# --- AI 코딩 작업 ---
vib doctor
vib anchor
vib patch "진행 표시바 추가해줘"
vib explain
vib guard

# --- 내보내기 & 감시 ---
vib export claude
vib export opencode
vib export cursor
vib export antigravity
vib watch
```

---

## 설치 방법

### 추천 방법 (uv 사용)
```bash
uv tool install .
```

### 다른 방법 (pip 사용)
```bash
pip install -e .
```

설치 후 `vib` 과 `vibelign` 두 명령어 모두 사용 가능합니다.

---

## 첫 번째 테스트

제대로 설치됐는지 터미널에 입력해 보세요:

```bash
vib init
vib checkpoint "첫 번째 저장"
vib doctor
vib anchor --dry-run
vib patch "진행 표시바 추가" --json
vib explain --json
vib guard --json
```

이 명령어들이 잘 작동한다면 준비 끝!

---

## 시각 가이드

<p align="center">
  <img src="assets/banner.svg" alt="VibeLign 시각 가이드" width="100%"/>
</p>

---

## 실시간 감시 모드 (선택 사항)

파일이 바뀔 때마다 실시간으로 지켜보게 할 수 있습니다.

1. 먼저 도구 설치: `uv add watchdog` (또는 `pip install watchdog`)
2. 실행: `vib watch`

---

## 권장 사용법

```bash
vib init
vib checkpoint "프로젝트 시작"

# AI 작업 전
vib doctor --strict
vib anchor
vib patch "원하는 변경사항"

# AI 작업 후
vib explain --write-report
vib guard --strict --write-report

# 이상 없으면 저장
vib checkpoint "완료: 작업 내용"

# 이상 있으면 되돌리기
vib undo
```

---

## 도움말

- 초보자 가이드: `VibeLign_QUICKSTART.md`
- 상세 설명서: `docs/MANUAL.md`

---

## 출시 상태

**v1.5.32** — 체크포인트/되돌리기 UX 개편 + AI 설정 파일 보호:

- `vib checkpoint` — 메시지 없이 실행하면 자동으로 메시지 입력 안내 (git commit 방식)
- `vib undo` — 완전 인터랙티브: 번호 목록 + 친숙한 시간 표시 + `[0] 취소` 옵션
- `vib history` — 초 단위 시간 표시 (`오늘 14:30:02`)로 같은 분의 체크포인트도 구별 가능
- `vib start` — 신규 사용자 온보딩에 "딱 3가지만 기억하세요" 추가 + 첫 체크포인트 바로 저장
- `vib export` — `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, `.cursorrules` 마커 보호 (덮어쓰기 방지)
- GitHub 배너 이미지 추가

**v1.5.0** — 멀티 AI 툴 설정 내보내기:

- `vib export claude` — Claude Code용 `CLAUDE.md` 안전 규칙 생성
- `vib export cursor` — Cursor용 `.cursorrules` 생성
- `vib export opencode` — OpenCode용 `OPENCODE.md` 생성
- `vib export antigravity` — Codex/에이전트용 `AGENTS.md` 생성
- 모든 내보낸 파일에 VibeLign 마커 적용 (사용자 커스텀 내용 보호)

**v1.1.0** — 코알못을 위한 핵심 기능 추가:

- `init` — VibeLign 메타데이터 초기화/재설치
- `start` — 처음 쓰는 사람용 가이드 온보딩
- `checkpoint` / `undo` — git 몰라도 되는 세이브/복구
- `protect` — 중요 파일 AI로부터 보호
- `ask` — 코드 쉬운 말로 설명받기
- `history` — 체크포인트 이력 보기

이전 개선 사항:

- 명령어 실행 방식 개선
- 더 안전한 수정 제안
- 설명과 감시 기능 향상
- 경로 처리 개선

---

## VibeLign의 철학

AI 코딩은 정말 빠릅니다. 하지만 안전장치가 없으면 프로젝트의 구조가 무너질 수 있죠.
VibeLign은 AI 개발에 **구조를 생각하는 안전함**을 더해줍니다 — 그리고 누구나 쉽게 저장하고 되돌릴 수 있게 해줍니다.

---

## 라이선스

MIT
