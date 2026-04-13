"""Tests for multi-file contract scope: allowed_file_details, preconditions."""

from vibelign.patch.patch_contract_helpers import build_contract, preconditions


def _make_patch_plan(**overrides):
    base = {
        "target_file": "src/App.tsx",
        "target_anchor": "APP",
        "confidence": "high",
        "interpretation": "로그 뷰어 추가",
        "codespeak": "ui.component.watch_log.add",
        "codespeak_generated": True,
        "patch_points": {"operation": "add"},
        "related_files": [],
        "request": "로그 뷰어 추가",
    }
    base.update(overrides)
    return base


# --- preconditions ---


def test_preconditions_single_file():
    result = preconditions("src/App.tsx", "APP")
    assert any("하나뿐" in c for c in result)


def test_preconditions_multi_file():
    related = [
        {"file": "src/lib/vib.ts", "role": "data_source", "anchor": "VIB", "reason": "stream", "exists": True},
    ]
    result = preconditions("src/App.tsx", "APP", related_files=related)
    assert any("총 2개" in c for c in result)
    assert any("vib.ts" in c for c in result)


def test_preconditions_new_file():
    related = [
        {"file": "src/components/WatchLog.tsx", "role": "new_file", "anchor": None, "reason": "컨벤션 추론", "exists": False},
    ]
    result = preconditions("src/App.tsx", "APP", related_files=related)
    assert any("새로 생성될 파일" in c for c in result)
    assert any("WatchLog" in c for c in result)


# --- build_contract ---


def test_contract_keeps_allowed_files_legacy_list():
    plan = _make_patch_plan(
        related_files=[
            {"file": "src/lib/vib.ts", "role": "data_source", "anchor": "VIB", "reason": "stream", "exists": True},
        ]
    )
    result = build_contract(plan)
    scope = result["scope"]
    assert "src/App.tsx" in scope["allowed_files"]
    assert "src/lib/vib.ts" in scope["allowed_files"]


def test_contract_has_allowed_file_details():
    plan = _make_patch_plan(
        related_files=[
            {"file": "src/lib/vib.ts", "role": "data_source", "anchor": "VIB", "reason": "stream", "exists": True},
        ]
    )
    result = build_contract(plan)
    scope = result["scope"]
    details = scope["allowed_file_details"]
    assert details[0]["role"] == "primary"
    assert details[0]["file"] == "src/App.tsx"
    assert details[1]["role"] == "data_source"
    assert details[1]["file"] == "src/lib/vib.ts"


def test_contract_single_file_has_empty_details():
    plan = _make_patch_plan(related_files=[])
    result = build_contract(plan)
    scope = result["scope"]
    # Even single-file has primary detail
    details = scope["allowed_file_details"]
    assert len(details) == 1
    assert details[0]["role"] == "primary"


def test_contract_no_related_files_key():
    plan = _make_patch_plan()
    del plan["related_files"]
    result = build_contract(plan)
    scope = result["scope"]
    assert "allowed_file_details" in scope
    details = scope["allowed_file_details"]
    assert len(details) == 1


def test_contract_new_file_in_details():
    plan = _make_patch_plan(
        related_files=[
            {"file": "src/components/WatchLog.tsx", "role": "new_file", "anchor": None, "reason": "new", "exists": False},
        ]
    )
    result = build_contract(plan)
    scope = result["scope"]
    details = scope["allowed_file_details"]
    new_entries = [d for d in details if d.get("role") == "new_file"]
    assert len(new_entries) == 1
    assert new_entries[0]["exists"] is False
