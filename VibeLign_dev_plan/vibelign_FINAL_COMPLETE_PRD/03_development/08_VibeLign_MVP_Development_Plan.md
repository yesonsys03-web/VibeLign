# VibeLign — MVP Development Plan

MVP command set:

- vib init
- vib start
- vib doctor
- vib anchor
- vib patch
- vib explain
- vib guard
- vib checkpoint
- vib undo
- vib history

Out of core MVP acceptance boundary:

- dedicated `vib preview` command
- HTML preview
- Simulation Engine execution
- GUI integration
- IDE integrations
- `vib protect`, `vib ask`, `vib config`, `vib export`, `vib watch` as extended CLI commands

Acceptance criteria for MVP:

- command surface is documented consistently across CLI docs
- `.vibelign` metadata files have explicit schema ownership
- preview is exposed only through `vib patch --preview`
- `vib guard` is the required post-edit verification step
- checkpoint/undo/history are available as the beginner rollback safety net
- MVP release criteria are explicit and observable
- rough requests are interpreted before action
- CodeSpeak is visible in beginner-facing patch flows
- explanation output is readable at a middle-school level
- the workflow always suggests one safe next step

Week 1
doctor + init metadata contract

Week 2
anchor + anchor index contract

Week 3
patch + CodeSpeak alignment

Week 4
ASCII preview through `vib patch --preview`

Week 5
guard verification plus rollback workflow alignment

Week 6
stability and edge-case review

Week 7
documentation cleanup

Week 8
release readiness review
