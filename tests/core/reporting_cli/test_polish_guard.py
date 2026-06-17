from __future__ import annotations

from vibelign.core.reporting_cli.polish_guard import extract_numbers, guard_polished


def test_extract_normalizes_thousands_separator():
    assert extract_numbers("회원 1,000명, 매출 50% 증가") == {"1000", "50"}


def test_guard_ok_when_numbers_preserved():
    ok, reason, missing = guard_polished("신규 회원 50% 증가", "신규 회원이 50% 늘었습니다")
    assert ok is True
    assert reason == ""
    assert missing == []


def test_guard_fails_when_number_dropped():
    ok, reason, missing = guard_polished("신규 회원 50% 증가", "신규 회원이 대폭 늘었습니다")
    assert ok is False
    assert reason == "number_dropped"
    assert missing == ["50"]


def test_guard_fails_when_new_number_added():
    ok, reason, missing = guard_polished("회원이 늘었다", "회원이 200% 늘었다")
    assert ok is False
    assert reason == "number_added"


def test_guard_ok_when_no_numbers_either_side():
    ok, reason, missing = guard_polished("회원이 늘었다", "회원이 증가했습니다")
    assert ok is True


def test_guard_ok_when_date_reformatted():
    # '06'(원본) 과 '6'(다듬) 을 같게 보아 멀쩡한 날짜 재포맷을 되돌리지 않는다.
    ok, reason, missing = guard_polished("기한 2026-06-17 까지", "기한 2026년 6월 17일까지")
    assert ok is True
    assert missing == []
