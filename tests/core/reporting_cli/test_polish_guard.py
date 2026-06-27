from __future__ import annotations

from vibelign.core.reporting_cli.polish_guard import (
    extract_numbers,
    guard_polished,
    looks_like_non_answer,
)


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


_REAL_GARBAGE = (
    "This is an **evaluation/clarification** intent — you've given me the "
    "refinement instructions but I don't see the actual sentence to refine.\n\n"
    "**어떤 문장을 다듬어 드릴까요?**"
)


def test_nonanswer_detects_real_garbage():
    assert looks_like_non_answer("동네 미용실 사장님", _REAL_GARBAGE) is True


def test_nonanswer_detects_markdown_bold():
    assert looks_like_non_answer("짧은 원문", "**다듬은 결과**") is True


def test_nonanswer_detects_length_blowup():
    assert looks_like_non_answer("짧은 문장", "가" * 200) is True


def test_nonanswer_allows_clean_rewrite():
    base = "전화 예약 누락을 줄이려고 MVP 를 빨리 deploy 하는 게 목표임. 신규 회원 50% 증가 기대."
    pol = "전화 예약 누락을 줄이기 위해 MVP를 신속히 deploy하는 것이 목표입니다. 신규 회원 50% 증가가 기대됩니다."
    assert looks_like_non_answer(base, pol) is False


def test_nonanswer_allows_short_clean_rewrite():
    assert looks_like_non_answer("동네 미용실 사장님", "동네 미용실 사장님입니다") is False
