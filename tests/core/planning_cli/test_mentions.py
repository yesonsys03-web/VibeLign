from vibelign.core.planning_cli.mentions import resolve_persona_mentions


def test_mentions_resolve_korean_and_english_aliases() -> None:
    text = "@지오랑 @mina가 자동 스크린샷 앱을 검토해줘"

    result = resolve_persona_mentions(text)

    assert result.persona_ids == ("gio", "mina")
    assert result.used_default is False
    assert result.clean_text == "자동 스크린샷 앱을 검토해줘"


def test_mentions_resolve_all_alias_to_every_persona() -> None:
    text = "@모두 자동 스크린샷 앱을 기획해줘"

    result = resolve_persona_mentions(text)

    assert result.persona_ids == ("chloe", "gio", "mina")
    assert result.used_default is False
    assert result.clean_text == "자동 스크린샷 앱을 기획해줘"


def test_mentions_default_to_prepared_persona_set() -> None:
    text = "자동 스크린샷 앱을 만들고 싶어"

    result = resolve_persona_mentions(text)

    assert result.persona_ids == ("chloe", "gio", "mina")
    assert result.used_default is True
    assert result.clean_text == text
