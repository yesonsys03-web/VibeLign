
# 07_VibeLign_CLI_Command_Spec.md
Version: Final Draft 1.0

This document defines the command-line interface specification for VibeLign.

CLI executable name:

vib

Philosophy:

The CLI should be simple, predictable, and safe for both developers and vibecoders.
Commands should guide the user step-by-step through a safe AI-assisted development workflow.
The beginner-facing experience should prefer interpretation, explanation, and next-step guidance over terse tool output.

Canonical command surface rule:

- `vib` is the only CLI executable name in the final PRD.
- `AI edit` is a user workflow step outside the CLI surface.
- MVP preview is exposed through `vib patch --preview`.
- There is no separate `vib preview` command in MVP.

Core workflow:

vib init → vib doctor → vib checkpoint → vib anchor → vib patch --preview (optional) → AI edit → vib explain → vib guard → vib history / vib undo if needed


--------------------------------------------------
MVP Command Surface
--------------------------------------------------

Authoritative MVP commands:

| Command | MVP | Primary purpose | Writes metadata | Writes source |
| --- | --- | --- | --- | --- |
| `vib init` | yes | attach VibeLign and create baseline metadata | yes | no |
| `vib doctor` | yes | analyze project structure | yes, state only | no |
| `vib anchor` | yes | suggest/insert/validate anchors | yes | yes, anchors only |
| `vib patch` | yes | generate safe patch request | no | no |
| `vib explain` | yes | explain recent code changes | no | no |
| `vib guard` | yes | verify safety after edits | yes, state only | no |
| `vib checkpoint` | yes | save project state before experimentation | yes | no |
| `vib undo` | yes | restore project state after a bad edit | yes | yes |
| `vib history` | yes | list available checkpoints | no | no |
| `vib protect` | no | mark protected files | yes | no |
| `vib ask` | no | generate explanation prompts | no | no |
| `vib config` | no | configure providers | yes | no |
| `vib export` | no | export tool helpers | no | no |
| `vib watch` | no | real-time monitoring | no | no |

Shared command rules:

- `--json` returns machine-readable output when a command supports structured reporting.
- `--strict` enables tighter validation and lower tolerance for risky structure.
- `--write-report` writes a persistent report artifact instead of console-only output.
- Commands not listed as MVP are post-MVP unless promoted in the MVP plan.


--------------------------------------------------
vib init
--------------------------------------------------

Initialize VibeLign inside an existing project.

IMPORTANT:

`vib init` must NEVER modify existing source code unless explicitly requested.

Its role is to attach VibeLign to the project and generate internal metadata.


What vib init does

When executed, vib init performs the following steps:

1. Scan the project structure
2. Generate the internal Project Map
3. Create the `.vibelign` metadata folder
4. Optionally create the first checkpoint
5. Provide guidance for next commands


Project Scan

The command analyzes the project to identify:

- entry files (main.py, app.py, cli.py)
- UI related modules
- core modules
- large files
- file counts

This scan is read-only and does not modify the project.


Metadata Folder

`vib init` creates an internal metadata directory:

.vibelign/
    config.yaml
    project_map.json
    state.json
    checkpoints/


Project Map Generation

The command generates a project structure map:

.vibelign/project_map.json


Example structure:

{
  "entry_files": ["main.py"],
  "ui_modules": ["ui/window.py"],
  "core_modules": ["engine/patch.py"],
  "large_files": ["main.py"],
  "file_count": 38
}


This map helps AI tools understand project architecture.


Safety Guarantee

`vib init` will NOT:

- modify existing Python files
- insert anchors automatically
- refactor code
- change imports

This ensures that running init on existing projects is safe.


Metadata contract created by `vib init`

`vib init` creates these files under `.vibelign/`:

| File | Required in MVP | Purpose |
| --- | --- | --- |
| `config.yaml` | yes | user-selected provider and output defaults |
| `project_map.json` | yes | structural project metadata |
| `state.json` | yes | tool state and last refresh timestamps |
| `checkpoints/` | yes | restore data for beginner-safe experimentation |

`state.json` MVP example:

```json
{
  "schema_version": 1,
  "project_initialized": true,
  "project_map_version": 1,
  "last_scan_at": "2026-01-01T12:00:00Z",
  "last_anchor_run_at": null,
  "last_guard_run_at": null
}
```

State update rules in MVP:

- `vib init` creates `state.json`.
- `vib doctor` updates `last_scan_at`.
- `vib anchor` updates `last_anchor_run_at`.
- `vib guard` updates `last_guard_run_at`.
- `vib patch` and `vib explain` do not mutate `state.json` in MVP.


Optional First Checkpoint

`vib init` may create an initial checkpoint:

before_vibelign_init


Example Output

$ vib init

Scanning project...

Files detected: 42
Entry files: main.py
Large files: 2

Project map created:
.vibelign/project_map.json

Metadata directory created:
.vibelign/

No source files were modified.

Next steps:
vib doctor
vib anchor --suggest
vib patch "your request"



--------------------------------------------------
vib doctor
--------------------------------------------------

Analyze the project structure and report potential risks for AI editing.

Responsibilities:

- detect oversized files
- detect mixed responsibilities
- check anchor coverage
- evaluate entry file risks
- produce a project health score

Output modes:

vib doctor
vib doctor --detailed
vib doctor --json
vib doctor --fix-hints
vib doctor --strict


Doctor Output Example

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VibeLign Project Health Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project score: 72 / 100
Status: Caution

Main findings:
1. main.py is too large (612 lines)
2. ui.py mixes UI and business logic
3. 3 important files are missing anchors

Recommended next steps:
vib anchor --auto
split main.py



--------------------------------------------------
vib anchor
--------------------------------------------------

Insert safe editing anchors into source files.

Anchors define boundaries where AI modifications are allowed.

Example:

# ANCHOR START ui_layout
...
# ANCHOR END ui_layout

Options:

vib anchor
vib anchor --auto
vib anchor --suggest
vib anchor --dry-run
vib anchor --validate

Default behavior in MVP:

- `vib anchor` behaves as `vib anchor --suggest`
- `vib anchor --dry-run` is an alias of `vib anchor --suggest`



--------------------------------------------------
vib patch
--------------------------------------------------

Generate a safe patch request for AI coding tools.

Instead of allowing AI to rewrite entire files, VibeLign generates structured patch prompts.

Example:

vib patch "add progress bar"

Options:

vib patch "feature request"
vib patch --target FILE
vib patch --preview
vib patch --json

Preview rule:

- `vib patch --preview` is the canonical MVP preview flow.
- The preview shows the expected patch target, constraints, and projected output.
- ASCII preview is MVP. HTML preview is post-MVP.

Beginner-facing output rule for `vib patch`:

- show `Interpretation:` before patch details
- show `CodeSpeak:` using the canonical grammar
- show `Confidence:` for the request translation
- show `Next step:` with one recommended safe action
- ask clarifying questions instead of pretending certainty when confidence is low



--------------------------------------------------
vib explain
--------------------------------------------------

Explain recent code changes in simple human language.

Goal:

Allow vibecoders and non-developers to understand what the AI changed.

Default explanation style:

- middle-school-level wording
- short sentences
- minimal jargon
- structure: `What changed`, `Why it matters`, `What to do next`

Examples:

vib explain
vib explain --last
vib explain --file login.py



--------------------------------------------------
vib guard
--------------------------------------------------

Safety verification after AI edits.

Combines structural analysis and change explanation.

Responsibilities:

- detect structural damage
- detect unsafe AI modifications
- confirm project stability

Examples:

vib guard
vib guard --strict
vib guard --write-report


--------------------------------------------------
Metadata Ownership
--------------------------------------------------

Metadata ownership in MVP:

- `vib init` creates `.vibelign/config.yaml`, `.vibelign/project_map.json`, and `.vibelign/state.json`.
- `vib anchor` may create `.vibelign/anchor_index.json`.
- `vib checkpoint` writes checkpoint data under `.vibelign/checkpoints/`.
- `vib undo` restores from existing checkpoint data.
- `vib doctor` and `vib guard` may update `state.json` timestamps but do not change source code.
- `vib patch` and `vib explain` are read-only with respect to metadata in MVP.
- Source modification in MVP is limited to anchor insertion by `vib anchor` and user-approved AI edits outside the CLI.


--------------------------------------------------
Report Artifact Contract
--------------------------------------------------

Commands that support `--write-report` write into:

`.vibelign/reports/`

Naming rules:

- text report: `<command>_latest.md`
- json report: `<command>_latest.json`

MVP commands using this contract:

- `vib guard --write-report`
- `vib explain --write-report` when supported in MVP-aligned workflows

If `--json` and `--write-report` are both used, the written artifact must use the JSON filename.


--------------------------------------------------
Verification Rules
--------------------------------------------------

MVP verification flow:

1. Run `vib doctor` before anchor or patch work.
2. Run `vib checkpoint` before risky experimentation.
3. Use `vib anchor` to narrow the edit zone.
4. Use `vib patch --preview` before AI editing when preview is needed.
5. After AI editing, run `vib explain` and `vib guard`.
6. If the result is bad, use `vib history` and `vib undo`.

Guard checks in MVP:

- structural damage detection
- anchor coverage regression detection
- oversized file regression detection
- unsafe edit warning generation

Guard result thresholds in MVP:

- pass: no blocking structural failures detected
- warn: risky but non-blocking findings detected
- fail: blocking structural failures detected or required metadata is unreadable

Mode semantics:

- default mode: standard structural checks and human-readable output
- `--strict`: any warning-level structural finding becomes a failure in MVP

Exit code contract for MVP commands:

- `0`: command completed successfully, including `warn` in default mode
- `1`: validation or guard failure
- `2`: internal processing failure



--------------------------------------------------
vib export
--------------------------------------------------

Export helper templates for external AI coding tools.

Supported tools:

- Claude Code
- OpenCode
- Cursor
- Antigravity

Examples:

vib export claude
vib export opencode
vib export cursor
vib export antigravity



--------------------------------------------------
vib watch
--------------------------------------------------

Real-time project monitoring.

Detects risky changes while the project is being edited.

Example:

vib watch



--------------------------------------------------
Design Principles
--------------------------------------------------

1. CLI must remain simple and predictable
2. Commands must be safe for existing projects
3. Default behavior must never break user code
4. Every command should guide the next action

The CLI should feel like a guided workflow rather than a collection of unrelated commands.
