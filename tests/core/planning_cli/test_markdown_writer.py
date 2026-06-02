from vibelign.core.planning_cli.markdown_writer import SECTION_TITLES, build_template_markdown


def test_template_markdown_contains_required_sections() -> None:
    markdown = build_template_markdown("예약 앱 만들고 싶어")
    for section in SECTION_TITLES:
        assert f"## {section}" in markdown


def test_template_markdown_avoids_legacy_terms() -> None:
    markdown = build_template_markdown("예약 앱 만들고 싶어")
    forbidden = ("CodeSpeak", "target_anchor", "patch")
    for term in forbidden:
        assert term.lower() not in markdown.lower()
