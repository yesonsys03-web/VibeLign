import os
import builtins
from argparse import Namespace

from vibelign.core.keys_store import (
    _keys_file_path_for_platform,
    delete_key,
    get_key,
    has_any_ai_key,
    is_key_disabled,
    load_keys,
    save_key,
)


def test_windows_key_path_uses_appdata_when_available() -> None:
    path = _keys_file_path_for_platform("nt", r"C:\Users\me\AppData\Roaming", None, r"C:\Users\me")

    assert str(path) == r"C:\Users\me\AppData\Roaming/vibelign/api_keys.json"


def test_windows_key_path_falls_back_to_user_roaming_profile() -> None:
    path = _keys_file_path_for_platform("nt", None, None, r"C:\Users\me")

    assert str(path) == r"C:\Users\me/AppData/Roaming/vibelign/api_keys.json"


def test_delete_key_disables_matching_environment_variable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")

    assert get_key("GEMINI_API_KEY") == "env-key"
    assert has_any_ai_key()

    delete_key("GEMINI_API_KEY")

    assert get_key("GEMINI_API_KEY") is None
    assert not has_any_ai_key()
    assert is_key_disabled("GEMINI_API_KEY")
    assert "GEMINI_API_KEY" not in load_keys()


def test_saved_key_reenables_and_takes_precedence_over_environment_variable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    delete_key("GEMINI_API_KEY")

    save_key("GEMINI_API_KEY", "saved-key")

    os.environ["GEMINI_API_KEY"] = "env-key"

    assert not is_key_disabled("GEMINI_API_KEY")
    assert get_key("GEMINI_API_KEY") == "saved-key"
    assert load_keys()["GEMINI_API_KEY"] == "saved-key"


def test_saved_key_takes_precedence_over_stale_environment_variable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "stale-env-key")

    save_key("GEMINI_API_KEY", "fresh-saved-key")

    assert get_key("GEMINI_API_KEY") == "fresh-saved-key"


def test_config_delete_can_disable_environment_only_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    answers = iter(["7", "1"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(answers))

    from vibelign.commands.config_cmd import run_config

    run_config(Namespace(ai_enhance=None, config_args=[]))

    assert get_key("GEMINI_API_KEY") is None
    assert is_key_disabled("GEMINI_API_KEY")
