from pathlib import Path
import unicodedata

import pytest

from vibelign.core.recovery.path import PathSafetyError, normalize_recovery_path


def test_normalize_recovery_path_returns_project_relative_display_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    target = root / "src" / "app.py"
    _ = target.parent.mkdir()
    _ = target.write_text("print('ok')\n", encoding="utf-8")

    normalized = normalize_recovery_path(root, "src\\app.py")

    assert normalized.relative_path == "src/app.py"
    assert normalized.display_path == "src/app.py"
    assert normalized.absolute_path == target.resolve()
    assert normalized.was_absolute_input is False


def test_parent_traversal_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()

    with pytest.raises(PathSafetyError, match="project root|parent traversal"):
        _ = normalize_recovery_path(root, "../secret.txt")


def test_absolute_path_requires_trusted_local_cli(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    target = root / "src" / "app.py"
    _ = target.parent.mkdir()
    _ = target.write_text("print('ok')\n", encoding="utf-8")

    with pytest.raises(PathSafetyError, match="absolute paths"):
        _ = normalize_recovery_path(root, str(target))

    normalized = normalize_recovery_path(root, str(target), trusted_local_cli=True)
    assert normalized.relative_path == "src/app.py"
    assert normalized.was_absolute_input is True


def test_generated_directories_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()

    with pytest.raises(PathSafetyError, match="generated or internal"):
        _ = normalize_recovery_path(root, "node_modules/pkg/index.js")


def test_windows_reserved_names_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()

    with pytest.raises(PathSafetyError, match="Windows reserved"):
        _ = normalize_recovery_path(root, "src/CON.txt")


def test_windows_ads_streams_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()

    with pytest.raises(PathSafetyError, match="ADS"):
        _ = normalize_recovery_path(root, "src/app.py:stream")


def test_trailing_dot_or_space_segments_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()

    with pytest.raises(PathSafetyError, match="trailing dot or space"):
        _ = normalize_recovery_path(root, "src/app.")
    with pytest.raises(PathSafetyError, match="whitespace"):
        _ = normalize_recovery_path(root, "src/app.py ")


def test_unicode_paths_are_normalized_to_nfc(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _ = root.mkdir()
    decomposed = "cafee\u0301.py".replace("ee", "e")
    normalized = normalize_recovery_path(root, f"src/{decomposed}")

    assert normalized.relative_path == unicodedata.normalize("NFC", f"src/{decomposed}")


def test_windows_drive_input_can_match_wsl_project_root_identity() -> None:
    normalized = normalize_recovery_path(
        Path("/mnt/c/repo"),
        "C:\\repo\\src\\app.py",
        trusted_local_cli=True,
    )

    assert normalized.relative_path == "src/app.py"
    assert normalized.was_absolute_input is True


def test_existing_case_insensitive_collisions_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    src = root / "src"
    _ = src.mkdir(parents=True)
    _ = (src / "App.py").write_text("print('upper')\n", encoding="utf-8")

    with pytest.raises(PathSafetyError, match="case-insensitive"):
        _ = normalize_recovery_path(root, "src/app.py")
