"""Tests for multi-file related_files in PatchSuggestion and PatchPlan."""

from pathlib import Path

from vibelign.core.patch_plan import PatchPlan
from vibelign.core.patch_suggester import (
    PatchSuggestion,
    _is_barrel_like,
    _classify_to_role,
    _build_related_file_entry,
    _filter_related_files,
    _infer_new_file_path,
)


# --- Task 1: PatchSuggestion.related_files ---


def test_patch_suggestion_has_related_files_default():
    suggestion = PatchSuggestion(
        request="test",
        target_file="src/App.tsx",
        target_anchor="APP",
        confidence="high",
        rationale=["test"],
    )
    assert suggestion.related_files == []


def test_patch_suggestion_has_related_files_explicit():
    suggestion = PatchSuggestion(
        request="test",
        target_file="src/App.tsx",
        target_anchor="APP",
        confidence="high",
        rationale=["test"],
        related_files=[],
    )
    assert suggestion.related_files == []


def test_patch_suggestion_to_dict_includes_related_files():
    suggestion = PatchSuggestion(
        request="test",
        target_file="a.tsx",
        target_anchor="A",
        confidence="high",
        rationale=[],
        related_files=[
            {
                "file": "b.tsx",
                "role": "data_source",
                "anchor": "B",
                "reason": "state owner",
                "exists": True,
            }
        ],
    )
    data = suggestion.to_dict()
    assert data["related_files"][0]["role"] == "data_source"
    assert data["related_files"][0]["file"] == "b.tsx"


# --- Task 0: PatchPlan.related_files ---


def test_patch_plan_has_related_files_default():
    plan = PatchPlan(
        schema_version=1,
        request="test",
        interpretation="test",
        target_file="src/App.tsx",
        target_anchor="APP",
    )
    assert plan.related_files == []


def test_patch_plan_to_dict_keeps_related_files_shape():
    plan = PatchPlan(
        schema_version=1,
        request="test",
        interpretation="test",
        target_file="src/App.tsx",
        target_anchor="APP",
        related_files=[
            {
                "file": "src/lib/vib.ts",
                "role": "data_source",
                "anchor": "VIB",
                "reason": "stream source",
                "exists": True,
            }
        ],
    )
    data = plan.to_dict()
    assert data["related_files"][0]["file"] == "src/lib/vib.ts"
    assert data["related_files"][0]["role"] == "data_source"
    assert data["related_files"][0]["exists"] is True


def test_patch_plan_empty_related_files_in_dict():
    plan = PatchPlan(
        schema_version=1,
        request="test",
        interpretation="test",
        target_file="a.py",
        target_anchor="A",
        related_files=[],
    )
    data = plan.to_dict()
    assert data["related_files"] == []


# --- Task 2: related_files helpers ---


def test_is_barrel_like_index_ts():
    assert _is_barrel_like(Path("src/index.ts")) is True


def test_is_barrel_like_init_py():
    assert _is_barrel_like(Path("vibelign/__init__.py")) is True


def test_is_barrel_like_normal_file():
    assert _is_barrel_like(Path("src/App.tsx")) is False


def test_classify_to_role_lib_path():
    assert _classify_to_role(None, "src/lib/vib.ts") == "data_source"


def test_classify_to_role_components_path():
    assert _classify_to_role(None, "src/components/Button.tsx") == "component"


def test_classify_to_role_ui_classify():
    assert _classify_to_role("ui", "src/pages/Home.tsx") == "component"


def test_classify_to_role_service_classify():
    assert _classify_to_role("service", "src/api/auth.py") == "data_source"


def test_classify_to_role_fallback():
    assert _classify_to_role(None, "src/utils/helper.py") == "utility"


def test_build_related_file_entry(tmp_path):
    f = tmp_path / "helper.py"
    f.write_text("def foo(): pass\n")
    entry = _build_related_file_entry(tmp_path, f, None)
    assert entry["file"] == "helper.py"
    assert entry["role"] == "utility"
    assert entry["anchor"] is None
    assert entry["exists"] is True


def test_build_related_file_entry_with_anchor(tmp_path):
    f = tmp_path / "helper.py"
    f.write_text("# === ANCHOR: HELPER_START ===\ndef foo(): pass\n# === ANCHOR: HELPER_END ===\n")
    entry = _build_related_file_entry(tmp_path, f, None)
    assert entry["anchor"] == "HELPER"


def test_filter_related_files_excludes_target(tmp_path):
    target = tmp_path / "App.tsx"
    target.write_text("import './lib'\n")
    lib = tmp_path / "lib.ts"
    lib.write_text("export const x = 1;\n")
    result = _filter_related_files(
        root=tmp_path, target_path=target, candidates=[target, lib], project_map=None,
    )
    assert len(result) == 1
    assert result[0]["file"] == "lib.ts"


def test_filter_related_files_excludes_barrel(tmp_path):
    target = tmp_path / "App.tsx"
    target.write_text("")
    index = tmp_path / "index.ts"
    index.write_text("")
    lib = tmp_path / "lib.ts"
    lib.write_text("")
    result = _filter_related_files(
        root=tmp_path, target_path=target,
        candidates=[index, lib], project_map=None,
    )
    assert len(result) == 1
    assert result[0]["file"] == "lib.ts"


def test_filter_related_files_max_3(tmp_path):
    target = tmp_path / "App.tsx"
    target.write_text("")
    candidates = []
    for i in range(5):
        f = tmp_path / f"mod{i}.ts"
        f.write_text("")
        candidates.append(f)
    result = _filter_related_files(
        root=tmp_path, target_path=target, candidates=candidates, project_map=None,
    )
    assert len(result) == 3


# --- Task 3: _infer_new_file_path ---


def test_infer_new_file_path_add(tmp_path):
    sibling_dir = tmp_path / "components"
    sibling_dir.mkdir()
    (sibling_dir / "Button.tsx").write_text("")
    result = _infer_new_file_path(
        root=tmp_path, subject="WatchLog", action="add", sibling_dir=sibling_dir,
    )
    assert result is not None
    assert result.name == "WatchLog.tsx"


def test_infer_new_file_path_lowercase_convention(tmp_path):
    sibling_dir = tmp_path / "utils"
    sibling_dir.mkdir()
    (sibling_dir / "helper.py").write_text("")
    result = _infer_new_file_path(
        root=tmp_path, subject="Parser", action="create", sibling_dir=sibling_dir,
    )
    assert result is not None
    assert result.name == "parser.py"


def test_infer_new_file_path_not_add(tmp_path):
    sibling_dir = tmp_path / "components"
    sibling_dir.mkdir()
    (sibling_dir / "Button.tsx").write_text("")
    result = _infer_new_file_path(
        root=tmp_path, subject="WatchLog", action="update", sibling_dir=sibling_dir,
    )
    assert result is None


def test_infer_new_file_path_already_exists(tmp_path):
    sibling_dir = tmp_path / "components"
    sibling_dir.mkdir()
    (sibling_dir / "Button.tsx").write_text("")
    (sibling_dir / "WatchLog.tsx").write_text("")
    result = _infer_new_file_path(
        root=tmp_path, subject="WatchLog", action="add", sibling_dir=sibling_dir,
    )
    assert result is None


def test_infer_new_file_path_empty_subject(tmp_path):
    sibling_dir = tmp_path / "components"
    sibling_dir.mkdir()
    (sibling_dir / "Button.tsx").write_text("")
    result = _infer_new_file_path(
        root=tmp_path, subject="", action="add", sibling_dir=sibling_dir,
    )
    assert result is None
