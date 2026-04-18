<p align="center">
  <img src="https://raw.githubusercontent.com/yesonsys03-web/VibeLign/main/assets/banner.svg" alt="VibeLign Banner" width="100%"/>
</p>

<p align="center">
  <a href="https://github.com/yesonsys03-web/VibeLign/blob/main/README.ko.md">🇰🇷 한국어</a> &nbsp;|&nbsp; <b>🇺🇸 English</b>
</p>

<p align="center">
  <video src="https://github.com/user-attachments/assets/1bbcb1da-3c61-48e3-abd4-94ec9d66ecb7"
         autoplay loop muted playsinline width="100%">
  </video>
</p>

<p align="center">
  <a href="https://pypi.org/project/vibelign/"><img src="https://img.shields.io/pypi/v/vibelign?color=7c3aed&label=vibelign" alt="PyPI"/></a>
  <a href="https://github.com/yesonsys03-web/VibeLign/releases/latest"><img src="https://img.shields.io/github/v/release/yesonsys03-web/VibeLign?color=22c55e&label=Desktop%20App" alt="GitHub Release"/></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Cursor%20%7C%20Codex-orange" alt="AI Tools"/>
</p>

---

# 🎮 VibeLign — Safety Guard for AI Coding

VibeLign (`vibelign`) is an AI coding safety **CLI + Desktop GUI** for vibe coding workflows.
It helps developers and non-developers protect project structure, save checkpoints, undo bad AI edits, manage anchors, and block secret leaks before commit.

> **🆕 v2.0**: Desktop app for macOS / Windows, per-document AI summarization, anchor intent regeneration. See [CHANGELOG](https://github.com/yesonsys03-web/VibeLign/blob/main/CHANGELOG.md) and [migration notes](https://github.com/yesonsys03-web/VibeLign/blob/main/MIGRATION_v1_to_v2.md).

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

**Desktop App (macOS / Windows)** — [📥 Download latest release](https://github.com/yesonsys03-web/VibeLign/releases/latest)

**Mac / Linux (CLI)**
```bash
pip install vibelign
vib start
```

**Windows** (PowerShell, CLI)
```powershell
# Step 1: install uv — one-time setup, auto-configures PATH
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Close and reopen PowerShell, then:
uv tool install vibelign
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

**Mac / Linux**
```bash
# 1. Install
pip install vibelign

# 2. Go to your project folder
cd my-project

# 3. Start!
vib start
```

**Windows** (PowerShell)
```powershell
# 1. Install uv — one-time setup (auto-configures PATH, no warnings)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Close and reopen PowerShell, then:

# 2. Install vibelign
uv tool install vibelign

# 3. Go to your project folder and start!
cd my-project
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

### VibeLign patch rules

- Split composite requests into `intent / source / destination / behavior_constraint`.
- If `delete` and `move` appear together, treat it as move + preservation unless the user clearly wants removal.
- Resolve `source` and `destination` by role, not with the same rule.
- If patch contract or codespeak shape changes, update tests and docs together.
- Keep terminology aligned with the shared glossary and project docs.

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
| `vib transfer` | Generate `PROJECT_CONTEXT.md` for switching AI tools |
| `vib transfer --handoff` | Add Session Handoff block so a new AI can continue immediately |
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

# Hitting a token limit or switching AI tools?
vib transfer --handoff    # generates a Session Handoff block
# Then tell the new AI: "Read PROJECT_CONTEXT.md first"
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

> **If you see "is not on your PATH" warning after install:**
> ```bash
> uv tool update-shell
> ```
> Then close and reopen your terminal. `vib` will work after that.
> If you use **bash**, run `uv tool update-shell` from inside bash, or:
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
> ```

### Option 2: pip
```bash
pip install vibelign
```

After installation, both `vib` and `vibelign` commands are available.

### Option 3: Desktop App (GUI)

Download the latest `.dmg` (macOS, Apple Silicon) or `.exe` / `.msi` (Windows) from the
[Releases page](https://github.com/yesonsys03-web/VibeLign/releases/latest).
The GUI bundles the `vib` runtime — no separate CLI install required.

> macOS first-launch: if you see "app is damaged", open Terminal and run `xattr -rc vibelign-gui.app`
> (ad-hoc signed, not notarized).

### Windows — if `vib` is not recognized after pip install

When you install with pip on Windows, `vib.exe` is placed in the Python `Scripts` folder which may not be in PATH.
The pip warning message shows the exact path you need to add:

```
WARNING: The scripts vib.exe ... are installed in 'C:\Users\...\Scripts' which is not on PATH.
```

**To fix manually:**
1. Press `Win + R` → type `sysdm.cpl` → Enter
2. **Advanced** tab → **Environment Variables**
3. Under **System variables**, find `Path` → click **Edit**
4. Click **New** and paste the `Scripts` path shown in the pip warning
   - Example: `C:\Users\YourName\AppData\Local\Programs\Python\Python312\Scripts\`
5. Click OK → fully close and reopen PowerShell

> **Tip:** Use `uv tool install vibelign` to skip this entirely — uv handles PATH automatically.

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

**v2.0.0** — Desktop GUI + MCP/Patch Modularization + AI Opt-In:

- 🖥️ **VibeLign GUI (macOS / Windows)** — Tauri desktop app
  - Doctor page: one-click diagnosis + auto-apply
  - Anchor card: anchor insertion + intent/aliases regeneration (code-based / AI-based, `--force` overwrites prior AI results)
  - DocsViewer: per-document AI summarization
  - Settings: API key management, global AI opt-in toggle
- 🔌 **MCP server refactored** — `vibelign/mcp/` with dispatch/handlers/tool_specs split
- 🧩 **Patch module split** — `vibelign/patch/` (builder · handoff · preview · targeting · …)
- 🤖 **AI opt-in** — consent UI removed, single global toggle in Settings; Anthropic / OpenAI / Gemini auto-selected
- ⚡ **onedir runtime** — PyInstaller `onefile → onedir` removes GUI cold-start (1–3 s → instant)
- 🏷️ **Anchor `_source` field** — `anchor_meta.json` now tracks `code / ai / manual / ai_failed` so AI/manual results are protected from code-based regeneration (use `--force` to override)
- ⚠️ **Breaking**: `vibelign.vib_cli` → `vibelign.cli.vib_cli`; `vibelign.mcp_server` → `vibelign.mcp.mcp_server`
- See [CHANGELOG.md](https://github.com/yesonsys03-web/VibeLign/blob/main/CHANGELOG.md) · [MIGRATION_v1_to_v2.md](https://github.com/yesonsys03-web/VibeLign/blob/main/MIGRATION_v1_to_v2.md)

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
