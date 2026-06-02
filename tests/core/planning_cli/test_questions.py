from vibelign.core.planning_cli.questions import normalize_answers, questions_for_idea


def test_short_idea_gets_five_questions() -> None:
    assert len(questions_for_idea("예약 앱")) == 5


def test_detailed_idea_gets_three_questions() -> None:
    idea = "동네 카페 예약 앱을 만들고 싶고, 사장님은 시간대를 관리하고 손님은 모바일에서 예약합니다."
    assert len(questions_for_idea(idea)) == 3


def test_normalize_answers_allows_empty_answers() -> None:
    questions = questions_for_idea("예약 앱")
    answers = normalize_answers({questions[0].id: "  손님  "}, questions)
    assert answers[questions[0].id] == "손님"
    assert answers[questions[1].id] == ""
