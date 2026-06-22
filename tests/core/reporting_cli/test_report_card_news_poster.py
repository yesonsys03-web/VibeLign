from __future__ import annotations

from pathlib import Path

import pytest

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.reporting_cli.report_card_news_poster import (
    CardNewsPosterError,
    generate_card_news_poster,
    sanitize_card_news_html,
)


def test_sanitize_strips_script_and_handlers() -> None:
    html = sanitize_card_news_html(
        '<html><body><h1 onclick="x()">A</h1><script>alert(1)</script><p>본문</p></body></html>'
    )
    assert html is not None
    assert "<script" not in html
    assert "onclick" not in html
    assert "본문" in html


def test_sanitize_strips_external_resources() -> None:
    html = sanitize_card_news_html(
        '<html><head><link rel="stylesheet" href="https://cdn/x.css"></head>'
        '<body><img src="https://evil/x.png"><iframe src="//e"></iframe>카드</body></html>'
    )
    assert html is not None
    assert "https://" not in html
    assert "<iframe" not in html
    assert "<link" not in html


def test_sanitize_returns_none_without_html() -> None:
    assert sanitize_card_news_html("그냥 설명 텍스트, HTML 없음") is None


def test_sanitize_keeps_inline_style() -> None:
    html = sanitize_card_news_html("<html><head><style>.c{color:red}</style></head><body>카드</body></html>")
    assert html is not None
    assert "<style>" in html
    assert "color:red" in html


def test_sanitize_strips_protocol_relative_css_url() -> None:
    html = sanitize_card_news_html("<html><head><style>div{background:url(//evil.com/x.png)}</style></head><body>카드</body></html>")
    assert html is not None
    assert "//evil.com" not in html
    assert "<style>" in html  # style block itself kept
    assert "카드" in html


# ---------------------------------------------------------------------------
# Fix #1: dangerous URL schemes — javascript: / vbscript:
# ---------------------------------------------------------------------------


def test_sanitize_strips_javascript_href() -> None:
    html = sanitize_card_news_html('<html><body><a href="javascript:alert(1)">x</a></body></html>')
    assert html is not None
    assert "javascript:" not in html
    assert "x" in html


def test_sanitize_strips_vbscript_href() -> None:
    html = sanitize_card_news_html("<html><body><a href='vbscript:MsgBox(1)'>y</a></body></html>")
    assert html is not None
    assert "vbscript:" not in html
    assert "y" in html


# ---------------------------------------------------------------------------
# Fix #2: data: URIs in image-bearing attrs — kept for inline svg/style
# ---------------------------------------------------------------------------


def test_sanitize_strips_data_uri_img_src() -> None:
    html = sanitize_card_news_html(
        '<html><body>'
        '<img src="data:image/png;base64,AAAA">'
        '<svg><circle r="5"/></svg>'
        '</body></html>'
    )
    assert html is not None
    assert "data:image" not in html
    assert "<svg>" in html  # inline svg kept


# ---------------------------------------------------------------------------
# C2: generate_card_news_poster tests
# ---------------------------------------------------------------------------

class FakeRunner:
    def __init__(self, stdout: str, status: cli_adapters.PlanningCliStatus = "ok") -> None:
        self.stdout, self.status, self.commands = stdout, status, []

    def run(self, command, *, cwd, input_text, timeout_seconds):
        self.commands.append(command)
        return cli_adapters.PlanningCliResult(status=self.status, stdout=self.stdout, stderr="", exit_code=0, duration_ms=7)


def _payload() -> dict:
    card = {
        "id": "c1", "title": "목표", "body": "한 줄 목표", "caption": "출처: 개요",
        "visual_prompt": "scene, no readable text in image", "negative_prompt": "text",
        "source_refs": [], "approved": True,
        "image": {"provider": "agy", "asset_path": "", "prompt": "", "generated": False, "source": "template"},
    }
    return {"schema_version": "report-visual-cards-v1", "status": "ready", "provider": "agy", "cards": [card], "assets": []}


def test_poster_success_returns_sanitized_llm_html(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner("<html><body><h1>카드뉴스</h1><script>x</script></body></html>")
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: ["fake", p])
    p = _payload()
    result = generate_card_news_poster(p, p["cards"], tmp_path, "agy", runner=runner)
    assert result.source == "llm"
    assert "<script" not in result.html
    assert "카드뉴스" in result.html


def test_poster_timeout_falls_back(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner("", status="timeout")
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: ["fake", p])
    p = _payload()
    result = generate_card_news_poster(p, p["cards"], tmp_path, "agy", runner=runner)
    assert result.source == "fallback"
    assert "<html" in result.html.lower()


def test_poster_missing_cli_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: None)
    p = _payload()
    with pytest.raises(CardNewsPosterError):
        _ = generate_card_news_poster(p, p["cards"], tmp_path, "agy")


def test_poster_fallback_is_self_contained_no_img(tmp_path: Path, monkeypatch) -> None:
    # In poster mode the cards carry on-disk per-card SVG assets. The fallback render
    # must NOT emit relative <img src> (those can't load in a null-origin srcDoc iframe);
    # it must be self-contained (inline sketch SVG).
    rel = ".vibelign/reports/card-news/assets/x-card-news/01-card.svg"
    asset = tmp_path / rel
    asset.parent.mkdir(parents=True, exist_ok=True)
    _ = asset.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 150"><rect/></svg>',
        encoding="utf-8",
    )
    p = _payload()
    p["cards"][0]["image"]["asset_path"] = rel
    runner = FakeRunner("", status="timeout")
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda pr, prompt: ["fake", pr])

    result = generate_card_news_poster(p, p["cards"], tmp_path, "claude", runner=runner)

    assert result.source == "fallback"
    assert "<img" not in result.html
    assert "<svg" in result.html


def test_sanitize_rejects_js_interactive_buttons() -> None:
    # The model stripped of <script> leaves dead buttons and JS-hidden content; treat as
    # unusable so the caller falls back to the static deterministic render.
    html = sanitize_card_news_html(
        '<html><body><button id="slide-mode-btn">슬라이드 보기</button>'
        '<div class="slide inactive" style="display:none">카드2</div></body></html>'
    )
    assert html is None


def test_poster_with_buttons_falls_back_to_static(tmp_path: Path, monkeypatch) -> None:
    interactive = (
        "<html><body><button id=\"b\">슬라이드 보기</button>"
        "<div class=\"slide inactive\" style=\"display:none\">카드 본문</div></body></html>"
    )
    runner = FakeRunner(interactive)
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: ["fake", p])
    p = _payload()

    result = generate_card_news_poster(p, p["cards"], tmp_path, "agy", runner=runner)

    assert result.source == "fallback"
    assert "<button" not in result.html.lower()


def test_poster_prompt_forbids_js_and_requires_all_visible() -> None:
    from vibelign.core.reporting_cli.report_card_news_poster import _poster_prompt

    p = _payload()
    prompt = _poster_prompt(p["cards"])
    assert "JavaScript" in prompt
    assert "button" in prompt.lower()
    assert "모든 카드" in prompt
