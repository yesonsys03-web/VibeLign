from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningInput:
    idea: str
    language: str = "auto"
    output: str | None = None
    force: bool = False


@dataclass(frozen=True)
class PlanningResult:
    output_path: str
    absolute_output_path: str
    markdown: str
    fallback_reason: str | None
    session_id: str
    adapter: str | None = None
    persona_id: str | None = None
    llm_status: str | None = None

    def with_markdown(self, markdown: str) -> "PlanningResult":
        return PlanningResult(
            output_path=self.output_path,
            absolute_output_path=self.absolute_output_path,
            markdown=markdown,
            fallback_reason=self.fallback_reason,
            session_id=self.session_id,
            adapter=self.adapter,
            persona_id=self.persona_id,
            llm_status=self.llm_status,
        )

    def with_llm_status(
        self,
        *,
        adapter: str,
        persona_id: str,
        llm_status: str,
        fallback_reason: str | None,
    ) -> "PlanningResult":
        return PlanningResult(
            output_path=self.output_path,
            absolute_output_path=self.absolute_output_path,
            markdown=self.markdown,
            fallback_reason=fallback_reason,
            session_id=self.session_id,
            adapter=adapter,
            persona_id=persona_id,
            llm_status=llm_status,
        )
