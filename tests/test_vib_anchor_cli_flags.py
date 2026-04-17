"""CLI regression: `vib anchor --set-intent` forwards extras (aliases/description/warning/connects)."""
import json
from pathlib import Path

import pytest

from vibelign.cli.vib_cli import build_parser
from vibelign.commands.vib_anchor_cmd import run_vib_anchor
from vibelign.core.anchor_tools import load_anchor_meta


@pytest.fixture
def anchor_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    (meta_dir / "anchor_meta.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _parse(argv: list[str]) -> object:
    parser = build_parser()
    return parser.parse_args(argv)


def test_set_intent_forwards_all_extras(anchor_project: Path) -> None:
    args = _parse(
        [
            "anchor",
            "--set-intent", "FOO_BAR",
            "--intent", "설명",
            "--aliases", "apply button, 전체적용, apply btn",
            "--description", "적용 버튼 스타일",
            "--warning", "건들지 마세요",
            "--connects", "BAZ, QUX",
        ]
    )
    run_vib_anchor(args)

    meta = load_anchor_meta(anchor_project)
    entry = meta["FOO_BAR"]
    assert entry["intent"] == "설명"
    assert entry["aliases"] == ["apply button", "전체적용", "apply btn"]
    assert entry["description"] == "적용 버튼 스타일"
    assert entry["warning"] == "건들지 마세요"
    assert entry["connects"] == ["BAZ", "QUX"]
    assert entry["_source"] == "manual"


def test_set_intent_empty_csv_skips_field(anchor_project: Path) -> None:
    """빈 CSV(`","` 또는 공백)는 필드를 None으로 남겨 기존 값 보존."""
    # 1차: aliases 저장
    args_first = _parse(
        [
            "anchor",
            "--set-intent", "FOO",
            "--intent", "v1",
            "--aliases", "a,b",
        ]
    )
    run_vib_anchor(args_first)

    # 2차: aliases 빈 문자열 → 보존
    args_second = _parse(
        [
            "anchor",
            "--set-intent", "FOO",
            "--intent", "v2",
            "--aliases", "",
            "--connects", ",,,",
        ]
    )
    run_vib_anchor(args_second)

    meta = load_anchor_meta(anchor_project)
    entry = meta["FOO"]
    assert entry["intent"] == "v2"
    assert entry["aliases"] == ["a", "b"]  # 빈 CSV는 덮어쓰지 않음
    assert "connects" not in entry  # 처음부터 없었고 빈 CSV는 skip


def test_set_intent_json_mode_prints_entry(
    anchor_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parse(
        [
            "anchor",
            "--set-intent", "ZAP",
            "--intent", "z",
            "--aliases", "x,y",
            "--json",
        ]
    )
    run_vib_anchor(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    entry = payload["data"]["entry"]
    assert entry["aliases"] == ["x", "y"]
    assert entry["_source"] == "manual"


def test_auto_intent_json_stdout_is_pure_json_even_with_ai_chatter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AI provider 가 stdout 에 status 를 찍어도 --json stdout 은 파싱 가능해야 한다."""
    from vibelign.core import ai_explain

    src = tmp_path / "main_window.py"
    _ = src.write_text(
        "# === ANCHOR: MAIN_START ===\n"
        "class Main:\n"
        "    pass\n"
        "# === ANCHOR: MAIN_END ===\n",
        encoding="utf-8",
    )
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    _ = (meta_dir / "anchor_meta.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def chatty_generate(prompt: str, quiet: bool = False) -> tuple[str, list[str]]:
        # 실제 provider 처럼 stdout 에 ✅ 같은 토큰을 흘려보낸다
        print("✅ Anthropic (claude) 호출 중…")
        print("🤖 응답 수신")
        ai_response = json.dumps(
            [{"anchor": "MAIN", "intent": "메인", "aliases": ["m"], "description": "d"}],
            ensure_ascii=False,
        )
        return ai_response, ["Anthropic (claude)"]

    monkeypatch.setattr(ai_explain, "generate_text_with_ai", chatty_generate)
    monkeypatch.setattr(ai_explain, "has_ai_provider", lambda: True)

    args = _parse(["anchor", "--auto-intent", "--json"])
    run_vib_anchor(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out)  # 깨지면 SyntaxError → 회귀
    assert payload["ok"] is True
    assert payload["data"]["total_anchors"] == 1
    # ✅ / 🤖 같은 chatter 는 stderr 로 가야 한다
    assert "✅" in captured.err or "🤖" in captured.err
