# VibeLign Planning Checklist

This file is the execution and verification tracker for the PRD set under `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/`. The source PRD documents are mostly narrative specs and final-draft design notes, so they do not provide built-in Markdown checkboxes for tracking progress.

Use this checklist to mark planning decisions as confirmed, implementation-readiness conditions as verified, and MVP scope boundaries as enforced. When a checklist item is marked complete, the source PRD should already support that decision or requirement.

Audit note: checked items below were verified against the current repository code and command behavior. Unchecked items are either missing, partially implemented, or currently mismatched with the PRD.

## 00_core_prd

### 01_VibeLign_Ultimate_Vision
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/01_VibeLign_Ultimate_Vision.md`

- [x] Confirm the product remains centered on the loop `Align -> Understand -> Modify -> Verify`.
- [x] Confirm the product principles remain explicit in execution work: safe over clever, small patches over rewrites, understandable over magical, intent-driven coding.
- [x] Confirm planning and implementation flows always show the interpretation before the edit.
- [x] Confirm the system always makes the next step obvious for the user.
- [x] Confirm novice experimentation remains a first-class design goal.

### 02_VibeLign_Product_Positioning
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/02_VibeLign_Product_Positioning.md`

- [x] Confirm VibeLign is positioned as a safety layer for AI coding rather than a generic code assistant.
- [x] Confirm the product scope still includes project analysis, safe edit-zone restriction, controlled patch generation, and preview-before-apply behavior.
- [x] Confirm beginner-facing output still includes rough-request understanding, visible CodeSpeak, middle-school-level explanation, and one safe next action.
- [x] Confirm checkpoint, history, and undo remain part of the beginner-facing recovery story.

### 03_VibeLign_System_Architecture
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/03_VibeLign_System_Architecture.md`

- [x] Confirm MVP architecture includes CLI Layer, Analysis Layer, Engine Layer, Patch Layer, and Preview Layer.
- [x] Confirm Simulation Layer remains post-MVP support.
- [x] Confirm GUI Layer remains future scope.
- [x] Confirm MVP playground outputs include interpreted user intent, visible CodeSpeak translation, next-step guidance, and human explanation.
- [x] Confirm the workflow order still flows from user intent to intent understanding, project analysis, anchor detection, patch builder, preview engine, and apply patch.

### 04_VibeLign_Repo_Structure
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/04_VibeLign_Repo_Structure.md`

- [x] Confirm the planned repository structure still reserves distinct areas for `cli/`, `analysis/`, `engine/`, `patch/`, `preview/`, `simulator/`, `ui/`, `recipes/`, `examples/`, and `docs/`.
- [x] Confirm CLI contains commands only.
- [x] Confirm reusable logic is planned to live outside the CLI layer so CLI and GUI can share the same engine.

### 05_VibeLign_Playground_Experience
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/05_VibeLign_Playground_Experience.md`

- [x] Confirm rough requests are treated as normal input rather than user error.
- [x] Confirm low-confidence interpretation triggers clarification instead of blind editing.
- [x] Confirm beginner-facing explanations default to middle-school-level wording.
- [x] Confirm preview appears before risky action.
- [x] Confirm recovery stays simple through checkpoint, history, and undo.
- [x] Confirm visible output includes `Interpretation:`, `CodeSpeak:`, `Confidence:`, and `Next step:`.
- [x] Confirm ambiguous requests produce clarifying questions when confidence is below threshold.

## 01_cli_design

### 05_VibeLign_CLI_Strategy
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/05_VibeLign_CLI_Strategy.md`

- [x] Confirm the development model remains `CLI First -> Engine Stable -> GUI Later`.
- [x] Confirm the public command name strategy still targets `vib`.
- [x] Confirm CLI-first rationale still prioritizes easier debugging, easier automated tests, easier packaging, and engine stabilization before UI.

### 06_VibeLign_CLI_Command_Model
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/06_VibeLign_CLI_Command_Model.md`

- [x] Confirm `vib` remains the only public CLI name in the final PRD.
- [x] Confirm preview is exposed in MVP only through `vib patch --preview`.
- [x] Confirm `AI edit` remains a workflow step and not a CLI command.
- [x] Confirm the MVP command set remains limited to `vib init`, `vib doctor`, `vib anchor`, `vib patch`, `vib explain`, `vib guard`, `vib checkpoint`, `vib undo`, and `vib history`.
- [x] Confirm `protect`, `guard`, and `watch` remain grouped as monitoring-oriented tools.
- [x] Confirm `ask`, `config`, and `export` remain utilities outside the MVP command set.
- [x] Confirm dedicated preview commands and GUI-specific commands remain post-MVP.

### 07_VibeLign_CLI_Command_Spec
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/07_VibeLign_CLI_Command_Spec.md`

- [x] Confirm the authoritative MVP command table matches the command model and MVP plan.
- [x] Confirm shared command rules for `--json`, `--strict`, and `--write-report` are documented consistently.
- [x] Confirm `vib init` remains safe for existing projects and does not modify source code in normal MVP behavior.
- [x] Confirm `.vibelign/config.yaml`, `.vibelign/project_map.json`, `.vibelign/state.json`, and `.vibelign/checkpoints/` remain the MVP metadata contract.
- [x] Confirm `state.json` ownership rules stay explicit: `vib init` creates it, `vib doctor` updates `last_scan_at`, `vib anchor` updates `last_anchor_run_at`, `vib guard` updates `last_guard_run_at`, and `vib patch` plus `vib explain` do not mutate it in MVP.
- [x] Confirm `vib doctor` responsibilities still include oversized-file detection, mixed-responsibility detection, anchor coverage checks, entry-file risk checks, and project health scoring.
- [x] Confirm `vib anchor` default behavior and preview-related guidance remain aligned with the rest of the CLI docs.
- [x] Confirm `vib patch --preview` remains the canonical MVP preview flow and no standalone `vib preview` command is introduced.
- [x] Confirm beginner-facing patch output still includes interpretation, CodeSpeak, confidence, and one recommended next step.
- [x] Confirm `vib explain` output rules still target middle-school-level wording, short sentences, minimal jargon, and the structure `What changed`, `Why it matters`, `What to do next`.
- [x] Confirm `vib guard` still checks structural damage, unsafe AI modifications, and overall project stability.
- [x] Confirm metadata and report artifact rules remain explicit for MVP.
- [x] Confirm the recommended user workflow order remains `doctor -> checkpoint -> anchor -> patch --preview -> AI edit -> explain -> guard -> history/undo`.
- [x] Confirm pass, warn, fail status semantics and exit-code rules remain defined.
- [x] Confirm integration targets still mention Claude Code, OpenCode, Cursor, and Antigravity.

### VibeLign_vib_doctor_Final_Design_Spec
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/VibeLign_vib_doctor_Final_Design_Spec.md`

- [x] Confirm `vib doctor` continues to explain what is wrong, what is risky for AI editing, and what to do next.
- [x] Confirm file-size thresholds remain documented as 300+ warning, 500+ strong warning, and 800+ critical.
- [x] Confirm mixed-responsibility checks still include UI plus business logic, API plus DB logic, and command layer plus core engine logic.
- [x] Confirm anchor coverage checks still report anchor presence, missing important anchors, and estimated protection coverage.
- [x] Confirm entry-file risk checks still treat `main.py`, `app.py`, and `cli.py` as special cases.
- [x] Confirm dependency-risk checks still include circular imports, suspicious internal chains, and missing internal targets.
- [x] Confirm the AI risk-score ranges remain explicit.
- [x] Confirm default, detailed, JSON, and fix-suggestion output modes remain part of the design.

## 02_engine_design

### 09_VibeLign_Project_Understanding_Engine
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/09_VibeLign_Project_Understanding_Engine.md`

- [x] Confirm the engine goal remains automatic project-structure understanding.
- [x] Confirm core capabilities remain file scanning, import detection, dependency-graph building, and module classification.
- [x] Confirm the output is still defined as an internal project graph.

### 09a_VibeLign_Project_Map
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/09a_VibeLign_Project_Map.md`

- [x] Confirm `.vibelign/project_map.json` remains the shared structural metadata layer for the product.
- [x] Confirm the map still captures project structure, module roles, risky files, entry points, and edit-safe areas.
- [x] Confirm `vib init` remains the primary writer of the Project Map in MVP.
- [x] Confirm `vib doctor`, `vib anchor`, `vib patch`, `vib explain`, and `vib guard` remain readers in MVP.
- [x] Confirm required fields still include `schema_version`, `project_name`, `entry_files`, `ui_modules`, `core_modules`, `service_modules`, `large_files`, `file_count`, and `generated_at`.
- [x] Confirm unsupported schema versions must fail clearly.
- [x] Confirm Project Map usage remains aligned across doctor, anchor, patch, explain, and guard.
- [x] Confirm regeneration still happens through rerunning `vib init` in MVP.
- [x] Confirm the Project Map remains observational metadata and never modifies source code.

### 10_VibeLign_CodeSpeak_Grammar
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/10_VibeLign_CodeSpeak_Grammar.md`

- [x] Confirm the canonical MVP grammar remains `layer.target.subject.action`.
- [x] Confirm CodeSpeak rules remain lower_snake_case tokens, dot-separated hierarchy, action-last ordering, and one intent per expression in MVP.
- [x] Confirm Patch System examples continue to use the canonical grammar.
- [x] Confirm aliases remain post-MVP.

### 11_VibeLign_Anchor_System
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/11_VibeLign_Anchor_System.md`

- [x] Confirm `vib anchor` remains one of the core commands used to create and validate safe edit zones.
- [x] Confirm Suggest Mode, Auto Mode, and Validate Mode remain part of MVP behavior.
- [x] Confirm List Mode and Coverage Mode remain post-MVP.
- [x] Confirm anchor recommendations continue to use project map, file size, module role, code structure, and doctor findings.
- [x] Confirm recommendation rules still prioritize large, likely AI-edited, UI-heavy, entry-adjacent, and high-value feature files.
- [x] Confirm anchors are recommended around natural code boundaries rather than unrelated code spans.
- [x] Confirm full-file anchors remain a fallback rather than the default.
- [x] Confirm anchor readability rules still target reasonable density and 1 to 5 anchors per file in MVP.
- [x] Confirm anchor naming rules remain snake_case, max 64 chars, file-local uniqueness, and stable regeneration where possible.

### 12_VibeLign_Patch_System
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/12_VibeLign_Patch_System.md`

- [x] Confirm Patch System remains the core engine that turns natural-language requests into safe patch prompts.
- [x] Confirm the patch flow remains user intent -> CodeSpeak translation -> anchor selection -> patch prompt generation -> preview simulation -> AI edit execution.
- [x] Confirm the system still addresses whole-file rewrites, wrong-location edits, structural damage, and context hallucination.
- [x] Confirm patch philosophy still enforces small edits, anchor-based editing, prompt safety, and predictable change.
- [x] Confirm the Patch Engine still includes Intent Parser, CodeSpeak Translator, Anchor Selector, Patch Builder, and Safety Guard.
- [x] Confirm `vib patch <user request>` remains the canonical command entry point.
- [x] Confirm MVP preview exposure remains `vib patch --preview` and not a separate preview command.
- [x] Confirm low-confidence requests trigger clarifying questions instead of fake certainty.
- [x] Confirm CodeSpeak remains visible in beginner-facing patch flows.
- [x] Confirm patch target output still includes target file, target anchor, confidence score, and reason.
- [x] Confirm patch prompts still include context, task, constraints, and expected result.
- [x] Confirm constraints still enforce patch-only behavior, structure preservation, and avoidance of unrelated edits.

### 13_VibeLign_Preview_Engine
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/13_VibeLign_Preview_Engine.md`

- [x] Confirm ASCII preview remains the only MVP preview format.
- [x] Confirm HTML preview remains post-MVP and screenshot preview remains future scope.
- [x] Confirm preview purpose remains showing expected changes before patch application.
- [x] Confirm canonical preview exposure remains `vib patch --preview`.
- [x] Confirm preview input still includes user request, selected target file, selected anchor, and generated patch constraints.
- [x] Confirm preview output still includes target summary, before/after description, confidence score, and JSON payload support.
- [x] Confirm JSON rules remain: `vib patch --json` returns `data.patch_plan`, while `vib patch --preview --json` returns both `data.patch_plan` and `data.preview`.

### 14_VibeLign_Simulation_Engine
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/14_VibeLign_Simulation_Engine.md`

- [x] Confirm Simulation Engine remains post-MVP.
- [x] Confirm MVP verification continues to rely on `vib guard` plus direct structural checks instead of simulation.
- [x] Confirm post-MVP simulation steps remain clone project, apply patch, run checks, and produce a risk report.
- [x] Confirm post-MVP checks may include lint, tests, build, and structural regression checks.

### 17_VibeLign_Engine_API_Spec
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/17_VibeLign_Engine_API_Spec.md`

- [x] Confirm all structured responses still use the shared envelope with `ok`, `error`, and `data`.
- [x] Confirm structured error responses still include `code`, `message`, and `hint`.
- [x] Confirm the core APIs remain `analyze_project`, `detect_anchors`, `build_patch`, `generate_preview`, and `run_guard`.
- [x] Confirm `build_patch` still returns interpretation, target file, target anchor, confidence, CodeSpeak, and constraints.
- [x] Confirm `patch_plan` required fields remain explicit.
- [x] Confirm `patch_plan` optional fields remain explicit.
- [x] Confirm preview payload required fields remain explicit.
- [x] Confirm `run_guard` JSON output still exposes status, strict flag, checks, blocking failures, and warnings.
- [x] Confirm CLI `--json` output remains aligned to these Engine API contracts.
- [x] Confirm unsupported schema and missing metadata still require structured error envelopes.
- [x] Confirm low-confidence patch requests may return clarifying questions instead of a fully actionable target.

## 03_development

### 08_VibeLign_MVP_Development_Plan
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/08_VibeLign_MVP_Development_Plan.md`

- [x] Confirm the MVP command set remains `vib init`, `vib start`, `vib doctor`, `vib anchor`, `vib patch`, `vib explain`, `vib guard`, `vib checkpoint`, `vib undo`, and `vib history`.
- [x] Confirm out-of-MVP scope still excludes a dedicated `vib preview` command, HTML preview, Simulation Engine execution, GUI integration, IDE integrations, and `protect`/`ask`/`config`/`export`/`watch`.
- [x] Confirm acceptance criteria still require consistent command-surface documentation across CLI docs. <!-- DONE: README, MANUAL, QUICKSTART 모두 vib CLI 이름으로 정합 완료 -->
- [x] Confirm acceptance criteria still require explicit schema ownership for `.vibelign` metadata files.
- [x] Confirm acceptance criteria still require preview exposure only through `vib patch --preview`.
- [x] Confirm acceptance criteria still require `vib guard` as the post-edit verification step.
- [x] Confirm acceptance criteria still require checkpoint, undo, and history as the rollback safety net.
- [x] Confirm acceptance criteria still require explicit and observable MVP release criteria.
- [x] Confirm acceptance criteria still require rough requests to be interpreted before action.
- [x] Confirm acceptance criteria still require CodeSpeak to be visible in beginner-facing patch flows.
- [x] Confirm acceptance criteria still require explanation output readable at a middle-school level.
- [x] Confirm acceptance criteria still require the workflow to suggest one safe next step.
- [x] Confirm Week 1 scope remains doctor plus init metadata contract.
- [x] Confirm Week 2 scope remains anchor plus anchor index contract.
- [x] Confirm Week 3 scope remains patch plus CodeSpeak alignment.
- [x] Confirm Week 4 scope remains ASCII preview through `vib patch --preview`.
- [x] Confirm Week 5 scope remains guard verification plus rollback workflow alignment.
- [x] Confirm Week 6 scope remains stability and edge-case review.
- [x] Confirm Week 7 scope remains documentation cleanup.
- [x] Confirm Week 8 scope remains release readiness review.

### 15_VibeLign_Config_System
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/15_VibeLign_Config_System.md`

- [x] Confirm `.vibelign/config.yaml` remains the MVP configuration file.
- [x] Confirm config schema fields remain `schema_version`, `llm_provider`, `api_key`, and `preview_format`.
- [x] Confirm `preview_format` remains `ascii` only in MVP.
- [x] Confirm `vib init` remains the creator of the config file when it is missing.
- [x] Confirm `vib config` remains the post-MVP interactive writer.
- [x] Confirm other commands may read config but must not silently rewrite it.

### 16_VibeLign_Development_Workflow
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/16_VibeLign_Development_Workflow.md`

- [x] Confirm the typical workflow remains `vib init -> vib doctor -> vib checkpoint -> vib anchor -> vib patch --preview -> AI edit -> vib explain -> vib guard -> vib history / vib undo if needed`.
- [x] Confirm the beginner playground workflow still starts from a rough request and reviews interpretation plus CodeSpeak before editing.
- [x] Confirm the workflow still requires checkpoint creation before edits.
- [x] Confirm preview remains optional but canonical when needed.
- [x] Confirm AI editing is deferred until the target looks correct.
- [x] Confirm explain and guard remain the required post-edit steps.
- [x] Confirm history and undo remain the recovery path when the result feels wrong.
- [x] Confirm the MVP release-ready checklist still requires anchor-bound patch targets, reviewed preview output when needed, scope-limited AI edits, understandable explanations, successful guard completion, one safe next step after each major phase, and rollback availability.

### 18_VibeLign_Roadmap
Source: `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/18_VibeLign_Roadmap.md`

- [x] Confirm Stage 1 remains CLI tool delivery.
- [x] Confirm Stage 2 remains Desktop GUI.
- [x] Confirm Stage 3 remains IDE integrations.

## Cross-Document Alignment

### MVP boundary alignment
Sources:
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/03_VibeLign_System_Architecture.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/06_VibeLign_CLI_Command_Model.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/07_VibeLign_CLI_Command_Spec.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/08_VibeLign_MVP_Development_Plan.md`

- [x] Confirm all documents agree that MVP is CLI-first.
- [x] Confirm all documents agree there is no standalone `vib preview` command in MVP.
- [x] Confirm all documents agree ASCII preview is in MVP and HTML preview is post-MVP.
- [x] Confirm all documents agree Simulation Engine is post-MVP.
- [x] Confirm all documents agree `protect`, `ask`, `config`, `export`, and `watch` are outside the MVP command set unless later promoted.

### Beginner-safety alignment
Sources:
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/00_core_prd/05_VibeLign_Playground_Experience.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/12_VibeLign_Patch_System.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/16_VibeLign_Development_Workflow.md`

- [x] Confirm rough natural-language requests remain supported end to end.
- [x] Confirm low-confidence flows prefer clarification over unsafe action.
- [x] Confirm preview-first and guard-after-edit remain the standard safety pattern.
- [x] Confirm checkpoint/history/undo remain the recovery contract across documents.

### Metadata and contract alignment
Sources:
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/01_cli_design/07_VibeLign_CLI_Command_Spec.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/09a_VibeLign_Project_Map.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/02_engine_design/17_VibeLign_Engine_API_Spec.md`
- `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/15_VibeLign_Config_System.md`

- [x] Confirm `.vibelign` metadata ownership is explicit and non-overlapping.
- [x] Confirm schema-version handling is documented for Project Map, config, and structured API payloads.
- [x] Confirm JSON output contracts and metadata contracts do not conflict across docs.
- [x] Confirm MVP readers and writers for each metadata file are fully specified.

## Open Decisions

Source: `PROJECT_DOC_STATUS.md`

- [x] Decide the final public CLI name. → `vib`
- [x] Decide the final package name. → `vibelign`
- [x] Decide the final repository rename timing. → MVP 출시 후
- [x] Decide the backward-compatibility policy for `vibelign` naming. → vibelign CLI 래퍼 유지

## Documentation Cleanup Queue

Source: `PROJECT_DOC_STATUS.md`

- [x] Align `README.md` with the final PRD direction.
- [x] Align `docs/MANUAL.md` with the final PRD direction.
- [x] Align `VibeLign_QUICKSTART.md` with the final PRD direction.
