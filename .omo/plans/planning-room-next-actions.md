# Planning Room Next Actions

## TODOs

- [x] Connect saved planning Markdown to the next user action.
  - Extract planning-room action controls into a focused component.
  - Show `AI 작업 시작` only after a saved `plans/*.md` exists.
  - Make `AI 작업 시작` return to Home and preserve the saved output path.
  - Show the saved output path on Home instead of dropping it as `null`.

- [x] Improve deterministic planning Markdown synthesis quality.
  - Keep the current stable file-save behavior.
  - Better distribute persona responses into feature, flow, exclusion, and open-question sections.
  - Keep transcript-style raw messages visible only in the dedicated conversation summary section.

## Final Verification Wave

- [x] Run focused GUI tests, lint touched TypeScript files, and record a manual UI QA artifact.
