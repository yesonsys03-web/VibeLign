from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from vibelign.core.recovery.agent import (
    AgentConfig,
    LLMValidationError,
    RecommendationOutcome,
    build_recovery_context_packet,
    cache_key,
    compute_evidence_score,
    is_agent_enabled,
    load_cached_ranking,
    parse_time_window,
    pre_rank_candidates,
    recommend_candidates,
    store_cached_ranking,
    validate_llm_ranking,
)
from vibelign.core.recovery.models import (
    EvidenceScore,
    LLMConfidence,
    LLMRankingItem,
    LLMRankingResponse,
    RecoveryCandidate,
    RecoveryCandidateSource,
    RecoveryRecommendation,
)


def _candidate(candidate_id: str, source: str, created_at: str, **kwargs: object) -> RecoveryCandidate:
    commit_hash = kwargs.get("commit_hash")
    return RecoveryCandidate(
        candidate_id=candidate_id,
        source=cast(RecoveryCandidateSource, source),
        created_at=created_at,
        label=candidate_id,
        commit_hash=commit_hash if isinstance(commit_hash, str) else None,
        preview_available=bool(kwargs.get("preview_available", True)),
        changed_files_since_previous=tuple(cast(tuple[str, ...], kwargs.get("changed_files_since_previous", ()))),
        verification_nearby=cast(dict[str, str], kwargs.get("verification_nearby", {})),
    )


def test_recovery_candidate_and_recommendation_models() -> None:
    candidate = RecoveryCandidate(
        candidate_id="checkpoint:chk_1",
        source="manual_checkpoint",
        created_at="2026-05-04T10:00:00Z",
        label="manual save",
    )
    recommendation = RecoveryRecommendation(
        candidate=candidate,
        rank=1,
        evidence_score=EvidenceScore(protected_paths_clean=True),
    )

    assert recommendation.provider == "deterministic"
    assert recommendation.llm_confidence is None
    assert 0.0 <= recommendation.evidence_score.score() <= 1.0


def test_llm_response_models_default_to_no_apply() -> None:
    response = LLMRankingResponse(
        interpreted_goal="rollback",
        ranked=(
            LLMRankingItem(
                candidate_id="c1",
                rank=1,
                llm_confidence=LLMConfidence(level="high", reason="near failure"),
                reason="near failure",
            ),
        ),
    )

    assert response.should_apply is False
    assert response.should_write_memory is False


def test_parse_time_window_english_and_korean() -> None:
    now = datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc)
    english = parse_time_window("30m ago", now=now)
    korean = parse_time_window("30분 전", now=now)
    yesterday = parse_time_window("어제", now=now)
    before_commit = parse_time_window("before commit 813ccb4", now=now)

    assert english is not None and english.start is not None
    assert korean is not None and korean.start is not None
    assert yesterday is not None and yesterday.start is not None
    assert before_commit is not None
    assert english.start.isoformat().startswith("2026-05-04T11:30")
    assert korean.start.isoformat().startswith("2026-05-04T11:30")
    assert yesterday.start.date().isoformat() == "2026-05-03"
    assert before_commit.before_commit == "813ccb4"
    assert parse_time_window("whenever gui broke", now=now) is None


def test_pre_rank_prefers_time_commit_verification_then_recency() -> None:
    old_verified = _candidate(
        "old_verified",
        "manual_checkpoint",
        "2026-05-04T11:40:00Z",
        verification_nearby={"status": "passed"},
    )
    commit = _candidate("commit", "git_commit", "2026-05-04T11:35:00Z", commit_hash="abc")
    outside = _candidate("outside", "git_commit", "2026-05-04T08:00:00Z", commit_hash="def")
    window = parse_time_window("30m ago", now=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc))

    ranked = pre_rank_candidates([outside, old_verified, commit], time_window=window, top_n=2)

    assert [item.candidate_id for item in ranked] == ["commit", "old_verified"]


def test_compute_evidence_score_sets_expected_flags() -> None:
    candidate = _candidate(
        "c1",
        "git_commit",
        "2026-05-04T11:55:00Z",
        commit_hash="abc",
        changed_files_since_previous=("src/app.py",),
        verification_nearby={"status": "passed"},
    )
    window = parse_time_window("30m ago", now=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc))

    score = compute_evidence_score(candidate, time_window=window, protected_paths_clean=True)

    assert score.commit_boundary is True
    assert score.verification_fresh is True
    assert score.diff_small is True
    assert score.time_match_user_request is True


def test_context_packet_redacts_caps_and_hashes() -> None:
    candidate = RecoveryCandidate(
        candidate_id="c1",
        source="manual_checkpoint",
        created_at="2026-05-04T10:00:00Z",
        label="x" * 50_000,
        changed_files_since_previous=("secrets/api.key", "src/app.py"),
    )

    packet = build_recovery_context_packet("rollback", [candidate], None, ("secrets/*",))

    assert packet.truncated is True
    assert packet.byte_size <= packet.byte_cap
    assert packet.packet_hash
    redacted_paths = packet.candidates[0]["changed_files_since_previous"] if packet.candidates else []
    assert packet.candidates == [] or (isinstance(redacted_paths, list) and "<protected>" in redacted_paths)


def test_validate_llm_ranking_rejects_bad_candidate_and_forces_no_apply() -> None:
    raw: dict[str, object] = {
        "interpreted_goal": "rollback",
        "ranked_candidates": [
            {"candidate_id": "c1", "rank": 1, "confidence": "high", "reason": "x"},
        ],
        "uncertainties": [],
        "should_apply": True,
    }

    out = validate_llm_ranking(raw, allowed_ids={"c1"})
    assert out.should_apply is False

    raw["ranked_candidates"] = [{"candidate_id": "ghost", "rank": 1, "confidence": "high", "reason": "x"}]
    try:
        _ = validate_llm_ranking(raw, allowed_ids={"c1"})
    except LLMValidationError:
        pass
    else:
        raise AssertionError("expected LLMValidationError")


def test_cache_and_opt_in(tmp_path: Path) -> None:
    cfg = AgentConfig(cache_dir=tmp_path / "cache")
    key = cache_key(model_id="m", prompt_version="v1", schema_version="s", packet_hash="p")
    store_cached_ranking(cfg, key=key, raw={"x": 1})

    assert load_cached_ranking(cfg, key=key) is not None
    assert is_agent_enabled(tmp_path) is False
    _ = (tmp_path / "vibelign.toml").write_text("[agent.llm]\nenabled = true\n", encoding="utf-8")
    assert is_agent_enabled(tmp_path) is True


def test_recommend_candidates_deterministic_fallback(tmp_path: Path) -> None:
    candidates = [_candidate("c1", "git_commit", "2026-05-04T11:00:00Z", commit_hash="abc")]

    outcome = recommend_candidates(tmp_path, "rollback", candidates, provider=None, cfg=AgentConfig(tmp_path / "cache"))

    assert isinstance(outcome, RecommendationOutcome)
    assert outcome.provider == "deterministic"
    assert outcome.recommendations[0].llm_confidence is None
