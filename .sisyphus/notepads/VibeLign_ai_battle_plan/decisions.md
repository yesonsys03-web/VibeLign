# VibeLign ELI15 Design - Architecture Decisions & Recommendations

## Recommended Architecture Changes
1. **Collapse the Synthesis Pipeline**: Merge `Conflict Finder`, `Term Simplifier`, `Decision Builder`, and `ELI15 Renderer` into a **single LLM prompt** using a fast model (e.g., Haiku/GPT-4o-mini). Pass the 3 raw outputs and enforce the ELI15 tone via system instructions.
2. **Strict Structured Outputs**: Use structured JSON outputs for the synthesis step to guarantee the GUI receives exactly: `Problem Definition`, `Options (optional)`, `Recommendation`, `Reason`, `Next Actions`.
3. **Dynamic "Consensus" Mode**: If the synthesis model detects total agreement among the 3 AIs, skip the "Options" array and render a unified recommendation path.
4. **Stream Synthesis Directly**: The GUI should show "Collecting AI Responses" while waiting, and immediately switch to streaming the JSON/Markdown of the final synthesis to minimize perceived latency.