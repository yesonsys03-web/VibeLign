# VibeLign — `vib doctor` Final Design Spec
Version: Final Draft 1.0

This document defines the most important command in VibeLign:

`vib doctor`

The goal of `vib doctor` is to become the **entry point** for users.
It should immediately tell users:

- what is wrong with the project
- what is risky for AI editing
- what they should do next

In short:

> `vib doctor` is the health check, safety scanner, and onboarding guide for the whole product.

---

# 1. Product Role

`vib doctor` is the command that makes users trust VibeLign.

Why it matters:

- It gives instant value
- It works before any patching
- It explains project risk in human language
- It guides the next action

If this command is excellent, users will understand VibeLign immediately.

---

# 2. Primary User Promise

When a user runs:

```bash
vib doctor
```

They should get answers to these questions:

1. Is my project safe for AI editing?
2. Which files are risky?
3. Which files are too large or messy?
4. Do I have anchors?
5. What should I do next?

---

# 3. Core Output Philosophy

The command output should feel:

- clear
- visual
- non-threatening
- useful even for non-programmers

It should avoid overly technical output by default.

Bad:

```text
AST traversal found multiple mixed concerns in module.
```

Good:

```text
This file mixes screen code and business logic.
AI may modify it in unsafe ways.
```

---

# 4. Doctor Responsibilities

`vib doctor` should perform these checks.

## 4.1 File Size Check

Detect oversized files.

Suggested thresholds:

- 300+ lines → warning
- 500+ lines → strong warning
- 800+ lines → critical

Reason:
Large files are high-risk for AI drift.

---

## 4.2 Mixed Responsibility Check

Detect likely mixing of:

- UI + business logic
- API + DB logic
- command layer + core engine logic

Goal:
Warn when one file is doing too many unrelated jobs.

---

## 4.3 Anchor Coverage Check

Check:

- how many files contain anchors
- which important files are missing anchors
- estimated protection coverage %

This is one of the most important doctor signals.

---

## 4.4 Entry File Risk Check

Detect if entry files such as:

- main.py
- app.py
- cli.py

are becoming too large or too smart.

Rule:
Entry files should stay thin.

---

## 4.5 Dependency Risk Check

Detect simple structural problems such as:

- circular imports
- suspicious internal import chains
- missing internal module targets

The first version can keep this lightweight.

---

## 4.6 New AI Risk Score

Provide a single project risk score.

Suggested scale:

- 0–20 → Safe
- 21–40 → Caution
- 41–60 → Risky
- 61+ → High Risk

This score must be explainable.

---

# 5. Output Modes

## 5.1 Default Output

Command:

```bash
vib doctor
```

Shows:

- overall health score
- top issues
- next recommended actions

This is the main UX.

---

## 5.2 Detailed Output

Command:

```bash
vib doctor --detailed
```

Shows:

- file-by-file findings
- anchor coverage details
- why each issue matters
- recommended commands

---

## 5.3 JSON Output

Command:

```bash
vib doctor --json
```

Used for:

- scripts
- GUI integration
- future dashboards

JSON contract rule:

- `vib doctor --json` uses the shared Engine API envelope: `{ "ok": ..., "error": ..., "data": ... }`

---

## 5.4 Fix Suggestions

Command:

```bash
vib doctor --fix-hints
```

Shows action guidance such as:

- run `vib anchor --auto`
- split module
- move UI logic to `ui/`
- move services to `engine/` or `analysis/`

The first version should suggest fixes, not auto-apply them.

---

# 6. Recommended Default Output Example

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VibeLign Project Health Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project score: 72 / 100
Status: Caution

Main findings:
1. main.py is too large (612 lines)
2. ui.py mixes screen code and business logic
3. 3 important files are missing anchors
4. Anchor coverage is only 18%

Why this matters:
Large mixed files are more likely to break when edited by AI.

Recommended next steps:
- vib anchor --auto src/ui.py
- split main.py into smaller modules
- run vib doctor --detailed

Summary:
Your project is usable, but AI edits may become unstable unless structure improves.
```

---

# 7. Detailed Output Example

```text
File: src/ui.py
- 428 lines
- contains UI imports: PyQt5
- contains API calls: requests
- contains file IO
Issue:
This file mixes screen code and backend work.

Risk:
AI may modify the wrong area.

Recommendation:
Split UI layout and backend logic into separate modules.
```

---

# 8. JSON Output Example

```json
{
  "ok": true,
  "error": null,
  "data": {
    "project_score": 72,
    "status": "caution",
    "anchor_coverage": 18,
    "issues": [
      {
        "type": "oversized_file",
        "file": "main.py",
        "severity": "high",
        "detail": "612 lines"
      },
      {
        "type": "mixed_responsibility",
        "file": "src/ui.py",
        "severity": "medium",
        "detail": "UI + business logic detected"
      }
    ],
    "recommended_actions": [
      "vib anchor --auto src/ui.py",
      "Split main.py into smaller modules"
    ]
  }
}
```

---

# 9. Human Explanation Rules

Every issue should include:

- what was found
- why it matters
- what the user can do next

Format:

```text
Found:
Why it matters:
Next step:
```

This is critical for vibecoders.

---

# 10. Scoring Model (First Version)

Suggested weighted scoring:

Start at 100.

Subtract:

- oversized file warning: -8
- oversized file critical: -15
- mixed responsibility: -12
- missing anchors in important file: -10
- low anchor coverage: -10
- entry file too large: -10
- circular dependency: -15

Never go below 0.

Status labels:

- 85–100 → Safe
- 70–84 → Good
- 50–69 → Caution
- 30–49 → Risky
- 0–29 → High Risk

---

# 11. Recommended Internal Modules

Suggested implementation split:

```text
cli/doctor.py
analysis/project_scanner.py
analysis/file_metrics.py
analysis/responsibility_detector.py
analysis/anchor_coverage.py
analysis/risk_scoring.py
engine/human_explainer.py
```

Rule:
CLI should orchestrate only.
Actual logic should live outside the CLI layer.

---

# 12. MVP Scope

The first release of `vib doctor` should include only:

- file size detection
- mixed responsibility detection
- anchor coverage
- human-readable report
- JSON output

Do NOT block MVP with:

- full dependency graph
- complex refactor suggestions
- advanced architecture inference

Those can come later.

---

# 13. Versioned Growth Plan

## v1
- basic health score
- file size check
- mixed responsibility check
- anchor coverage check

## v1.1
- entry file warnings
- import issues
- better detailed output

## v1.2
- lightweight dependency graph
- risk trend history
- GUI doctor dashboard integration

---

# 14. Success Criteria

`vib doctor` is successful if:

1. New users understand the product within 10 seconds
2. Users immediately know the next command to run
3. The report feels useful even without patching
4. It becomes the most shared/demoed command in the project

---

# 15. One-Sentence Design Principle

> `vib doctor` should make users feel: “Now I understand my project, and I know what to do next.”
