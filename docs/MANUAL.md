# VibeLign Manual

This manual explains how to use VibeLign before, during, and after AI-assisted edits.

The primary CLI command is **`vib`**. The legacy `vibelign` command is also supported as a backward-compatible wrapper.

---

## 1. What VibeLign is for

VibeLign is a safety layer for AI coding workflows.

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

### New project (beginner)

```bash
vib start
```

Interactive guided setup — runs init, hooks, and health check.

### Existing project / re-initialize

```bash
vib init
```

Sets up or resets VibeLign metadata.

### Ongoing workflow

Use this loop whenever you ask AI to change code:

```bash
vib checkpoint "before your task"
vib doctor --strict
vib anchor
vib patch "your request here"
# ask AI using the generated patch request
vib explain --write-report
vib guard --strict --write-report

# if all good:
vib checkpoint "done: your task"

# if something broke:
vib undo
```

---

## 3. Command reference

---

## `vib init`

VibeLign 메타데이터를 초기화(또는 재초기화)합니다.

```bash
vib init
```

What it does:

1. Exports `AI_DEV_SYSTEM_SINGLE_FILE.md` and `AGENTS.md` to the project root
2. Creates `.vibelign/` directory with config, state, and project map
3. Creates a `.gitignore` entry if needed
4. Scans project structure and builds `project_map.json`

Use `vib init` to set up or reset VibeLign metadata.

---

## `vib start`

Beginner-friendly guided setup with interactive onboarding.

```bash
vib start
vib start "first save"
```

What it does:

- Ensures AI rule files exist (creates if missing, keeps if present)
- Sets up AI tool hooks (e.g. Claude Code auto-checkpoint)
- Runs a project health check and shows the score
- Guides you to the recommended next step

Use `vib start` if you are new to VibeLign or want a guided walkthrough.
Note: `vib start` and `vib init` are separate commands with different purposes.

---

## `vib checkpoint`

Saves the current project state as a restore point (uses Git under the hood).

```bash
vib checkpoint "before login feature"
vib checkpoint "added signup validation"
vib checkpoint
```

- If no message is given, a timestamp is used automatically.
- Shows a list of changed files before saving.
- Displays the total number of checkpoints saved.

Think of it as a **game save point** for your code.

---

## `vib undo`

Restores the project to the last checkpoint.

```bash
vib undo
vib undo --list
```

Behavior:

- If there are **unsaved changes** → restores to the last commit (like pressing "undo" in a game)
- If the working tree is **already clean** → rolls back to the previous checkpoint commit
- `--list` → shows the list of available checkpoints to choose from

Use this when AI broke something and you want to go back.

---

## `vib history`

Shows all saved checkpoints.

```bash
vib history
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

## `vib protect`

Locks important files so AI cannot accidentally modify them.

```bash
vib protect main.py
vib protect src/config.py
vib protect --list
vib protect --remove main.py
```

- Protected files are tracked in `.vibelign_protected`
- `guard` and `watch` will warn you if a protected file was changed
- Use this for files that must never be touched by AI

---

## `vib config`

Sets API keys and Gemini model preferences.

```bash
vib config
```

What it does:

- Guides you through saving API keys to your shell profile or current session
- If Gemini is selected, shows available Gemini model IDs
- Saves `GEMINI_MODEL` when you choose a Gemini model

Notes:

- When a Gemini API key is available, VibeLign tries to fetch the current official model list from Google AI Studio
- If the live model list cannot be fetched, VibeLign falls back to a built-in recommended Gemini model list
- Press Enter or choose `0` to keep the current Gemini model setting unchanged

---

## `vib ask`

Generates a plain-language explanation prompt for a file.

```bash
vib ask login.py
vib ask login.py "what does the validate function do?"
vib ask login.py --write
GEMINI_MODEL=gemini-2.5-flash-lite vib ask login.py
```

What it does:

- Reads the file
- Builds a prompt asking an AI to explain it in plain Korean
- With `--write`: saves the prompt to `VIBELIGN_ASK.md`
- Without `--write`: prints the prompt so you can copy it

Use this when you do not understand a file and want to ask AI to explain it before editing.

Notes:

- Files over 300 lines are truncated to the first 300 lines
- The prompt includes the filename, line count, and file content
- If Gemini is the provider that runs, it uses `gemini-3-flash-preview` by default
- You can override the Gemini model for one command by setting `GEMINI_MODEL`

---

## `vib doctor`

Checks structural issues.

```bash
vib doctor
vib doctor --strict
vib doctor --json
```

Looks for:

- oversized entry files
- huge files (300+ warning, 500+ strong warning, 800+ critical)
- catch-all files
- missing anchors
- UI + business logic mixing
- too many definitions in one file
- circular imports and missing internal module targets

Use `--strict` when you want earlier warnings.

---

## `vib anchor`

Adds module-level anchors to source files that do not have them yet.

```bash
vib anchor
vib anchor --dry-run
vib anchor --only-ext .py,.js
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

### Anchor intent metadata

You can attach intent descriptions to anchors in `.vibelign/anchor_meta.json`.
This improves patch suggestion accuracy when using `vib patch`.

Format:

```json
{
  "LOGIN_FORM": {
    "intent": "이메일/비밀번호 입력받아 로그인 처리",
    "connects": ["AUTH_API"],
    "warning": "수정 시 AUTH_API에 영향"
  }
}
```

This file is written programmatically via the Python API (`set_anchor_intent`) or edited manually.

---

## `vib scan`

Runs anchor scan + anchor index update + project map refresh in a single command.

```bash
vib scan
vib scan --auto
```

What it does:

1. Runs `vib anchor --suggest` (or `--auto` if flag given)
2. Rebuilds `.vibelign/anchor_index.json`
3. Regenerates `.vibelign/project_map.json` with the latest anchor index

Use `vib scan` instead of running `vib anchor` and `vib init` separately.
This is the recommended way to keep the project map fresh after adding anchors.

---

## `vib patch`

Builds a safer AI prompt.

```bash
vib patch "로그인 버튼 추가해줘"
vib patch "add progress indicator to backup worker"
vib patch "add progress indicator to backup worker" --json
```

Outputs:

- suggested target file and anchor (CodeSpeak + 앵커 위치 요약)
- confidence
- rationale

Korean requests are fully supported:

```bash
vib patch "로그인 버튼 크기 키워줘"
vib patch "장바구니 삭제 버튼 추가해줘"
vib patch "비밀번호 버그 고쳐줘"
```

Notes:

- files like `__init__.py`, tests, docs, and cache folders are strongly deprioritized
- if the project has no useful source files yet, confidence becomes low
- if anchor intent metadata exists in `.vibelign/anchor_meta.json`, it is used to improve anchor matching accuracy

---

## `vib explain`

Explains recent changes in human language.

```bash
vib explain
vib explain --write-report
vib explain --json
vib explain --since-minutes 30
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
VIBELIGN_EXPLAIN.md
```

---

## `vib guard`

Combines `doctor` + `explain`.

```bash
vib guard
vib guard --strict
vib guard --json
vib guard --write-report
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
VIBELIGN_GUARD.md
```

---

## `vib export`

Creates helper files for tool-specific workflows.

```bash
vib export claude
vib export opencode
vib export cursor
vib export antigravity
```

This creates:

```text
vibelign_exports/<tool>/
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

## `vib watch`

Real-time monitor while AI or you edit files.

```bash
vib watch
vib watch --strict
vib watch --write-log
vib watch --json
vib watch --debounce-ms 800
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

**Auto project map refresh:**
When files change, `vib watch` automatically refreshes `.vibelign/project_map.json` after a debounce period (default 800ms). The map update uses a temp-file swap to avoid partial reads. Status messages are printed:

```
⏳ 코드맵 갱신 중... (파일 3개 변경)
✅ 파일 3개 변경 감지 → 코드맵 자동 갱신 완료
```

Log file if enabled:

```text
.vibelign/watch.log
```

State file:

```text
.vibelign/watch_state.json
```

If `watchdog` is missing, only the `watch` command fails gracefully.
All other commands continue to work.

---

## 4. Recommended project rules

Best results come from these conventions:

- run `vib init` when starting a new project
- save a `vib checkpoint` before every AI edit
- use `vib undo` immediately if something looks wrong
- `vib protect` files that must never change
- keep entry files tiny
- split large files before AI keeps growing them
- run `vib scan` after adding anchors to keep the project map fresh
- prefer patch requests over vague instructions (Korean is supported)
- run `vib guard` before another large AI change

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
vib anchor --dry-run
vib anchor --only-ext .py
```

### `undo` says there are no checkpoints
Run `vib checkpoint "initial"` first to create your first save point.

### `protect` list is empty
Run `vib protect <filename>` to add files to the protected list.

---

## 7. Typical initial setup

New project:

```bash
vib init
```

That's it. Everything else is set up automatically.

Existing project:

```bash
vib doctor
vib anchor --dry-run
vib anchor
vib export opencode
vib checkpoint "vibelign added"
```

---

## 8. Backward compatibility

The legacy `vibelign` command is maintained as a wrapper that delegates to `vib`. All commands work with both:

```bash
vib doctor        # primary
vibelign doctor   # also works (backward-compatible wrapper)
```

---

## 9. Final advice

The safest pattern is:

> checkpoint first, AI second, guard always

That is exactly what VibeLign is for.
