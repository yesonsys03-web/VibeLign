# Project Document Status

This file is the single source of truth for documentation status during the
transition from VibeGuard to VibeLign.

If documents conflict, follow this file first.

## Current Official Direction

- Product direction name: `VibeLign`
- Current implementation name: `VibeGuard`
- Current repository name: `VibeGuard`
- Transition state: in migration

## Source of Truth Rules

Use documents in this order:

1. `PROJECT_DOC_STATUS.md`
2. `VibeGuard_dev_plan/vibelign_FINAL_COMPLETE_PRD/`
3. Current implementation-facing docs in the repository root and `docs/`

If a planning document conflicts with current code behavior:

- use `VibeGuard_dev_plan/vibelign_FINAL_COMPLETE_PRD/` for future design
- use current implementation docs for current shipped behavior
- do not use any other planning folder for active planning decisions

## Naming Policy During Migration

- Use `VibeLign` when writing future-facing product planning.
- Use `VibeGuard` when describing the current shipped implementation,
  repository, Python package, or existing CLI behavior.
- Do not mass-rename old documents unless they are being actively promoted to
  the new source of truth.
- New planning documents should be added only under
  `VibeGuard_dev_plan/vibelign_FINAL_COMPLETE_PRD/`.
- Do not add new planning content to any other folder under
  `VibeGuard_dev_plan/`.

## Document Status Table

| Path | Purpose | Status | Authority | Notes |
| --- | --- | --- | --- | --- |
| `PROJECT_DOC_STATUS.md` | Documentation entry point | active | highest | Start here first |
| `VibeGuard_dev_plan/vibelign_FINAL_COMPLETE_PRD/` | Final product planning for VibeLign | active | planning source of truth | Use for future design decisions |
| `README.md` | Current project overview | migration-needed | implementation reference | Still branded as VibeGuard |
| `docs/MANUAL.md` | Current user manual | migration-needed | implementation reference | Describes current CLI behavior |
| `VibeGuard_QUICKSTART.md` | Current onboarding guide | migration-needed | implementation reference | Keep aligned with shipped commands |
| `VIBEGUARD_PATCH_REQUEST.md` | Generated working artifact | reference | none | Not a planning source |
| `VIBEGUARD_EXPLAIN.md` | Generated working artifact | reference | none | Not a planning source |
| `VIBEGUARD_GUARD.md` | Generated working artifact | reference | none | Not a planning source |
| `VibeGuard_dev_plan/vibeguard_1차기획/` | Early VibeGuard planning set | reference | none | Do not use for active planning |
| `VibeGuard_dev_plan/vibelign_updated_docs_v2/` | Intermediate VibeLign planning set | reference | none | Do not use for active planning |
| `VibeGuard_dev_plan/vibelign_updated_2차수정안/` | Intermediate revision set | reference | none | Do not use for active planning |
| `VibeGuard_dev_plan/VibeLign Final PRD v1/` | Older final-draft set | reference | none | Do not use for active planning |

Status meanings:

- `active`: current official document set
- `migration-needed`: still useful, but needs alignment with final direction
- `reference`: keep for context, not as the default decision source

## Working Rule For New Decisions

When making a new product or architecture decision:

1. Check `PROJECT_DOC_STATUS.md`.
2. Check `VibeGuard_dev_plan/vibelign_FINAL_COMPLETE_PRD/`.
3. If current implementation differs, document the gap as migration work.
4. Do not consult other planning folders unless you are doing historical
   comparison only.

## Immediate Cleanup Order

Update these first when documentation alignment work begins:

1. `README.md`
2. `docs/MANUAL.md`
3. `VibeGuard_QUICKSTART.md`

Do not move planning work into older planning folders.

## Open Naming Decisions

These are still unresolved and should remain explicit until decided:

- final public CLI name
- final package name
- final repository rename timing
- backward compatibility policy for `vibeguard` naming
