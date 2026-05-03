from vibelign.core.recovery.intent_zone import build_intent_zone


def test_empty_memory_falls_back_to_diff_aware_intent_zone() -> None:
    zone, drift = build_intent_zone(changed_paths=["src/app.py"])

    assert [entry.path for entry in zone] == ["src/app.py"]
    assert zone[0].source == "diff_fallback"
    assert drift == []


def test_file_outside_explicit_relevant_files_is_drift_candidate() -> None:
    zone, drift = build_intent_zone(
        explicit_relevant_paths=["src/ui.py"],
        changed_paths=["src/ui.py", "src/auth.py"],
    )

    assert [entry.path for entry in zone] == ["src/ui.py"]
    assert [candidate.path for candidate in drift] == ["src/auth.py"]
    assert drift[0].requires_user_review is True


def test_shared_anchor_intent_expands_intent_zone() -> None:
    zone, drift = build_intent_zone(
        explicit_relevant_paths=["src/ui.py"],
        changed_paths=["src/ui.py", "src/button.py", "src/auth.py"],
        anchor_intents_by_path={
            "src/ui.py": ["UI rendering"],
            "src/button.py": ["UI rendering"],
            "src/auth.py": ["Authentication"],
        },
    )

    assert [entry.path for entry in zone] == ["src/ui.py", "src/button.py"]
    assert zone[1].source == "anchor_co_occurrence"
    assert [candidate.path for candidate in drift] == ["src/auth.py"]
