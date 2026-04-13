"""Tests for patch_builder operation-based related_files post-processing."""

from pathlib import Path

from vibelign.patch.patch_builder import (
    _dedupe_related_files,
    _extract_codespeak_action,
    _extract_codespeak_subject,
    _postprocess_related_files,
)


class _FakeCodeSpeak:
    def __init__(self, action="update", subject=""):
        self.action = action
        self.subject = subject


def test_extract_codespeak_action():
    cs = _FakeCodeSpeak(action="add")
    assert _extract_codespeak_action(cs) == "add"


def test_extract_codespeak_action_default():
    assert _extract_codespeak_action(object()) == "update"


def test_extract_codespeak_subject():
    cs = _FakeCodeSpeak(subject="WatchLog")
    assert _extract_codespeak_subject(cs) == "WatchLog"


def test_dedupe_related_files():
    items = [
        {"file": "a.ts", "role": "utility"},
        {"file": "b.ts", "role": "component"},
        {"file": "a.ts", "role": "data_source"},  # duplicate
    ]
    result = _dedupe_related_files(items)
    assert len(result) == 2
    assert result[0]["role"] == "utility"  # first-win


def test_dedupe_related_files_invalid_file():
    items = [
        {"file": "a.ts"},
        {"no_file_key": True},
        {"file": 123},
    ]
    result = _dedupe_related_files(items)
    assert len(result) == 1


def test_postprocess_move_clears_related_files(tmp_path):
    raw = [{"file": "lib.ts", "role": "utility", "anchor": None, "reason": "test", "exists": True}]
    result = _postprocess_related_files(
        raw, "move", "move",
        root=tmp_path, best_path=tmp_path / "App.tsx",
        codespeak_subject="",
    )
    assert result == []


def test_postprocess_update_keeps_raw(tmp_path):
    raw = [{"file": "lib.ts", "role": "utility", "anchor": None, "reason": "test", "exists": True}]
    result = _postprocess_related_files(
        raw, "update", "update",
        root=tmp_path, best_path=tmp_path / "App.tsx",
        codespeak_subject="",
    )
    assert len(result) == 1
    assert result[0]["file"] == "lib.ts"


def test_postprocess_add_appends_new_file(tmp_path):
    components = tmp_path / "components"
    components.mkdir()
    (components / "Button.tsx").write_text("")
    raw = [{"file": "lib.ts", "role": "utility", "anchor": None, "reason": "test", "exists": True}]
    result = _postprocess_related_files(
        raw, "add", "add",
        root=tmp_path, best_path=components / "App.tsx",
        codespeak_subject="WatchLog",
    )
    assert len(result) == 2
    new_entry = [r for r in result if r.get("role") == "new_file"]
    assert len(new_entry) == 1
    assert new_entry[0]["exists"] is False
    assert "WatchLog" in str(new_entry[0]["file"])


def test_postprocess_add_dedupes_existing_and_new(tmp_path):
    components = tmp_path / "components"
    components.mkdir()
    (components / "Button.tsx").write_text("")
    # raw already has the same path that would be inferred
    raw = [
        {"file": str(Path("components/WatchLog.tsx")), "role": "utility", "anchor": None, "reason": "existing", "exists": True},
    ]
    result = _postprocess_related_files(
        raw, "add", "add",
        root=tmp_path, best_path=components / "App.tsx",
        codespeak_subject="WatchLog",
    )
    # existing entry should win, no duplicate
    assert len(result) == 1
    assert result[0]["role"] == "utility"  # first-win: existing
