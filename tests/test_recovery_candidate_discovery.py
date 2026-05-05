from __future__ import annotations

from pathlib import Path

from vibelign.core.recovery.signals import collect_recovery_candidates


def test_collect_returns_list_even_when_empty(tmp_path: Path) -> None:
    assert collect_recovery_candidates(tmp_path) == []


def test_collect_includes_manual_checkpoints(tmp_path: Path, monkeypatch) -> None:
    from vibelign.core.recovery import signals as signals_mod

    monkeypatch.setattr(
        signals_mod,
        "_iter_manual_checkpoints",
        lambda root: [{"checkpoint_id": "chk_manual", "created_at": "2026-05-04T09:00:00Z", "message": "manual"}],
    )
    monkeypatch.setattr(signals_mod, "_iter_auto_backup_checkpoints", lambda root: [])
    monkeypatch.setattr(signals_mod, "_iter_recent_git_commits", lambda root, limit: [])

    candidates = collect_recovery_candidates(tmp_path)

    assert candidates[0].candidate_id == "checkpoint:chk_manual"
    assert candidates[0].source == "manual_checkpoint"


def test_collect_deduplicates_auto_backup_and_commit(tmp_path: Path, monkeypatch) -> None:
    from vibelign.core.recovery import signals as signals_mod

    monkeypatch.setattr(signals_mod, "_iter_manual_checkpoints", lambda root: [])
    monkeypatch.setattr(
        signals_mod,
        "_iter_auto_backup_checkpoints",
        lambda root: [
            {
                "checkpoint_id": "chk_auto",
                "created_at": "2026-05-04T10:00:00Z",
                "message": "auto",
                "commit_hash": "abc123",
            }
        ],
    )
    monkeypatch.setattr(
        signals_mod,
        "_iter_recent_git_commits",
        lambda root, limit: [{"commit_hash": "abc123", "created_at": "2026-05-04T11:00:00Z", "message": "commit"}],
    )

    candidates = collect_recovery_candidates(tmp_path)

    assert [candidate.source for candidate in candidates] == ["post_commit_checkpoint"]


def test_collect_candidate_ids_are_unique(tmp_path: Path, monkeypatch) -> None:
    from vibelign.core.recovery import signals as signals_mod

    monkeypatch.setattr(signals_mod, "_iter_manual_checkpoints", lambda root: [])
    monkeypatch.setattr(signals_mod, "_iter_auto_backup_checkpoints", lambda root: [])
    monkeypatch.setattr(
        signals_mod,
        "_iter_recent_git_commits",
        lambda root, limit: [
            {"commit_hash": "abc123", "created_at": "2026-05-04T11:00:00Z", "message": "one"},
            {"commit_hash": "abc123", "created_at": "2026-05-04T11:01:00Z", "message": "two"},
        ],
    )

    ids = [candidate.candidate_id for candidate in collect_recovery_candidates(tmp_path)]

    assert len(ids) == len(set(ids))
