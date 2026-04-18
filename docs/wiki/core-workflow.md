# Core Workflow

## Default Safe Workflow

```bash
vib checkpoint "before work"
vib doctor --strict
vib anchor
vib patch "your request"
# apply the AI edit
vib explain --write-report
vib guard --strict --write-report
vib checkpoint "done"
```

## Why This Flow Exists

- `checkpoint` gives you a rollback point
- `doctor` catches obvious project issues early
- `anchor` makes edit locations more precise
- `patch` narrows the request into safer structure
- `explain` helps review what actually changed
- `guard` checks that the project still looks healthy

## When To Use Undo

Use undo when AI changed the wrong files, broke the project, or took the work in the wrong direction.
The intended workflow is to save first, experiment second.

## Related Canonical Docs

- Recommended workflow: [`../../README.md`](../../README.md)
- Full command manual: [`../../VIBELIGN_MANUAL.md`](../../VIBELIGN_MANUAL.md)
- Docs manual: [`../MANUAL.md`](../MANUAL.md)
