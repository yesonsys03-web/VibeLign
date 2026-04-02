# VibeLign ELI15 Design - Identified Issues & Blockers

## Logical Contradictions
1. **Pipeline Overlap**: `Term Simplifier` and `ELI15 Renderer` have overlapping responsibilities. If both use LLMs, it causes redundant latency.
2. **Data Model Mismatch**: `Decision Builder` output (Recommendation, Reason, Alternatives) does not match the final GUI `Output Structure` (Problem Definition, Options, Recommendation, Reason, Next Actions).

## Missing Edge Cases
1. **Total Consensus**: The design assumes conflicts/options will always exist. If all AIs agree, forcing 3 options will confuse the user.
2. **Provider Failures**: No fallback strategy defined for when 1 out of 3 AIs times out or returns an error.
3. **Irreconcilable Complexity**: Over-simplifying deeply technical bugs might strip away nuance required for a safe choice.

## Implementation Risks
1. **Severe Latency**: A sequential pipeline (Collect -> Conflict Find -> Simplify -> Build Decision -> Render) will result in unacceptable TTFB (30-60+ seconds) in a desktop GUI.
2. **Streaming UX**: Waiting for collection to finish before starting synthesis will make the app feel unresponsive.
3. **Cost**: Multi-step LLM evaluations per user request will multiply API costs.