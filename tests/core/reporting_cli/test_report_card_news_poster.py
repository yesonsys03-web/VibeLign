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
