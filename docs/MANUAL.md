# VibeGuard Manual

This manual explains how to use VibeGuard before, during, and after AI-assisted edits.

---

## 1. What VibeGuard is for

VibeGuard is a safety layer for AI coding workflows.

It does **not** replace your AI tool.
It helps you keep the project stable while using tools like:

- Claude Code
- OpenCode
- Cursor
- Antigravity
- general GPT-based coding workflows

The core idea is simple:

> Let AI generate code, but do not let it freely destroy project structure.
> And always make it easy to save and undo.

---

## 2. The safest workflow

### New project

```bash
vibeguard init
```

This sets up everything in one command.

### Ongoing workflow

Use this loop whenever you ask AI to change code:

```bash
vibeguard checkpoint "before your task"
vibeguard doctor --strict
vibeguard anchor
vibeguard patch "your request here"
# ask AI using the generated patch request
vibeguard explain --write-report
vibeguard guard --strict --write-report

# if all good:
vibeguard checkpoint "done: your task"

# if something broke:
vibeguard undo
```

---

## 3. Command reference

---

## `vibeguard init`

One-command project setup for beginners.

```bash
vibeguard init
vibeguard init --tool claude
vibeguard init --tool cursor
vibeguard init --tool opencode
vibeguard init --tool antigravity
```

What it does:

1. Exports `AI_DEV_SYSTEM_SINGLE_FILE.md` and `AGENTS.md` to the project root
2. Exports tool-specific helper files (`vibeguard_exports/<tool>/`)
3. Creates a `.gitignore` if one does not exist
4. Runs `git init` if the project is not a Git repo yet
5. Creates the first checkpoint automatically

After `init`, your project is fully ready for AI-assisted development.

---

## `vibeguard checkpoint`

Saves the current project state as a restore point (uses Git under the hood).

```bash
vibeguard checkpoint "before login feature"
vibeguard checkpoint "added signup validation"
vibeguard checkpoint
```

- If no message is given, a timestamp is used automatically.
- Shows a list of changed files before saving.
- Displays the total number of checkpoints saved.

Think of it as a **game save point** for your code.

---

## `vibeguard undo`

Restores the project to the last checkpoint.

```bash
vibeguard undo
vibeguard undo --list
```

Behavior:

- If there are **unsaved changes** → restores to the last commit (like pressing "undo" in a game)
- If the working tree is **already clean** → rolls back to the previous checkpoint commit
- `--list` → shows the list of available checkpoints to choose from

Use this when AI broke something and you want to go back.

---

## `vibeguard history`

Shows all saved checkpoints.

```bash
vibeguard history
```

Displays:

- checkpoint number
- when it was saved (e.g. "2 hours ago")
- the message you gave it

Also shows:

- total checkpoint count
- most recent save time
- reminder of how to undo or save a new checkpoint

---

## `vibeguard protect`

Locks important files so AI cannot accidentally modify them.

```bash
vibeguard protect main.py
vibeguard protect src/config.py
vibeguard protect --list
vibeguard protect --remove main.py
```

- Protected files are tracked in `.vibeguard_protected`
- `guard` and `watch` will warn you if a protected file was changed
- Use this for files that must never be touched by AI

---

## `vibeguard ask`

Generates a plain-language explanation prompt for a file.

```bash
vibeguard ask login.py
vibeguard ask login.py "what does the validate function do?"
vibeguard ask login.py --write
```

What it does:

- Reads the file
- Builds a prompt asking an AI to explain it in plain Korean
- With `--write`: saves the prompt to `VIBEGUARD_ASK.md`
- Without `--write`: prints the prompt so you can copy it

Use this when you do not understand a file and want to ask AI to explain it before editing.

Notes:

- Files over 300 lines are truncated to the first 300 lines
- The prompt includes the filename, line count, and file content

---

## `vibeguard doctor`

Checks structural issues.

```bash
vibeguard doctor
vibeguard doctor --strict
vibeguard doctor --json
```

Looks for:

- oversized entry files
- huge files
- catch-all files
- missing anchors
- UI + business logic mixing
- too many definitions in one file

Use `--strict` when you want earlier warnings.

---

## `vibeguard anchor`

Adds module-level anchors to source files that do not have them yet.

```bash
vibeguard anchor
vibeguard anchor --dry-run
vibeguard anchor --only-ext .py,.js
```

Important behavior:

- skips docs, tests, GitHub workflow folders, virtualenvs, and dependency folders by default
- does not rewrite files that already contain anchors

Example anchor:

```python
# === ANCHOR: BACKUP_WORKER_START ===
# code
# === ANCHOR: BACKUP_WORKER_END ===
```

Why this matters:
AI can be instructed to edit only inside an anchor instead of rewriting the full file.

---

## `vibeguard patch`

Builds a safer AI prompt.

```bash
vibeguard patch "add progress indicator to backup worker"
vibeguard patch "add progress indicator to backup worker" --json
```

Outputs:

- suggested target file
- suggested target anchor
- confidence
- rationale

It also writes:

```text
VIBEGUARD_PATCH_REQUEST.md
```

This file can be pasted directly into your AI coding tool.

Notes:

- files like `__init__.py`, tests, docs, and cache folders are strongly deprioritized
- if the project has no useful source files yet, confidence becomes low

---

## `vibeguard explain`

Explains recent changes in human language.

```bash
vibeguard explain
vibeguard explain --write-report
vibeguard explain --json
vibeguard explain --since-minutes 30
```

Primary mode:
- uses Git status if available

Fallback mode:
- uses recently modified files
- intentionally avoids overreacting on freshly created repos

Output includes:

- summary
- what changed
- why it matters
- risk level
- rollback hint

When `--write-report` is used, this is saved:

```text
VIBEGUARD_EXPLAIN.md
```

---

## `vibeguard guard`

Combines `doctor` + `explain`.

```bash
vibeguard guard
vibeguard guard --strict
vibeguard guard --json
vibeguard guard --write-report
```

This answers:

> "Is it safe to continue with another AI edit right now?"

Output includes:

- overall level
- whether the session should be considered blocked
- recommendations
- doctor findings
- recent changed files
- protected file violations (if any)

Saved report:

```text
VIBEGUARD_GUARD.md
```

---

## `vibeguard export`

Creates helper files for tool-specific workflows.

```bash
vibeguard export claude
vibeguard export opencode
vibeguard export cursor
vibeguard export antigravity
```

This creates:

```text
vibeguard_exports/<tool>/
```

Also creates in the project root:

- `AI_DEV_SYSTEM_SINGLE_FILE.md` — the full ruleset
- `AGENTS.md` — auto-read by Claude Code, OpenCode, and other AI tools

Examples:

- Claude → `RULES.md`, `SETUP.md`, `PROMPT_TEMPLATE.md`
- OpenCode → `RULES.md`, `SETUP.md`, `PROMPT_TEMPLATE.md`
- Cursor → `RULES.md` (`.cursorrules` format), `SETUP.md`, `PROMPT_TEMPLATE.md`
- Antigravity → `TASK_ARTIFACT.md`, `VERIFICATION_CHECKLIST.md`, `SETUP.md`

---

## `vibeguard watch`

Real-time monitor while AI or you edit files.

```bash
vibeguard watch
vibeguard watch --strict
vibeguard watch --write-log
vibeguard watch --json
vibeguard watch --debounce-ms 800
```

Extra dependency required:

```bash
pip install watchdog
```

or

```bash
uv add watchdog
```

Watch detects:

- entry files growing too large
- catch-all filenames
- larger files with no anchors
- likely UI + business logic mixing
- likely business logic inside entry files
- changes to protected files

Log file if enabled:

```text
.vibeguard/watch.log
```

State file:

```text
.vibeguard/watch_state.json
```

If `watchdog` is missing, only the `watch` command fails gracefully.
All other commands continue to work.

---

## 4. Recommended project rules

Best results come from these conventions:

- run `init` when starting a new project
- save a `checkpoint` before every AI edit
- use `undo` immediately if something looks wrong
- `protect` files that must never change
- keep entry files tiny
- split large files before AI keeps growing them
- add anchors before repeated edits
- prefer patch requests over vague instructions
- run `guard` before another large AI change

---

## 5. Suggested installation strategy

Recommended:

- Python package use: `uv`
- JS helper ecosystem: `pnpm`

Still supported:

- `pip`
- `npm`

Good future distribution option on macOS:

- Homebrew

---

## 6. Troubleshooting

### `watch` says watchdog is missing
Install it:

```bash
pip install watchdog
```

### `patch` suggested the wrong file
Use the JSON output, inspect the rationale, then manually edit the generated markdown request.

### `guard` seems too noisy
Prefer Git repositories.
Fallback mtime mode is intentionally conservative, but calmer than before.

### `anchor` touched files you did not want
Use:

```bash
vibeguard anchor --dry-run
vibeguard anchor --only-ext .py
```

### `undo` says there are no checkpoints
Run `vibeguard checkpoint "initial"` first to create your first save point.

### `protect` list is empty
Run `vibeguard protect <filename>` to add files to the protected list.

---

## 7. Typical initial setup

New project:

```bash
vibeguard init
```

That's it. Everything else is set up automatically.

Existing project:

```bash
vibeguard doctor
vibeguard anchor --dry-run
vibeguard anchor
vibeguard export opencode
vibeguard checkpoint "vibeguard added"
```

---

## 8. Final advice

The safest pattern is:

> checkpoint first, AI second, guard always

That is exactly what VibeGuard is for.
