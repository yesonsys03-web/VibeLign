import json
from pathlib import Path

from vibelign.core.planning_cli.planning_config import (
    PersonaConfig,
    load_persona_config,
)


def _write_config(home: Path, payload: dict) -> None:
    cfg_dir = home / ".vibelign"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "gui_config.json").write_text(json.dumps(payload), encoding="utf-8")


def test_missing_file_returns_empty_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    cfg = load_persona_config()
    assert cfg.get("chloe") is None  # 호출자가 기본값을 채움


def test_reads_enabled_and_provider(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    _write_config(
        tmp_path,
        {
            "planning_personas": {
                "version": 1,
                "personas": {
                    "chloe": {"enabled": False, "provider": "codex"},
                },
            }
        },
    )
    cfg = load_persona_config()
    assert cfg["chloe"] == PersonaConfig(enabled=False, provider="codex")


def test_corrupt_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    cfg_dir = tmp_path / ".vibelign"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "gui_config.json").write_text("{ not json", encoding="utf-8")
    assert load_persona_config() == {}


def test_partial_entry_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    _write_config(
        tmp_path,
        {"planning_personas": {"personas": {"gio": {"provider": "claude"}}}},
    )
    cfg = load_persona_config()
    assert cfg["gio"] == PersonaConfig(enabled=True, provider="claude")


def test_non_boolean_enabled_defaults_true_for_rust_parity(tmp_path, monkeypatch):
    # Rust 측은 as_bool() 이 None 이면 true 로 본다. null/0/"" 같은 비-boolean
    # enabled 값에서 두 경로가 같은 결과(활성)를 내도록 보장한다.
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    _write_config(
        tmp_path,
        {
            "planning_personas": {
                "personas": {
                    "chloe": {"enabled": None},
                    "gio": {"enabled": 0},
                    "mina": {"enabled": ""},
                    "deepseek": {"enabled": False},
                }
            }
        },
    )
    cfg = load_persona_config()
    assert cfg["chloe"].enabled is True
    assert cfg["gio"].enabled is True
    assert cfg["mina"].enabled is True
    # 명시적 boolean False 만 비활성
    assert cfg["deepseek"].enabled is False
