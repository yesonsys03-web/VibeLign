from argparse import Namespace
from pathlib import Path

import pytest

from vibelign.cli.vib_cli import build_parser
from vibelign.commands.vib_doctor_cmd import run_vib_doctor


def _parse(argv: list[str]) -> Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def test_fix_anchors_dry_run_reports_candidates_without_modifying_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "main.py"
    _ = target.write_text("def main():\n    return True\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    args = _parse(["doctor", "--fix-anchors", "--dry-run"])
    run_vib_doctor(args)

    captured = capsys.readouterr()
    assert "main.py" in captured.out
    assert "ANCHOR:" not in target.read_text(encoding="utf-8")


def test_fix_anchors_paths_limits_application_to_requested_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    included = tmp_path / "included.py"
    skipped = tmp_path / "skipped.py"
    _ = included.write_text("def included():\n    return True\n", encoding="utf-8")
    _ = skipped.write_text("def skipped():\n    return True\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    args = _parse(["doctor", "--fix-anchors", "--paths", "included.py"])
    run_vib_doctor(args)

    assert "ANCHOR:" in included.read_text(encoding="utf-8")
    assert "ANCHOR:" not in skipped.read_text(encoding="utf-8")


def test_fix_anchors_paths_accepts_windows_style_separators(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    included = src_dir / "included.py"
    _ = included.write_text("def included():\n    return True\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    args = _parse(["doctor", "--fix-anchors", "--paths", "src\\included.py"])
    run_vib_doctor(args)

    assert "ANCHOR:" in included.read_text(encoding="utf-8")


def test_fix_anchors_skips_trivial_init_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    init_file = pkg / "__init__.py"
    _ = init_file.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    args = _parse(["doctor", "--fix-anchors"])
    run_vib_doctor(args)

    assert init_file.read_text(encoding="utf-8") == ""


def test_fix_anchors_skips_symlinks_outside_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside.py"
    _ = outside.write_text("def outside():\n    return True\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    link.symlink_to(outside)
    monkeypatch.chdir(tmp_path)

    try:
        args = _parse(["doctor", "--fix-anchors"])
        run_vib_doctor(args)

        assert "ANCHOR:" not in outside.read_text(encoding="utf-8")
    finally:
        outside.unlink(missing_ok=True)


def test_fix_anchors_paths_rejects_outside_project_without_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside.py"
    _ = outside.write_text("def outside():\n    return True\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    try:
        args = _parse(["doctor", "--fix-anchors", "--paths", f"../{outside.name}"])
        with pytest.raises(SystemExit) as exc_info:
            run_vib_doctor(args)

        assert "project-outside path" in str(exc_info.value)
        assert "ANCHOR:" not in outside.read_text(encoding="utf-8")
    finally:
        outside.unlink(missing_ok=True)
