# === ANCHOR: RECOVERY_AGENT_START ===
"""Recovery agent: deterministic pre-rank plus optional LLM advisory.

Slice A is recommend-only. This module never applies recovery operations.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import tomllib
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal, Protocol, cast

from vibelign.core.protected_files import get_protected
from vibelign.core.recovery.models import (
    EvidenceScore,
    LLMConfidence,
    LLMRankingItem,
    LLMRankingResponse,
    RecoveryCandidate,
    RecoveryRecommendation,
)

_RE_REL_MIN_EN = re.compile(r"^\s*(\d+)\s*m\s*ago\s*$", re.IGNORECASE)
_RE_REL_HR_EN = re.compile(r"^\s*(\d+)\s*h\s*ago\s*$", re.IGNORECASE)
_RE_REL_MIN_KO = re.compile(r"^\s*(\d+)\s*분\s*전\s*$")
_RE_REL_HR_KO = re.compile(r"^\s*(\d+)\s*시간\s*전\s*$")
_RE_BEFORE_COMMIT = re.compile(r"^\s*before\s+commit\s+([0-9a-fA-F]{4,40})\s*$", re.IGNORECASE)
_RE_SINCE_TAG = re.compile(r"^\s*since\s+([A-Za-z0-9._\-/]+)\s*$", re.IGNORECASE)
_RE_SINCE_ISO = re.compile(
    r"^\s*since\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+\-]\d{2}:?\d{2})?)\s*$",
    re.IGNORECASE,
)
_CONFIDENCE_LEVELS = {"high", "medium", "low"}
_DIFF_SMALL_FILE_LIMIT = 10
_PACKET_BYTE_CAP = 32 * 1024
_SCHEMA_VERSION = "recovery_packet_v1"
_PROMPT_VERSION = "v1"
_CACHE_FILENAME_PREFIX = "rec_"


@dataclass(frozen=True)
class TimeWindow:
    start: datetime | None = None
    end: datetime | None = None
    before_commit: str | None = None
    since_tag: str | None = None
    raw: str = ""


@dataclass(frozen=True)
class RecoveryContextPacket:
    user_phrase: str
    candidates: list[dict[str, object]]
    time_window: dict[str, str] | None
    schema_version: str
    packet_hash: str
    byte_size: int
    byte_cap: int
    truncated: bool


@dataclass(frozen=True)
class AgentConfig:
    cache_dir: Path = field(default_factory=lambda: Path(".vibelign/cache/agent"))
    timeout_seconds: float = 8.0
    cache_ttl_seconds: int = 86_400


@dataclass(frozen=True)
class CachedRanking:
    raw: dict[str, object]
    stored_at: float


@dataclass(frozen=True)
class RecommendationOutcome:
    recommendations: list[RecoveryRecommendation]
    provider: str
    interpreted_goal: str = ""
    fallback_reason: str | None = None


class LLMProvider(Protocol):
    def model_id(self) -> str: ...
    def prompt_version(self) -> str: ...
    def call(self, packet: RecoveryContextPacket) -> dict[str, object]: ...


class LLMValidationError(ValueError):
    pass


def parse_time_window(text: str, *, now: datetime | None = None) -> TimeWindow | None:
    if not text or not text.strip():
        return None
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    raw = text.strip()
    if (match := _RE_REL_MIN_EN.match(raw)) or (match := _RE_REL_MIN_KO.match(raw)):
        return TimeWindow(start=now - timedelta(minutes=int(match.group(1))), end=now, raw=raw)
    if (match := _RE_REL_HR_EN.match(raw)) or (match := _RE_REL_HR_KO.match(raw)):
        return TimeWindow(start=now - timedelta(hours=int(match.group(1))), end=now, raw=raw)
    lowered = raw.lower()
    if lowered in {"yesterday", "어제"}:
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return TimeWindow(start=start, end=start + timedelta(days=1), raw=raw)
    if lowered in {"today", "오늘"}:
        return TimeWindow(start=now.replace(hour=0, minute=0, second=0, microsecond=0), end=now, raw=raw)
    if lowered in {"just now", "방금 전", "방금"}:
        return TimeWindow(start=now - timedelta(minutes=5), end=now, raw=raw)
    if match := _RE_BEFORE_COMMIT.match(raw):
        return TimeWindow(before_commit=match.group(1), raw=raw)
    if match := _RE_SINCE_ISO.match(raw):
        try:
            return TimeWindow(
                start=datetime.fromisoformat(match.group(1).replace("Z", "+00:00")).astimezone(timezone.utc),
                raw=raw,
            )
        except ValueError:
            return None
    if match := _RE_SINCE_TAG.match(raw):
        return TimeWindow(since_tag=match.group(1), raw=raw)
    return None


def pre_rank_candidates(
    candidates: list[RecoveryCandidate],
    *,
    time_window: TimeWindow | None,
    top_n: int = 20,
) -> list[RecoveryCandidate]:
    def bucket(candidate: RecoveryCandidate) -> tuple[int, int, int]:
        return (
            0 if _candidate_in_window(candidate, time_window) else 1,
            0 if _is_commit_boundary(candidate) else 1,
            0 if _has_verification(candidate) else 1,
        )

    return sorted(candidates, key=lambda candidate: (*bucket(candidate), _reverse_iso(candidate.created_at)))[:top_n]


def compute_evidence_score(
    candidate: RecoveryCandidate,
    *,
    time_window: TimeWindow | None,
    protected_paths_clean: bool,
    verification_fresh: bool | None = None,
) -> EvidenceScore:
    if verification_fresh is None:
        status = (candidate.verification_nearby or {}).get("status")
        verification_fresh = bool(status) and status not in {"unknown", "stale"}
    return EvidenceScore(
        commit_boundary=_is_commit_boundary(candidate),
        verification_fresh=verification_fresh,
        diff_small=0 < len(candidate.changed_files_since_previous) <= _DIFF_SMALL_FILE_LIMIT,
        protected_paths_clean=protected_paths_clean,
        time_match_user_request=_candidate_in_window(candidate, time_window) if time_window else False,
        formula_version="v1",
    )


def build_recovery_context_packet(
    user_phrase: str,
    candidates: list[RecoveryCandidate],
    time_window: TimeWindow | None,
    protected_globs: tuple[str, ...],
    *,
    byte_cap: int = _PACKET_BYTE_CAP,
) -> RecoveryContextPacket:
    payload_candidates = [_candidate_payload(candidate, protected_globs) for candidate in candidates]
    raw: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "user_phrase": unicodedata.normalize("NFC", user_phrase),
        "time_window": _time_window_payload(time_window),
        "candidates": payload_candidates,
    }
    serialized = _json_dump(raw)
    truncated = False
    while len(serialized.encode("utf-8")) > byte_cap and payload_candidates:
        truncated = True
        _ = payload_candidates.pop()
        raw = {**raw, "candidates": payload_candidates, "truncated": True}
        serialized = _json_dump(raw)
    encoded = serialized.encode("utf-8")
    return RecoveryContextPacket(
        user_phrase=str(raw["user_phrase"]),
        candidates=payload_candidates,
        time_window=_time_window_payload(time_window),
        schema_version=_SCHEMA_VERSION,
        packet_hash=hashlib.sha256(encoded).hexdigest(),
        byte_size=len(encoded),
        byte_cap=byte_cap,
        truncated=truncated,
    )


def validate_llm_ranking(raw: dict[str, object], *, allowed_ids: set[str]) -> LLMRankingResponse:
    ranked_raw = raw.get("ranked_candidates")
    if not isinstance(ranked_raw, list) or not ranked_raw:
        raise LLMValidationError("ranked_candidates must be a non-empty list")
    ranked_entries = cast(list[object], ranked_raw)
    items = [_ranking_item(entry, allowed_ids) for entry in ranked_entries]
    uncertainties = raw.get("uncertainties") or []
    if not isinstance(uncertainties, list) or not all(isinstance(item, str) for item in uncertainties):
        raise LLMValidationError("uncertainties must be list[str]")
    interpreted_goal = raw.get("interpreted_goal", "")
    if not isinstance(interpreted_goal, str):
        raise LLMValidationError("interpreted_goal must be a string")
    return LLMRankingResponse(
        interpreted_goal=interpreted_goal,
        ranked=tuple(sorted(items, key=lambda item: item.rank)),
        uncertainties=tuple(cast(list[str], uncertainties)),
        should_apply=False,
        should_write_memory=False,
    )


def cache_key(*, model_id: str, prompt_version: str, schema_version: str, packet_hash: str) -> str:
    raw = f"{model_id}|{prompt_version}|{schema_version}|{packet_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def store_cached_ranking(cfg: AgentConfig, *, key: str, raw: dict[str, object]) -> None:
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {"stored_at": time.time(), "raw": raw}
    _ = (cfg.cache_dir / f"{_CACHE_FILENAME_PREFIX}{key}.json").write_text(_json_dump(payload), encoding="utf-8")


def load_cached_ranking(cfg: AgentConfig, *, key: str, ttl_seconds: int | None = None) -> CachedRanking | None:
    ttl = cfg.cache_ttl_seconds if ttl_seconds is None else ttl_seconds
    path = cfg.cache_dir / f"{_CACHE_FILENAME_PREFIX}{key}.json"
    if not path.exists():
        return None
    try:
        data = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None
    stored_value = cast(dict[str, object], data).get("stored_at", 0) if isinstance(data, dict) else 0
    stored_at = float(stored_value) if isinstance(stored_value, int | float | str) else 0.0
    if time.time() - stored_at >= ttl:
        return None
    raw = cast(dict[str, object], data).get("raw") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return None
    return CachedRanking(raw=cast(dict[str, object], raw), stored_at=stored_at)


def is_agent_enabled(project_root: Path) -> bool:
    config_path = project_root / "vibelign.toml"
    if not config_path.exists():
        return False
    try:
        data = cast(dict[str, object], tomllib.loads(config_path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    agent = data.get("agent")
    llm = cast(dict[str, object], agent).get("llm") if isinstance(agent, dict) else None
    return bool(cast(dict[str, object], llm).get("enabled")) if isinstance(llm, dict) else False


def recommend_candidates(
    project_root: Path,
    user_phrase: str,
    candidates: list[RecoveryCandidate],
    provider: LLMProvider | None,
    cfg: AgentConfig,
) -> RecommendationOutcome:
    time_window = parse_time_window(user_phrase)
    pre_ranked = pre_rank_candidates(candidates, time_window=time_window)
    protected_globs = tuple(get_protected(project_root))
    protected_clean = _protected_paths_clean(pre_ranked, protected_globs)
    if provider is None or not is_agent_enabled(project_root):
        return _deterministic_outcome(pre_ranked, time_window, protected_clean, None)
    packet = build_recovery_context_packet(user_phrase, pre_ranked, time_window, protected_globs)
    key = cache_key(
        model_id=provider.model_id(),
        prompt_version=provider.prompt_version() or _PROMPT_VERSION,
        schema_version=packet.schema_version,
        packet_hash=packet.packet_hash,
    )
    cached = load_cached_ranking(cfg, key=key)
    used_cache = cached is not None
    try:
        raw = cached.raw if cached else provider.call(packet)
        validated = validate_llm_ranking(raw, allowed_ids={candidate.candidate_id for candidate in pre_ranked})
    except TimeoutError:
        return _deterministic_outcome(pre_ranked, time_window, protected_clean, "llm timeout")
    except LLMValidationError as exc:
        return _deterministic_outcome(pre_ranked, time_window, protected_clean, f"llm validation failed: {exc}")
    except Exception as exc:
        return _deterministic_outcome(pre_ranked, time_window, protected_clean, f"llm error: {type(exc).__name__}")
    if not used_cache:
        store_cached_ranking(cfg, key=key, raw=raw)
    by_id = {candidate.candidate_id: candidate for candidate in pre_ranked}
    recommendations = [
        RecoveryRecommendation(
            candidate=by_id[item.candidate_id],
            rank=item.rank,
            evidence_score=compute_evidence_score(
                by_id[item.candidate_id],
                time_window=time_window,
                protected_paths_clean=protected_clean,
            ),
            llm_confidence=item.llm_confidence,
            reason=item.reason,
            expected_loss=item.expected_loss,
            provider="cache" if used_cache else "llm",
        )
        for item in validated.ranked
    ]
    return RecommendationOutcome(
        recommendations=recommendations,
        provider="cache" if used_cache else "llm",
        interpreted_goal=validated.interpreted_goal,
    )


def _deterministic_outcome(
    candidates: list[RecoveryCandidate],
    time_window: TimeWindow | None,
    protected_clean: bool,
    fallback_reason: str | None,
) -> RecommendationOutcome:
    return RecommendationOutcome(
        recommendations=[
            RecoveryRecommendation(
                candidate=candidate,
                rank=index,
                evidence_score=compute_evidence_score(
                    candidate,
                    time_window=time_window,
                    protected_paths_clean=protected_clean,
                ),
                reason="deterministic ranking",
                provider="deterministic",
            )
            for index, candidate in enumerate(candidates, start=1)
        ],
        provider="deterministic",
        fallback_reason=fallback_reason,
    )


def _candidate_in_window(candidate: RecoveryCandidate, time_window: TimeWindow | None) -> bool:
    if time_window is None:
        return True
    if time_window.before_commit is not None:
        return bool(candidate.commit_hash and candidate.commit_hash.startswith(time_window.before_commit))
    if time_window.since_tag is not None:
        return True
    try:
        created_at = datetime.fromisoformat(candidate.created_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if time_window.start and created_at < time_window.start:
        return False
    if time_window.end and created_at > time_window.end:
        return False
    return True


def _is_commit_boundary(candidate: RecoveryCandidate) -> bool:
    return candidate.source in {"post_commit_checkpoint", "git_commit"} and bool(candidate.commit_hash)


def _has_verification(candidate: RecoveryCandidate) -> bool:
    status = (candidate.verification_nearby or {}).get("status")
    return bool(status) and status != "unknown"


def _reverse_iso(value: str) -> str:
    return "".join(chr(255 - ord(char)) for char in value)


def _candidate_payload(candidate: RecoveryCandidate, protected_globs: tuple[str, ...]) -> dict[str, object]:
    payload = asdict(candidate)
    payload["changed_files_since_previous"] = [
        _redact_path(path, protected_globs) for path in candidate.changed_files_since_previous
    ]
    return payload


def _redact_path(path: str, protected_globs: tuple[str, ...]) -> str:
    normalized = unicodedata.normalize("NFC", path.replace("\\", "/"))
    for glob in protected_globs:
        if fnmatch(normalized, glob) or normalized == glob or normalized.startswith(glob.rstrip("/") + "/"):
            return "<protected>"
    return normalized


def _time_window_payload(time_window: TimeWindow | None) -> dict[str, str] | None:
    if time_window is None:
        return None
    payload: dict[str, str] = {}
    if time_window.start:
        payload["start"] = time_window.start.isoformat()
    if time_window.end:
        payload["end"] = time_window.end.isoformat()
    if time_window.before_commit:
        payload["before_commit"] = time_window.before_commit
    if time_window.since_tag:
        payload["since_tag"] = time_window.since_tag
    return payload


def _ranking_item(entry: object, allowed_ids: set[str]) -> LLMRankingItem:
    if not isinstance(entry, dict):
        raise LLMValidationError("each ranked entry must be a JSON object")
    entry_dict = cast(dict[str, object], entry)
    candidate_id = entry_dict.get("candidate_id")
    if not isinstance(candidate_id, str) or candidate_id not in allowed_ids:
        raise LLMValidationError(f"unknown candidate_id: {candidate_id!r}")
    rank = entry_dict.get("rank")
    if not isinstance(rank, int) or rank < 1:
        raise LLMValidationError("rank must be a positive int")
    confidence = entry_dict.get("confidence")
    if confidence not in _CONFIDENCE_LEVELS:
        raise LLMValidationError("confidence must be high, medium, or low")
    reason = entry_dict.get("reason", "")
    if not isinstance(reason, str):
        raise LLMValidationError("reason must be a string")
    expected_loss = entry_dict.get("expected_loss") or []
    expected_loss_items = cast(list[object], expected_loss) if isinstance(expected_loss, list) else []
    if not isinstance(expected_loss, list) or not all(isinstance(item, str) for item in expected_loss_items):
        raise LLMValidationError("expected_loss must be list[str]")
    action = entry_dict.get("recommended_action_type", "preview_file_restore")
    if not isinstance(action, str):
        raise LLMValidationError("recommended_action_type must be a string")
    return LLMRankingItem(
        candidate_id=candidate_id,
        rank=rank,
        llm_confidence=LLMConfidence(level=cast(Literal["high", "medium", "low"], confidence), reason=reason),
        reason=reason,
        expected_loss=tuple(cast(list[str], expected_loss_items)),
        recommended_action_type=action,
        requires_user_confirmation=entry_dict.get("requires_user_confirmation") is not False,
    )


def _protected_paths_clean(candidates: list[RecoveryCandidate], protected_globs: tuple[str, ...]) -> bool:
    for candidate in candidates:
        for path in candidate.changed_files_since_previous:
            if _redact_path(path, protected_globs) == "<protected>":
                return False
    return True


def _json_dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

# === ANCHOR: RECOVERY_AGENT_END ===
