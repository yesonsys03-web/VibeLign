from vibelign.core.planning_cli import cli_adapters


def test_resolve_opencode_executable(monkeypatch):
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.shutil.which",
        lambda name: f"/bin/{name}" if name == "opencode" else None,
    )
    assert cli_adapters.resolve_cli_executable("opencode") == "/bin/opencode"


def test_build_opencode_command(monkeypatch):
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.shutil.which",
        lambda name: f"/bin/{name}",
    )
    cmd = cli_adapters.build_cli_command("opencode", "프롬프트")
    assert cmd == [
        "/bin/opencode",
        "run",
        "-m",
        "opencode/deepseek-v4-flash-free",
        "프롬프트",
    ]


def test_select_adapter_accepts_opencode():
    assert cli_adapters.select_adapter("opencode") == "opencode"


def test_probe_includes_opencode(monkeypatch):
    monkeypatch.setattr(
        "vibelign.core.planning_cli.cli_adapters.shutil.which",
        lambda name: None,
    )
    adapters = [c.adapter for c in cli_adapters.probe_cli_candidates()]
    assert "opencode" in adapters
