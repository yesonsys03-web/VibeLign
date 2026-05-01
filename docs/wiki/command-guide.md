# Command Guide

This page lists the commands most likely to answer quick project questions.
For full details, use the linked canonical docs.

| Command | Use it when | Source |
|---|---|---|
| `vib start` | preparing a project for AI tooling | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib checkpoint` | saving state before risky edits | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib undo` | restoring a previous checkpoint | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib history` | reviewing saved checkpoints | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib backup-db-viewer --json` | inspecting the Rust backup DB in read-only mode | [`../../README.md`](../../README.md) |
| `vib backup-db-maintenance --json` | planning safe backup DB file cleanup without changing it | [`../../README.md`](../../README.md) |
| `vib backup-db-maintenance --apply --json` | backing up DB files, truncating WAL, and conditionally compacting SQLite | [`../../README.md`](../../README.md) |
| `vib doctor` | checking project health | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib anchor` | adding or refreshing AI-safe edit markers | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib patch` | converting natural requests into safer edit instructions | [`../../README.md`](../../README.md) |
| `vib explain` | understanding what changed | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib guard` | checking whether AI broke the project | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib protect` | blocking edits to important files | [`../../README.md`](../../README.md) |
| `vib secrets --staged` | blocking accidental secret commits | [`../../README.md`](../../README.md) |
| `vib transfer` | generating project handoff context | [`../../README.md`](../../README.md) |
| `vib export` | generating AI-tool-specific config files | [`../../README.md`](../../README.md) |

## Transfer / handoff quick reference

Use `vib transfer` when switching AI tools, opening a fresh chat, or preserving context before a token limit.

```bash
vib transfer
vib transfer --compact
vib transfer --full
vib transfer --handoff
vib transfer --handoff --no-prompt --print
vib transfer --handoff --session-summary "current session work" --first-next-action "next action"
vib transfer --handoff --dry-run
vib transfer --out ctx.md
```

- `--handoff` adds a `Session Handoff` block at the top of `PROJECT_CONTEXT.md`.
- `--session-summary` and `--first-next-action` let you override the two most important handoff lines explicitly.
- `--no-prompt` skips questions and fills what it can from project/session signals.
- `--print` also prints the handoff summary to the console.
- `--dry-run` previews without writing.
- `--handoff` cannot be combined with `--compact` or `--full`.

## Rule Of Thumb

- Before edit: `checkpoint`, `doctor`
- During edit prep: `anchor`, `patch`
- After edit: `explain`, `guard`
- For recovery: `undo`, `history`
