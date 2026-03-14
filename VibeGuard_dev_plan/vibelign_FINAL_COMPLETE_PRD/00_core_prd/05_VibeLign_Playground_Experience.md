# VibeLign - Playground Experience

VibeLign should feel like a safe playground for novice vibe coders.

The system must not expect precise technical language from the user.

Core playground loop:

1. user says something rough
2. VibeLign interprets the request
3. VibeLign shows the CodeSpeak translation
4. VibeLign explains what it is about to do
5. VibeLign suggests the next safe step

Experience rules:

- rough requests are normal, not errors
- low-confidence interpretation should trigger clarification, not blind editing
- middle-school-level explanation is the default for beginner-facing output
- preview should come before risky action
- failure should feel recoverable, not punishing
- checkpoint, history, and undo are part of the beginner safety net

Visible output contract:

- `Interpretation:` what VibeLign thinks the user means
- `CodeSpeak:` internal structured translation
- `Confidence:` confidence for the interpretation
- `Next step:` one recommended safe action

Spec scenarios:

Given a vague request like `make the UI nicer`, when `vib patch` runs, then it should show an interpretation, a CodeSpeak translation, a confidence score, and 1-3 clarifying questions if confidence is low.

Given a clear request like `add progress bar`, when `vib patch --preview` runs, then it should show the target, the CodeSpeak translation, and a simple explanation of the expected change.

Given AI edits are applied, when `vib explain` runs, then the default explanation should answer:

- what changed
- why it matters
- what to do next

Given a beginner wants to experiment, when following the default workflow, then the path should stay preview-first and guard-after-edit.

Given a beginner makes a bad edit, when they check history and run undo, then recovery should feel simple and expected rather than advanced.

Given a request is ambiguous, when confidence is below threshold, then VibeLign should prefer clarification over automatic action.
