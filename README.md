# VibeGuard

**AI coding safety system for vibecoders.**

AI writes code fast.  
VibeGuard keeps your project safe.

---

# Quick Start

![Quickstart](assets/quickstart_en.png)

---

# Why VibeGuard?

AI coding is powerful, but it often creates structural problems:

- giant `main.py`
- random `utils.py` catch-all files
- whole-file rewrites
- mixed UI + business logic
- uncontrolled wide patches

These problems are common when using:

- Claude Code
- Cursor
- OpenCode
- GPT coding workflows
- AI coding agents

VibeGuard adds **guardrails** so AI edits remain safe.

---

# AI Coding Workflow

Recommended loop:

doctor → anchor → patch → AI edit → explain → guard

| Command | Purpose |
|------|------|
| doctor | analyze project structure |
| anchor | insert safe edit anchors |
| patch | generate safe AI patch request |
| explain | explain recent changes |
| guard | verify project safety |

---

# Core Commands

```
vibeguard doctor
vibeguard anchor
vibeguard patch "add progress bar"
vibeguard explain
vibeguard guard
vibeguard export claude
vibeguard export opencode
vibeguard export antigravity
vibeguard watch
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

---

# First Test

Run these commands:

```
vibeguard doctor
vibeguard anchor --dry-run
vibeguard patch add progress bar --json
vibeguard explain --json
vibeguard guard --json
```

If these commands work, VibeGuard is installed correctly.

---

# Visual Guide (Korean)

![빠른 시작 가이드](assets/quickstart_kr.png)

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
vibeguard watch
```

---

# Recommended Workflow

```
vibeguard doctor --strict
vibeguard anchor
vibeguard patch add progress indicator to backup worker
vibeguard explain --write-report
vibeguard guard --strict --write-report
```

---

# Documentation

Beginner guide:

```
QUICKSTART.md
```

Full documentation:

```
docs/MANUAL.md
```

---

# Release Status

This is the **final pre-1.0 release candidate** with:

- fixed CLI import behavior
- safer patch suggestions
- improved fallback explain/guard logic
- better path handling

---

# Philosophy

AI coding is fast.

But without guardrails, it can break project structure.

VibeGuard adds **structure-aware safety** to AI-driven development.

---

# License

MIT

---

# VibeGuard (한글 번역)

**AI 코딩 안전 시스템: 바이브코더를 위한 보호막**

AI는 코드를 정말 빨리 작성하지만, 가끔 프로젝트를 엉망으로 만들기도 합니다. 
VibeGuard는 여러분의 소중한 프로젝트를 안전하게 지켜줍니다.

---

## 퀵 스타트 (빨리 시작하기)

![퀵스타트 가이드](assets/quickstart_kr.png)

---

## 왜 VibeGuard가 필요한가요?

AI로 코딩을 하면 힘은 세지지만, 가끔 규칙 없는 코드가 생겨서 문제가 됩니다:

- `main.py` 파일 하나에 모든 코드가 다 들어가서 너무 커질 때
- 아무 코드나 다 모아둔 정체불명의 `utils.py` 파일이 생길 때
- AI가 마음대로 파일 전체를 싹 다 새로 써버릴 때
- 화면 디자인(UI)과 실제 기능(로직)이 마구 뒤섞일 때
- 여기저기 너무 넓은 범위를 한꺼번에 고쳐서 감당이 안 될 때

Claude Code, Cursor, OpenCode 같은 AI 도구를 쓸 때 이런 일이 자주 생깁니다. VibeGuard는 AI가 안전하게 코드를 고칠 수 있도록 **가이드라인(안전 난간)**을 쳐줍니다.

---

## AI 코딩 작업 순서

VibeGuard가 추천하는 안전한 개발 순서:

**검사(doctor) → 고정(anchor) → 계획(patch) → AI 수정 → 설명(explain) → 감시(guard)**

| 명령어 | 하는 일 |
|------|------|
| doctor | 프로젝트 구조가 괜찮은지 분석해요 |
| anchor | 안전하게 고칠 수 있는 구역(앵커)을 정해요 |
| patch | AI에게 보낼 안전한 수정 요청서를 만들어요 |
| explain | 최근에 바뀐 내용을 알기 쉽게 설명해줘요 |
| guard | 프로젝트가 여전히 안전한지 검사해요 |

---

## 핵심 명령어

```bash
vibeguard doctor
vibeguard anchor
vibeguard patch "진행 표시바 추가해줘"
vibeguard explain
vibeguard guard
vibeguard export claude
vibeguard export opencode
vibeguard export antigravity
vibeguard watch
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

---

## 첫 번째 테스트

제대로 설치됐는지 터미널에 입력해 보세요:

```bash
vibeguard doctor
vibeguard anchor --dry-run
vibeguard patch add progress bar --json
vibeguard explain --json
vibeguard guard --json
```

이 명령어들이 잘 작동한다면 준비 끝!

---

## 시각 가이드

![빠른 시작 가이드](assets/quickstart_kr.png)

---

## 실시간 감시 모드 (선택 사항)

파일이 바뀔 때마다 실시간으로 지켜보게 할 수 있습니다.

1. 먼저 도구 설치: `uv add watchdog` (또는 `pip install watchdog`)
2. 실행: `vibeguard watch`

---

## 권장 사용법

```bash
vibeguard doctor --strict
vibeguard anchor
vibeguard patch "백업 작업에 진행 표시기 추가"
vibeguard explain --write-report
vibeguard guard --strict --write-report
```

---

## 도움말

- 초보자 가이드: `QUICKSTART.md`
- 상세 설명서: `docs/MANUAL.md`

---

## 출시 상태

이 버전은 **1.0 정식 버전이 나오기 전의 마지막 테스트 버전(Release Candidate)**입니다. 
명령어 실행 방식이 개선되었고, 더 안전한 수정 제안을 해주며, 설명과 감시 기능이 더 똑똑해졌습니다.

---

## VibeGuard의 철학

AI 코딩은 정말 빠릅니다. 하지만 안전장치가 없으면 프로젝트의 구조가 무너질 수 있죠.
VibeGuard는 AI 개발에 **구조를 생각하는 안전함**을 더해줍니다.

---

## 라이선스

MIT
