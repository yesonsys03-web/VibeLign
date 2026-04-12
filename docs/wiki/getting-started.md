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
vib patch "add a small feature"
vib explain --write-report
vib guard --strict --write-report
```

## Beginner Mental Model

- `start` prepares the project for AI work
- `checkpoint` saves a restorable state
- `doctor` checks project health
- `patch` turns a natural request into a safer edit plan
- `explain` tells you what changed
- `guard` checks whether the change broke things

## When To Read More

- For step-by-step install help: [`../../VibeLign_QUICKSTART.md`](../../VibeLign_QUICKSTART.md)
- For the full manual: [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md)
- For the docs site manual: [`../MANUAL.md`](../MANUAL.md)
