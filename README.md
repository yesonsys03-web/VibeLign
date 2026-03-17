<p align="center">
  <img src="assets/banner.svg" alt="VibeLign Banner" width="100%"/>
</p>

<p align="center">
  <a href="README.ko.md">🇰🇷 한국어</a> &nbsp;|&nbsp; <b>🇺🇸 English</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/vibelign/"><img src="https://img.shields.io/pypi/v/vibelign?color=7c3aed&label=vibelign" alt="PyPI"/></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Cursor%20%7C%20Codex-orange" alt="AI Tools"/>
</p>

---

# VibeLign

> ### Sound familiar?
>
> - You asked AI to add one small feature — it **rewrote the entire file**
> - Everything ended up crammed into `main.py` — **1000+ lines, zero structure**
> - AI changed something you didn't ask for — **now nothing works**
> - You want to undo it — **but you don't know Git, and Ctrl+Z is useless**
>
> **VibeLign was built for exactly this.**

```bash
pip install vibelign
vib start
```

---

# What VibeLign Does

Most AI coding tools are great at writing code fast — but terrible at **staying in bounds**.

VibeLign solves three problems that beginners hit every day:

| Problem | VibeLign's fix |
|---------|----------------|
| 🏚️ AI dumps everything into `main.py` | Injects **structure rules** so AI organizes code properly |
| 🤖 AI ignores your instructions and does its own thing | Generates a **precise patch request** AI actually follows |
| 💥 AI edits go wrong and you can't go back | **Checkpoint + Undo** — restore any saved state in seconds |

Works with: **Claude Code · Cursor · Codex · OpenCode · any AI coding agent**

---

# Just 3 Things to Remember

```
Before AI edits  →  vib checkpoint "description"   # save state
AI broke it      →  vib undo                        # instant rollback
Looks good       →  vib checkpoint "done"           # save again
```

> No Git knowledge needed. No fear required. Just `vib`.

---

# Why VibeLign?

AI coding tools write code fast — but they often go off the rails:

- Ask for one change → AI rewrites three files you didn't touch
- Ask for a new feature → everything gets stuffed into `main.py`
- AI "fixes" something → breaks something else entirely
- No structure, no rules, no way back

VibeLign puts **guardrails on AI** so it edits only what you asked, structures code properly, and gives you a save point to fall back on.

Works with: **Claude Code · Cursor · Codex · OpenCode · any AI coding agent**

---

# Quick Start

```bash
# 1. Install
pip install vibelign

# 2. Go to your project folder
cd your-project

# 3. Start
vib start
```

---

# AI Coding Workflow

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
vib start                               # guided onboarding for beginners

# --- Save & restore ---
vib checkpoint "before login feature"   # save with message
vib checkpoint                          # will prompt for message
vib undo                                # pick checkpoint from list
vib history                             # view all saves

# --- File protection ---
vib protect main.py
vib protect --list
vib protect --remove main.py

# --- Ask AI to explain a file ---
vib ask login.py
vib ask login.py --write

# --- AI coding workflow ---
vib doctor
vib anchor
vib scan
vib patch "add progress bar"
vib patch "로그인 버튼 추가해줘"    # Korean supported
vib explain
vib guard

# --- Export AI config files ---
vib export claude       # CLAUDE.md for Claude Code
vib export cursor       # .cursorrules for Cursor
vib export opencode     # OPENCODE.md for OpenCode
vib export antigravity  # AGENTS.md for Codex / agents

# --- Monitor ---
vib watch
```

---

# Install

### Recommended (uv)
```bash
uv tool install vibelign
```

### Alternative (pip)
```bash
pip install vibelign
```

After installation both `vib` and `vibelign` commands are available.

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

# Release Status

**v1.5.32** — Checkpoint & Undo UX overhaul + AI config file protection:

- `vib checkpoint` — now prompts for a message when none is given (like `git commit`)
- `vib undo` — fully interactive: numbered list with friendly timestamps, cancel option `[0]`
- `vib history` — timestamps show seconds (`오늘 14:30:02`) to distinguish same-minute saves
- `vib start` — new user onboarding shows "3 things to remember" + saves first checkpoint
- `vib export` — `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, `.cursorrules` protected by markers (no overwrite)
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

> *"AI coding is fast. But without guardrails, it can destroy what you built."*

Whether you're a seasoned dev or a total beginner — if you're using AI to build software, VibeLign is your safety net.

**VibeLign's promise:**
- Save in 1 second (`vib checkpoint "description"`)
- Restore in 1 second (`vib undo`)
- Nothing to learn. No Git needed. No fear.

---

⭐ **If VibeLign saved your code, a Star means a lot — thank you!**

---

# License

MIT
