import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path_factory, monkeypatch):
    """reporting_cli 테스트가 실제 ~/.vibelign 설정을 읽지 않도록 격리."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    monkeypatch.setenv("HOME", str(home))
    return home
