# === ANCHOR: MARKDOWN_WRITER_START ===
from __future__ import annotations

from vibelign.core.planning_cli.questions import questions_for_idea

FORBIDDEN_MARKDOWN_TERMS = ("CodeSpeak", "target_anchor")

SECTION_TITLES: tuple[str, ...] = (
    "한 줄 목표",
    "만들고 싶은 이유",
    "대상 사용자",
    "핵심 기능",
    "화면 또는 사용 흐름",
    "제외할 것",
    "아직 결정이 필요한 질문",
    "구현 전에 AI가 알아야 할 맥락",
    "다음 단계",
)


# === ANCHOR: MARKDOWN_WRITER_PROJECT_TITLE_FROM_IDEA_START ===
def project_title_from_idea(idea: str) -> str:
    normalized = " ".join(idea.split())
    if not normalized:
        return "새 기획안"
    title = normalized[:40].strip()
    return title if len(normalized) <= 40 else f"{title}..."
# === ANCHOR: MARKDOWN_WRITER_PROJECT_TITLE_FROM_IDEA_END ===


# === ANCHOR: MARKDOWN_WRITER_BUILD_TEMPLATE_MARKDOWN_START ===
def build_template_markdown(idea: str, *, language: str = "auto") -> str:
    title = project_title_from_idea(idea)
    questions = questions_for_idea(idea)
    question_lines = "\n".join(f"- {question.label}" for question in questions)
    markdown = f"""# {title}
## 한 줄 목표
# === ANCHOR: MARKDOWN_WRITER_BUILD_TEMPLATE_MARKDOWN_END ===
{idea.strip()}

## 만들고 싶은 이유
아직 결정이 필요합니다.

## 대상 사용자
아직 결정이 필요합니다.

## 핵심 기능
- 아직 결정이 필요합니다.

## 화면 또는 사용 흐름
- 아직 결정이 필요합니다.

## 제외할 것
- 아직 결정이 필요합니다.

## 아직 결정이 필요한 질문
{question_lines}

## 구현 전에 AI가 알아야 할 맥락
- 언어 설정: {language}
- 추가 맥락은 아직 결정이 필요합니다.

## 다음 단계
- 위 질문에 답한 뒤 기획안을 구체화합니다.
"""
    for term in FORBIDDEN_MARKDOWN_TERMS:
        if term in markdown:
            raise ValueError(f"forbidden planning term generated: {term}")
    if "patch" in markdown.lower():
        raise ValueError("forbidden planning term generated: patch")
    return markdown
# === ANCHOR: MARKDOWN_WRITER_END ===
