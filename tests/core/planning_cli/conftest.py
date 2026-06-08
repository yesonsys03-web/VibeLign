# tests/core/planning_cli/conftest.py
import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path_factory, monkeypatch):
    """planning_cli 테스트가 실제 ~/.vibelign/gui_config.json 을 읽지 않도록 격리.

    개별 테스트가 monkeypatch 로 Path.home 을 다시 덮어쓰면 그것이 우선한다.
    """
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setenv("HOME", str(home))
    return home
