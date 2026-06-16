from vibelign.core.reporting_cli.reader import parse_plan_markdown


SAMPLE = """# 예약 앱

## 한 줄 목표
미용실 예약을 앱으로 받고 싶어요.

## 만들고 싶은 이유
전화 예약이 많아 누락이 자주 생깁니다.

## 대상 사용자
동네 미용실 사장님.

## 핵심 기능
- 예약 캘린더
- 알림 문자
- 아직 결정이 필요합니다.

## 사용자 흐름
- 손님이 시간 선택
1. 사장이 확정

## 제외할 것
결제 연동

## 아직 결정이 필요한 질문
1) 노쇼 정책은?
"""


def test_parse_extracts_title_and_idea():
    data = parse_plan_markdown(SAMPLE)
    assert data.title == "예약 앱"
    assert data.idea == "미용실 예약을 앱으로 받고 싶어요."
    assert data.problem == "전화 예약이 많아 누락이 자주 생깁니다."


def test_parse_extracts_list_sections():
    data = parse_plan_markdown(SAMPLE)
    assert data.features == ["예약 캘린더", "알림 문자"]
    assert data.flows == ["손님이 시간 선택", "사장이 확정"]
    assert data.exclusions == ["결제 연동"]
    assert data.open_questions == ["노쇼 정책은?"]


def test_parse_drops_placeholder_items():
    data = parse_plan_markdown(SAMPLE)
    assert "아직 결정이 필요합니다." not in data.features


def test_parse_empty_text_returns_blank_data():
    data = parse_plan_markdown("")
    assert data.title == ""
    assert data.features == []


def test_parse_accepts_numbered_and_plain_list_lines():
    data = parse_plan_markdown(
        "# 앱\n\n## 핵심 기능\n1. 캘린더\n2) 알림\n일반 메모\n"
    )
    assert data.features == ["캘린더", "알림", "일반 메모"]
