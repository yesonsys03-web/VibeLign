# === ANCHOR: QUESTIONS_START ===
from __future__ import annotations

from dataclasses import dataclass


SHORT_IDEA_THRESHOLD = 40


@dataclass(frozen=True)
# === ANCHOR: QUESTIONS_PLANNINGQUESTION_START ===
class PlanningQuestion:
    id: str
    label: str
# === ANCHOR: QUESTIONS_PLANNINGQUESTION_END ===


SHORT_IDEA_QUESTIONS: tuple[PlanningQuestion, ...] = (
    PlanningQuestion("target_user", "누가 이걸 쓰나요?"),
    PlanningQuestion("core_features", "꼭 필요한 기능은 무엇인가요?"),
    PlanningQuestion("main_flow", "사용자는 어떤 순서로 쓰게 되나요?"),
    PlanningQuestion("excluded_scope", "이번에 만들지 않을 것은 무엇인가요?"),
    PlanningQuestion("context", "AI가 미리 알아야 할 맥락이 있나요?"),
)

DETAILED_IDEA_QUESTIONS: tuple[PlanningQuestion, ...] = (
    PlanningQuestion("target_user", "대상 사용자가 더 구체적으로 누구인가요?"),
    PlanningQuestion("excluded_scope", "이번 범위에서 제외할 것은 무엇인가요?"),
    PlanningQuestion("context", "구현 전에 AI가 알아야 할 제약이 있나요?"),
)


# === ANCHOR: QUESTIONS_QUESTIONS_FOR_IDEA_START ===
def questions_for_idea(idea: str) -> list[PlanningQuestion]:
    normalized = " ".join(idea.split())
    questions = (
        SHORT_IDEA_QUESTIONS
        if len(normalized) < SHORT_IDEA_THRESHOLD
        else DETAILED_IDEA_QUESTIONS
    )
    return list(questions)
# === ANCHOR: QUESTIONS_QUESTIONS_FOR_IDEA_END ===


# === ANCHOR: QUESTIONS_NORMALIZE_ANSWERS_START ===
def normalize_answers(
    answers: dict[str, str | None],
    questions: list[PlanningQuestion],
# === ANCHOR: QUESTIONS_NORMALIZE_ANSWERS_END ===
) -> dict[str, str]:
    return {question.id: (answers.get(question.id) or "").strip() for question in questions}
# === ANCHOR: QUESTIONS_END ===
