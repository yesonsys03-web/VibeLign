# === ANCHOR: CHECKPOINT_ENGINE_SHADOW_RUNNER_START ===
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import shutil
import unicodedata
from typing import cast

from vibelign.core import local_checkpoints
from vibelign.core.checkpoint_engine.rust_engine import call_rust_engine, find_rust_engine


@dataclass(frozen=True)
class ShadowRunResult:
    enabled: bool
    operation: str
    reason: str
    payload: dict[str, object] | None = None


@dataclass(frozen=True)
class ShadowComparisonResult:
    enabled: bool
    matched: bool
    reason: str
    mismatches: list[str]
    python_file_count: int = 0
    rust_file_count: int = 0
    python_total_size_bytes: int = 0
    rust_total_size_bytes: int = 0


def prepare_shadow_run(
    root: Path, operation: str, payload: Mapping[str, object] | None = None
) -> ShadowRunResult:
    if os.environ.get("VIBELIGN_SHADOW_COMPARE", "").strip() != "1":
        return ShadowRunResult(
            enabled=False,
            operation=operation,
            reason="Rust shadow comparison is disabled. Set VIBELIGN_SHADOW_COMPARE=1 to enable.",
        )
    availability = find_rust_engine(root)
    if not availability.available:
        return ShadowRunResult(
            enabled=False,
            operation=operation,
            reason=availability.reason or "Rust checkpoint engine is unavailable.",
        )
    request = {"command": operation, **dict(payload or {})}
    result = call_rust_engine(root, request)
    if not result.ok:
        return ShadowRunResult(
            enabled=False,
            operation=operation,
            reason=result.error_message or result.error_code or "Rust shadow run failed.",
            payload=result.payload,
        )
    return ShadowRunResult(
        enabled=True,
        operation=operation,
        reason="Rust checkpoint shadow execution completed.",
        payload=result.payload,
    )


def compare_checkpoint_create(root: Path, message: str) -> ShadowComparisonResult:
    current_files = local_checkpoints.current_snapshot_file_map(root)
    python_keys = _python_comparison_keys(current_files)
    python_total = sum(_coerce_size(item.get("size")) for item in current_files.values())

    with TemporaryDirectory(prefix="vibelign-rust-shadow-") as tmp:
        shadow_root = Path(tmp)
        _copy_snapshot_inputs(root, shadow_root, current_files)
        result = prepare_shadow_run(
            shadow_root,
            "checkpoint_create",
            {"root": str(shadow_root), "message": message},
        )

    if not result.enabled or result.payload is None:
        return ShadowComparisonResult(
            enabled=False,
            matched=False,
            reason=result.reason,
            mismatches=[result.reason],
            python_file_count=len(python_keys),
            python_total_size_bytes=python_total,
        )

    rust_files = _rust_files(result.payload)
    rust_keys = _rust_comparison_keys(rust_files)
    rust_count = _coerce_size(result.payload.get("file_count"))
    rust_total = _coerce_size(result.payload.get("total_size_bytes"))
    mismatches = _compare_keys(python_keys, rust_keys)
    if len(python_keys) != rust_count:
        mismatches.append(
            f"file_count differs: python={len(python_keys)} rust={rust_count}"
        )
    if python_total != rust_total:
        mismatches.append(
            f"total_size_bytes differs: python={python_total} rust={rust_total}"
        )

    return ShadowComparisonResult(
        enabled=True,
        matched=not mismatches,
        reason="Rust shadow comparison completed.",
        mismatches=mismatches,
        python_file_count=len(python_keys),
        rust_file_count=len(rust_keys),
        python_total_size_bytes=python_total,
        rust_total_size_bytes=rust_total,
    )


def _copy_snapshot_inputs(
    source_root: Path, shadow_root: Path, files: Mapping[str, Mapping[str, object]]
) -> None:
    for rel in files:
        src = source_root / rel
        dst = shadow_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            _ = shutil.copy2(src, dst)
        except (FileNotFoundError, OSError):
            continue


def _normalize_path(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\\", "/"))


def _coerce_size(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _python_comparison_keys(
    files: Mapping[str, Mapping[str, object]]
) -> set[tuple[str, int]]:
    return {
        (_normalize_path(rel), _coerce_size(item.get("size")))
        for rel, item in files.items()
    }


def _rust_files(payload: Mapping[str, object]) -> list[dict[str, object]]:
    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        return []
    files: list[dict[str, object]] = []
    raw_items = cast(list[object], raw_files)
    for raw_item in raw_items:
        if isinstance(raw_item, dict):
            files.append(cast(dict[str, object], raw_item))
    return files


def _rust_comparison_keys(files: list[dict[str, object]]) -> set[tuple[str, int]]:
    keys: set[tuple[str, int]] = set()
    for item in files:
        rel = item.get("relative_path")
        if isinstance(rel, str):
            keys.add((_normalize_path(rel), _coerce_size(item.get("size"))))
    return keys


def _compare_keys(
    python_keys: set[tuple[str, int]], rust_keys: set[tuple[str, int]]
) -> list[str]:
    mismatches: list[str] = []
    missing = sorted(python_keys - rust_keys)
    extra = sorted(rust_keys - python_keys)
    if missing:
        mismatches.append(f"missing_in_rust={missing[:5]}")
    if extra:
        mismatches.append(f"extra_in_rust={extra[:5]}")
    return mismatches


# === ANCHOR: CHECKPOINT_ENGINE_SHADOW_RUNNER_END ===
