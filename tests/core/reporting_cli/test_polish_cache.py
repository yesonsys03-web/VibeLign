from pathlib import Path

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.polish_cache import (
    load_polish_cache,
    polish_cache_key,
    save_polish_cache,
)


def _model(text="원문"):
    return ReportModel(
        title="t", report_type="work", date="2026-06-16",
        sections=[Section("S", [Block(kind="paragraph", text=text)])],
    )


def test_key_changes_with_content_and_provider():
    k1 = polish_cache_key(_model("a"), provider="auto")
    k2 = polish_cache_key(_model("b"), provider="auto")
    k3 = polish_cache_key(_model("a"), provider="codex")
    assert k1 != k2 and k1 != k3


def test_save_then_load_roundtrip(tmp_path: Path):
    polished = _model("다듬음")
    save_polish_cache(tmp_path, "예약-앱-work", key="abc", model=polished)
    hit = load_polish_cache(tmp_path, "예약-앱-work", key="abc")
    assert hit is not None
    assert hit.sections[0].blocks[0].text == "다듬음"


def test_load_miss_on_key_mismatch(tmp_path: Path):
    save_polish_cache(tmp_path, "s", key="abc", model=_model("x"))
    assert load_polish_cache(tmp_path, "s", key="zzz") is None


def test_load_miss_when_absent(tmp_path: Path):
    assert load_polish_cache(tmp_path, "none", key="abc") is None
