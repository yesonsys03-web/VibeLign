<p align="center">
  <img src="https://raw.githubusercontent.com/yesonsys03-web/VibeLign/main/assets/banner.svg" alt="VibeLign Banner" width="100%"/>
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

# 🎮 VibeLign — Safety Guard for AI Coding

VibeLign (`vibelign`) is an AI coding safety CLI for vibe coding workflows.
It helps developers and non-developers protect project structure, save checkpoints, undo bad AI edits, manage anchors, and block secret leaks before commit.

Documentation: `https://yesonsys03-web.github.io/VibeLign/`  
Repository: `https://github.com/yesonsys03-web/VibeLign`  
Issues: `https://github.com/yesonsys03-web/VibeLign/issues`  
Releases: `https://github.com/yesonsys03-web/VibeLign/releases`

> ### Sound familiar?
>
> - You asked AI to add a small feature — it **rewrote the entire file**
> - All code ended up in `main.py` — **1000+ lines, impossible to manage**
> - AI touched other files and now nothing works
> - You want to undo but don't know how
>
> **That's why we made this!**

```bash
pip install vibelign
vib start
```

![Quick Start](https://raw.githubusercontent.com/yesonsys03-web/VibeLign/main/assets/quickstart_en.jpeg)

---

## 🤔 What is VibeLign?

AI coding tools (Claude Code, Cursor, etc.) write code fast. But they have **problems**:

| Problem | VibeLign Fixes It |
|---------|-------------------|
| All code goes into `main.py` | AI **organizes** code properly |
| AI does something different from what you asked | Creates **precise edit requests** |
| Code breaks and you can't go back | **Save & Undo** feature |

**Works with any AI tool**: Claude Code · Cursor · Codex · OpenCode

---

## 📝 Just 3 Things to Remember

```
Before AI edits  →  vib checkpoint "before work"    # save
AI broke it      →  vib undo                         # undo
Looks good       →  vib checkpoint "done"             # save again
```

> No Git knowledge needed. Just type `vib`.

---

## 🚀 Start in 3 Steps

```bash
# 1. Install
pip install vibelign

# 2. Go to your project folder
cd my-project

# 3. Start!
vib start
```

---

## 📚 All Commands

### Basics (Must Know)

| Command | What It Does |
|---------|--------------|
| `vib start` | First time only! Set up project |
| `vib checkpoint "message"` | Save current state (like game save) |
| `vib checkpoint` | Will ask for a message |
| `vib undo` | Go back to last save |
| `vib history` | See all saves |

### When Asking AI to Code

| Command | What It Does |
|---------|--------------|
| `vib patch "add button"` | Tell AI exactly how to edit (Korean OK!) |
| `vib anchor` | Mark safe areas for AI to edit |
| `vib scan` | Clean up files + check status |

### Checking & Verification

| Command | What It Does |
|---------|--------------|
| `vib doctor` | Check project health |
| `vib explain` | Explain changes in plain language |
| `vib guard` | Check if code is broken |
| `vib ask filename.py` | Ask AI to explain a file |

### File Protection

| Command | What It Does |
|---------|--------------|
| `vib protect filename.py` | Lock important files (AI can't touch) |
| `vib protect --list` | See locked files |
| `vib protect --remove filename.py` | Unlock file |
| `vib secrets --staged` | Block staged API keys, tokens, and `.env` files before commit |

### Settings & Export

| Command | What It Does |
|---------|--------------|
| `vib config` | Set API keys |
| `vib export claude` | Create Claude Code settings |
| `vib export cursor` | Create Cursor settings |
| `vib export opencode` | Create OpenCode settings |

### Other Useful Commands

| Command | What It Does |
|---------|--------------|
| `vib watch` | Monitor file changes in real-time |
| `vib bench` | Test how effective anchors are |
| `vib manual` | Show detailed user guide |
| `vib rules` | Show all AI development rules |
| `vib transfer` | Keep project info when switching AI tools |
| `vib completion` | Set up tab autocomplete |
| `vib install` | Show step-by-step installation guide |

---

## 💡 Recommended Workflow

```bash
# First time
vib start

# Before AI edits
vib checkpoint "before login feature"
vib doctor --strict
vib patch "create login button"

# After AI edits
vib explain --write-report
vib guard --strict --write-report

# If done
vib checkpoint "login feature done!"

# If something broke
vib undo
```

`vib start` now also enables Git secret protection automatically when your project uses Git.
Before each commit, VibeLign checks staged changes for API keys, tokens, private keys, and secret-like files such as `.env`.

```bash
# Check manually anytime
vib secrets --staged
```

---

## 🔧 Installation

### Option 1: uv (Recommended, faster)
```bash
uv tool install vibelign
```

### Option 2: pip
```bash
pip install vibelign
```

After installation, both `vib` and `vibelign` commands are available.

---

## 📖 Want to Learn More?

```bash
vib manual          # Detailed user guide
vib manual rules    # AI development rules only
vib rules           # Same as above
```

---

## 🎯 Our Promise

> *"AI coding is fast. But without safety guards, it can destroy what you built."*

VibeLign promises:
- ✅ Save in 1 second (`vib checkpoint "description"`)
- ✅ Undo in 1 second (`vib undo`)
- ✅ No Git knowledge needed
- ✅ Easy for beginners

---

⭐ **If VibeLign saved your code, a Star would mean a lot — thank you!**

---

## 📋 Release Notes

**v1.6.0** — MCP Server + AI Development Rules System:

- `vib mcp` — MCP (Model Context Protocol) server for Claude Desktop integration
- `vib start` — Auto-register VibeLign MCP for Claude Code and Cursor without overwriting existing Cursor MCP servers
- `vib rules` — View all AI development rules directly in CLI
- `vib manual rules` — Detailed rules manual
- Anchor intent system — Store intent information in anchors
- Korean tokenizer — Accurately interpret patch requests in Korean
- AI_DEV_SYSTEM — Added maintainability/function design rules (Section 6-1, 14)
- `vib scan` bug fix — Fixed missing set_intent attribute

**v1.5.32** — Checkpoint & Undo UX Overhaul + AI Config File Protection:

- `vib checkpoint` — Message prompt support
- `vib undo` — Number selection + cancel option `[0]`
- `vib history` — Second-precision timestamps
- `vib start` — Beginner onboarding + auto first checkpoint
- `vib export` — AGENTS.md, CLAUDE.md, OPENCODE.md, .cursorrules protection

**v1.5.0** — Multi-Tool AI Config Export:

- `vib export claude` — Generate CLAUDE.md for Claude Code
- `vib export cursor` — Generate .cursorrules for Cursor
- `vib export opencode` — Generate OPENCODE.md for OpenCode
- `vib export antigravity` — Generate AGENTS.md for Codex/agents
- Added VibeLign markers to exported files (prevent overwriting)

**v1.1.0** — Core Features for Beginners:

- `vib init` — Initialize/reset VibeLign
- `vib start` — First-time user guide
- `vib checkpoint` / `vib undo` — Save & restore without Git
- `vib protect` — Lock important files
- `vib ask` — Generate AI explanation prompts
- `vib history` — View checkpoint history

---

# License

MIT
