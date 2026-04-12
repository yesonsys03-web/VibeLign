# Command Guide

This page lists the commands most likely to answer quick project questions.
For full details, use the linked canonical docs.

| Command | Use it when | Source |
|---|---|---|
| `vib start` | preparing a project for AI tooling | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib checkpoint` | saving state before risky edits | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib undo` | restoring a previous checkpoint | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib history` | reviewing saved checkpoints | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib doctor` | checking project health | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib anchor` | adding or refreshing AI-safe edit markers | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib patch` | converting natural requests into safer edit instructions | [`../../README.md`](../../README.md) |
| `vib explain` | understanding what changed | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib guard` | checking whether AI broke the project | [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md) |
| `vib protect` | blocking edits to important files | [`../../README.md`](../../README.md) |
| `vib secrets --staged` | blocking accidental secret commits | [`../../README.md`](../../README.md) |
| `vib transfer` | generating project handoff context | [`../../README.md`](../../README.md) |
| `vib export` | generating AI-tool-specific config files | [`../../README.md`](../../README.md) |

## Rule Of Thumb

- Before edit: `checkpoint`, `doctor`
- During edit prep: `anchor`, `patch`
- After edit: `explain`, `guard`
- For recovery: `undo`, `history`
