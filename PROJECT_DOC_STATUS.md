# Project Document Status

This file is the single source of truth for documentation status during the
transition from VibeLign to VibeLign.

If documents conflict, follow this file first.

## Current Official Direction

- Product direction name: `VibeLign`
- Current implementation name: `VibeLign`
- Current repository name: `VibeLign`
- Transition state: in migration

## Source of Truth Rules

Use documents in this order:

1. `PROJECT_DOC_STATUS.md`
2. `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/`
3. Current implementation-facing docs in the repository root and `docs/`

If a planning document conflicts with current code behavior:

- use `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/` for future design
- use current implementation docs for current shipped behavior
- do not use any other planning folder for active planning decisions

## Naming Policy During Migration

- Use `VibeLign` when writing future-facing product planning.
- Use `VibeLign` when describing the current shipped implementation,
  repository, Python package, or existing CLI behavior.
- Do not mass-rename old documents unless they are being actively promoted to
  the new source of truth.
- New planning documents should be added only under
  `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/`.
- Do not add new planning content to any other folder under
  `VibeLign_dev_plan/`.

## Document Status Table

| Path | Purpose | Status | Authority | Notes |
| --- | --- | --- | --- | --- |
| `PROJECT_DOC_STATUS.md` | Documentation entry point | active | highest | Start here first |
| `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/` | Final product planning for VibeLign | active | planning source of truth | Use for future design decisions |
| `README.md` | Current project overview | active | implementation reference | Aligned with `vib` CLI name and PRD direction |
| `docs/MANUAL.md` | Current user manual | active | implementation reference | Aligned with `vib` CLI name and PRD direction |
| `VibeLign_QUICKSTART.md` | Current onboarding guide | active | implementation reference | Aligned with `vib` CLI name and PRD direction |
| `VIBELIGN_PATCH_REQUEST.md` | Generated working artifact | reference | none | Not a planning source |
| `VIBELIGN_EXPLAIN.md` | Generated working artifact | reference | none | Not a planning source |
| `VIBELIGN_GUARD.md` | Generated working artifact | reference | none | Not a planning source |
| `VibeLign_dev_plan/vibelign_1차기획/` | Early VibeLign planning set | reference | none | Do not use for active planning |
| `VibeLign_dev_plan/vibelign_updated_docs_v2/` | Intermediate VibeLign planning set | reference | none | Do not use for active planning |
| `VibeLign_dev_plan/vibelign_updated_2차수정안/` | Intermediate revision set | reference | none | Do not use for active planning |
| `VibeLign_dev_plan/VibeLign Final PRD v1/` | Older final-draft set | reference | none | Do not use for active planning |

Status meanings:

- `active`: current official document set
- `migration-needed`: still useful, but needs alignment with final direction
- `reference`: keep for context, not as the default decision source

## Working Rule For New Decisions

When making a new product or architecture decision:

1. Check `PROJECT_DOC_STATUS.md`.
2. Check `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/`.
3. If current implementation differs, document the gap as migration work.
4. Do not consult other planning folders unless you are doing historical
   comparison only.

### Planning rule for the current `vib start` category docs

- Treat `VibeLign_dev_plan/vibelign_generated_file_manifest.md` as the source of truth for the generated-output contract.
- Treat `VibeLign_dev_plan/vibelign_nextjs_typescript_app_v1_asset_manifest.md` as the source of truth for the concrete `web_app_safe_default_v1` scaffold file set.
- If another planning doc conflicts with either one, align that doc first before making implementation or planning decisions.

## Immediate Cleanup Order

Update these first when documentation alignment work begins:

1. `README.md`
2. `docs/MANUAL.md`
3. `VibeLign_QUICKSTART.md`

Do not move planning work into older planning folders.

## Naming Decisions (Resolved)

- Final public CLI name: **`vib`**
- Final package name: **`vibelign`** (pip install vibelign)
- Repository rename timing: **MVP 출시 후**
- Backward compatibility: **`vibelign` CLI 래퍼 유지** (vibelign 명령이 vib으로 위임)
