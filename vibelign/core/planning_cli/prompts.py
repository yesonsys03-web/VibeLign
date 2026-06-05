# === ANCHOR: PROMPTS_START ===
from __future__ import annotations

from vibelign.core.planning_cli.personas import PlanningPersona


# === ANCHOR: PROMPTS_BUILD_PERSONA_PROMPT_START ===
def build_persona_prompt(
    persona: PlanningPersona,
    idea: str,
    template_markdown: str,
# === ANCHOR: PROMPTS_BUILD_PERSONA_PROMPT_END ===
) -> str:
    return "\n".join(
        [
            f"VibeLign 기획방의 {persona.prompt_role} 페르소나로 답하세요.",
            "초보자가 읽기 쉬운 한국어로 기획안을 보강하세요.",
            "불확실한 내용은 아직 결정이 필요한 질문으로 남기세요.",
            "프로젝트 전체 소스 코드를 요청하지 마세요.",
            "내부 구현 용어를 사용자용 기획안에 쓰지 마세요.",
            "",
            f"사용자 아이디어: {idea.strip()}",
            "",
            "현재 기획안:",
            template_markdown,
        ]
    )


# === ANCHOR: PROMPTS_APPEND_PERSONA_SECTION_START ===
def append_persona_section(markdown: str, section_title: str, response: str) -> str:
    return f"{markdown.rstrip()}\n\n## {section_title}\n{response.strip()}\n"
# === ANCHOR: PROMPTS_APPEND_PERSONA_SECTION_END ===
# === ANCHOR: PROMPTS_END ===
