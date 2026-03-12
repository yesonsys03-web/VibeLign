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

## Required Workflow

```bash
vibeguard doctor --strict
vibeguard anchor
vibeguard patch "<your request>"
# apply the AI edit
vibeguard explain --write-report
vibeguard guard --strict --write-report
```

## Full Rules

See `AI_DEV_SYSTEM_SINGLE_FILE.md` for the complete ruleset.
