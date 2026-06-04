# Getting Started

## Fastest Path

1. Install VibeLign
2. Move into your project folder
3. Run `vib start`
4. Create a checkpoint before asking AI to edit

## Typical First Session

```bash
vib start
vib checkpoint "before AI work"
vib doctor --strict
# Ask your host AI to make the edit after it reads AGENTS.md.
vib explain --write-report
vib guard --strict --write-report
```

## Beginner Mental Model

- `start` prepares the project for AI work
- `checkpoint` saves a restorable state
- `doctor` checks project health
- your host AI follows the project rules and anchors for the edit
- `explain` tells you what changed
- `guard` checks whether the change broke things

## When To Read More

- For step-by-step install help: [`../../VibeLign_QUICKSTART.md`](../../VibeLign_QUICKSTART.md)
- For the full manual: [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md)
- For the docs site manual: [`../MANUAL.md`](../MANUAL.md)
