# VibeGuard Manual

This manual explains how to use VibeGuard before, during, and after AI-assisted edits.

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

---

## 2. The safest workflow

Use this loop whenever you ask AI to change code:

```bash
vibeguard doctor --strict
vibeguard anchor
vibeguard patch "your request here"
# ask AI using the generated patch request
vibeguard explain --write-report
vibeguard guard --strict --write-report
```

What each step does:

### `doctor`
Checks structure problems before editing.

### `anchor`
Adds safe edit zones so AI is less likely to rewrite whole files.

### `patch`
Generates a structured patch request with a suggested file and anchor.

### `explain`
Translates recent changes into plain language.

### `guard`
Combines structure risk and recent change risk, then tells you whether it is safe to continue.

---

## 3. Command reference

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

> “Is it safe to continue with another AI edit right now?”

Output includes:

- overall level
- whether the session should be considered blocked
- recommendations
- doctor findings
- recent changed files

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
vibeguard export antigravity
```

This creates:

```text
vibeguard_exports/<tool>/
```

Examples:

- Claude → rules, setup notes, prompt template
- OpenCode → workflow notes and prompt template
- Antigravity → task artifact and verification checklist

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

- keep entry files tiny
- split large files before AI keeps growing them
- add anchors before repeated edits
- prefer patch requests over vague instructions
- use Git when possible
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

---

## 7. Final advice

The safest pattern is:

> structure first, AI second

That is exactly what VibeGuard is for.



##실제 추천 초기 세팅

그래서 저는 보통 이렇게 합니다.

vibeguard doctor
vibeguard anchor
vibeguard export opencode
vibeguard guard

이러면 프로젝트가 AI 개발 준비 상태가 됩니다.

새 프로젝트에서는 이 순서가 가장 좋습니다.

vibeguard doctor
vibeguard anchor
vibeguard export opencode

##진행 중 프로젝트 도입 흐름

정리하면 이렇게 합니다.

vibeguard doctor
vibeguard anchor --dry-run
vibeguard anchor
vibeguard export opencode
vibeguard guard