# AGENTS.md

This file is automatically read by OpenCode, Claude Code, and other AI coding tools that support AGENTS.md.

**Before making any changes to this project, read and follow `AI_DEV_SYSTEM_SINGLE_FILE.md`.**

## Core Rules

- Apply the smallest safe patch possible
- Do not rewrite entire files unless explicitly requested
- Edit only the file that is actually relevant
- Do not modify unrelated modules
- Respect anchor boundaries (`ANCHOR: NAME_START` / `ANCHOR: NAME_END`)
- Keep entry files (main.py, index.js, etc.) small and focused

## Two Modification Modes

### Mode 1 — Normal AI edit (default)

When the user makes a regular request, apply the smallest safe patch using your own judgment.

```
User: "Change the login button color to blue"
→ Modify directly. Follow Core Rules above.
```

### Mode 2 — VibeLign safe mode (triggered by keyword)

When the user includes **"바이브라인으로"** (or "with vibelign" / "vibelign mode") in their request,
activate the full VibeLign MCP workflow:

1. Call `patch_get` with the user's request — this translates it to CodeSpeak and pinpoints the exact `target_file` and `target_anchor`.
2. Modify **only** within the returned `target_anchor` boundary in `target_file`.
3. Call `guard_check` to validate.
4. Call `checkpoint_create` to save the state.

```
User: "바이브라인으로 로그인 버튼 색 파란색으로 바꿔줘"
→ patch_get("로그인 버튼 색 파란색으로 바꿔줘")
→ Modify only target_file at target_anchor
→ guard_check → checkpoint_create
```

**When to recommend Mode 2 to the user:**
- Request touches multiple files or the target location is ambiguous
- Logic or structural change (not just a text/style tweak)
- User is unsure which file to modify

### Without MCP (CLI fallback)

```bash
vib doctor --strict
vib anchor
vib patch "<your request>"
# apply the AI edit
vib explain --write-report
vib guard --strict --write-report
```

## Project Map

Before modifying any file, read `.vibelign/project_map.json` to understand:
- File categories (entry, ui, service, core)
- Anchor locations per file (`anchor_index`)
- File dependencies via `.vibelign/anchor_meta.json` (`@CONNECTS`)

## Full Rules

See `AI_DEV_SYSTEM_SINGLE_FILE.md` for the complete ruleset.
