# VibeLign — CLI Command Model

CLI executable:

vib

Canonical rule:

- `vib` is the only public CLI name in the final PRD.
- Preview is exposed in MVP through `vib patch --preview`.
- `AI edit` is a workflow step, not a CLI command.

Core workflow:

vib init
vib doctor
vib checkpoint
vib anchor
vib patch
AI edit
vib explain
vib guard
vib history / vib undo if needed

MVP command set:

- vib init
- vib doctor
- vib anchor
- vib patch
- vib explain
- vib guard
- vib checkpoint
- vib undo
- vib history

Safety tools:

vib checkpoint
vib undo
vib history

Monitoring:

vib protect
vib guard
vib watch

Utilities:

vib ask
vib config
vib export

Post-MVP:

- dedicated preview command
- GUI-specific commands
