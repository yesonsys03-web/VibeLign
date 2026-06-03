from pathlib import Path

from vibelign.core.planning_cli.mentions import resolve_persona_mentions
from vibelign.core.planning_cli.personas import ORDERED_PERSONAS


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


def test_mentions_derive_persona_aliases_from_persona_metadata() -> None:
    source = Path("vibelign/core/planning_cli/mentions.py").read_text(encoding="utf-8")

    for persona in ORDERED_PERSONAS:
        text = f"@{persona.name} {persona.prompt_role}에게 물어봐"

        result = resolve_persona_mentions(text)

        assert result.persona_ids == (persona.id,)
        assert result.clean_text == f"{persona.prompt_role}에게 물어봐"

    assert '"chloe": ("chloe", "클로이")' not in source
    assert '"gio": ("gio", "지오")' not in source
    assert '"mina": ("mina", "미나")' not in source
