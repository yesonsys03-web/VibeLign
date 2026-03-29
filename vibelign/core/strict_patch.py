# === ANCHOR: STRICT_PATCH_START ===
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from vibelign.core.anchor_tools import extract_anchor_line_ranges
from vibelign.core.local_checkpoints import create_checkpoint
from vibelign.core.patch_validation import (
    ERR_STRICT_ANCHOR_READ_FAIL,
    ERR_STRICT_FILE_NOT_FOUND,
    ERR_STRICT_FILE_READ,
    ERR_STRICT_MARKER_DRIFT,
    ERR_STRICT_MARKER_MISSING,
    ERR_STRICT_MISSING_FIELDS,
    ERR_STRICT_OP_SHAPE,
    ERR_STRICT_OPS_EMPTY,
    ERR_STRICT_PATH_TRAVERSAL,
    ERR_STRICT_PLACEHOLDER_REPLACE,
    ERR_STRICT_SEARCH_MISMATCH,
    ERR_STRICT_SEARCH_NOT_UNIQUE,
    err_strict_search_too_short,
    search_block_meets_min_lines,
)


STRICT_PATCH_REPLACE_PLACEHOLDER = "[REPLACE_WITH_UPDATED_BLOCK_KEEPING_ANCHOR_MARKERS]"


@dataclass
# === ANCHOR: STRICT_PATCH_STRICTPATCHOPERATION_START ===
class StrictPatchOperation:
    ordinal: int
    target_file: str
    target_anchor: str
    operation: str
    search: str
    replace: str
    search_match_count: int
    search_ready: bool
# === ANCHOR: STRICT_PATCH_STRICTPATCHOPERATION_END ===


@dataclass
# === ANCHOR: STRICT_PATCH_STRICTPATCHARTIFACT_START ===
class StrictPatchArtifact:
    schema_version: int
    generator_version: str
    status: str
    apply_ready: bool
    placeholder_replace: bool
    operations: list[StrictPatchOperation] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)

    # === ANCHOR: STRICT_PATCH_TO_DICT_START ===
    def to_dict(self) -> dict[str, Any]:
# === ANCHOR: STRICT_PATCH_STRICTPATCHARTIFACT_END ===
        return asdict(self)
    # === ANCHOR: STRICT_PATCH_TO_DICT_END ===


# === ANCHOR: STRICT_PATCH__COERCE_ORDINAL_START ===
def _coerce_ordinal(value: object) -> int:
    return value if isinstance(value, int) else 0
# === ANCHOR: STRICT_PATCH__COERCE_ORDINAL_END ===


# === ANCHOR: STRICT_PATCH__RESOLVE_TARGET_PATH_START ===
def _resolve_target_path(root: Path, target_file: str) -> Path | None:
    if not target_file:
        return None
    candidate = Path(target_file)
    if candidate.is_absolute():
        return None
    resolved_root = root.resolve()
    resolved_target = (root / candidate).resolve()
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved_target
# === ANCHOR: STRICT_PATCH__RESOLVE_TARGET_PATH_END ===


# === ANCHOR: STRICT_PATCH__ANCHOR_MARKERS_START ===
def _anchor_markers(block: str) -> tuple[str, str] | None:
    lines = block.splitlines()
    if len(lines) < 2:
        return None
    start_line = lines[0].strip()
    end_line = lines[-1].strip()
    if "ANCHOR:" not in start_line or "_START" not in start_line:
        return None
    if "ANCHOR:" not in end_line or "_END" not in end_line:
        return None
    return start_line, end_line
# === ANCHOR: STRICT_PATCH__ANCHOR_MARKERS_END ===


# === ANCHOR: STRICT_PATCH__COUNT_EXACT_MATCHES_START ===
def _count_exact_matches(text: str, search: str) -> int:
    if not search:
        return 0
    return text.count(search)
# === ANCHOR: STRICT_PATCH__COUNT_EXACT_MATCHES_END ===


# === ANCHOR: STRICT_PATCH__READ_ANCHOR_BLOCK_START ===
def _read_anchor_block(path: Path, anchor_name: str) -> str | None:
    if not anchor_name or not path.exists():
        return None
    line_ranges = extract_anchor_line_ranges(path)
    if anchor_name not in line_ranges:
        return None
    start, end = line_ranges[anchor_name]
    try:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError:
        return None
    if start < 1 or end < start:
        return None
    block = "".join(lines[start - 1 : end])
    return block or None
# === ANCHOR: STRICT_PATCH__READ_ANCHOR_BLOCK_END ===


# === ANCHOR: STRICT_PATCH__OPERATIONS_FROM_ANCHOR_REGIONS_START ===
def _operations_from_anchor_regions(
    root: Path,
    regions: list[tuple[str, str, int]],
# === ANCHOR: STRICT_PATCH__OPERATIONS_FROM_ANCHOR_REGIONS_END ===
) -> list[StrictPatchOperation] | None:
    operations: list[StrictPatchOperation] = []
    for target_file, target_anchor, ordinal in regions:
        if not target_file or not target_anchor:
            return None
        search = _read_anchor_block(root / target_file, target_anchor)
        if search is None:
            return None
        try:
            file_text = (root / target_file).read_text(encoding="utf-8")
        except OSError:
            return None
        search_match_count = _count_exact_matches(file_text, search)
        line_ok = search_block_meets_min_lines(search)
        unique_ok = search_match_count == 1
        search_ready = line_ok and unique_ok
        operations.append(
            StrictPatchOperation(
                ordinal=ordinal,
                target_file=target_file,
                target_anchor=target_anchor,
                operation="replace_range",
                search=search,
                replace=STRICT_PATCH_REPLACE_PLACEHOLDER,
                search_match_count=search_match_count,
                search_ready=search_ready,
            )
        )
    return operations


# === ANCHOR: STRICT_PATCH_BUILD_STRICT_PATCH_ARTIFACT_START ===
def build_strict_patch_artifact(
    root: Path,
    patch_plan: dict[str, object],
    contract: dict[str, object],
# === ANCHOR: STRICT_PATCH_BUILD_STRICT_PATCH_ARTIFACT_END ===
) -> dict[str, Any] | None:
    if str(contract.get("status")) != "READY":
        return None

    patch_points = cast(dict[str, object], patch_plan.get("patch_points", {}))
    operation = str(patch_points.get("operation", "update"))
    if operation == "move":
        src_file = str(patch_plan.get("target_file", ""))
        src_anchor = str(patch_plan.get("target_anchor", ""))
        dst_file = str(patch_plan.get("destination_target_file") or "")
        dst_anchor = str(patch_plan.get("destination_target_anchor") or "")
        if not src_file or not src_anchor or not dst_file or not dst_anchor:
            return None
        operations = _operations_from_anchor_regions(
            root,
            [(src_file, src_anchor, 0), (dst_file, dst_anchor, 1)],
        )
        if operations is None:
            return None
        move_notes = [
            "move: ordinal 0 = source 앵커 블록(잘라낸 뒤 내용을 비우거나 플레이스홀더로 채움), "
            "ordinal 1 = destination 앵커 블록(이동할 내용을 합친 최종 블록).",
            "두 replace 모두 anchor START/END 줄을 유지해야 합니다.",
        ]
        extra_notes: list[str] = []
        if any(not search_block_meets_min_lines(op.search) for op in operations):
            extra_notes.append(
                err_strict_search_too_short(
                    min(len(op.search.splitlines()) for op in operations)
                )
            )
        artifact = StrictPatchArtifact(
            schema_version=1,
            generator_version="0.2",
            status="READY"
            if all(op.search_ready for op in operations)
            else "NEEDS_CLARIFICATION",
            apply_ready=False,
            placeholder_replace=True,
            operations=operations,
            instructions=[
                "Replace each `replace` placeholder with the final updated block.",
                "Keep the anchor marker lines inside the replacement block.",
                "Do not change `target_file`, `target_anchor`, or `search`.",
                "Auto-apply is allowed only when every SEARCH block matches exactly once.",
                *move_notes,
                *extra_notes,
            ],
        )
        return artifact.to_dict()

    raw_steps = patch_plan.get("steps", [])
    step_dicts = (
        [cast(dict[str, object], item) for item in cast(list[object], raw_steps)]
        if isinstance(raw_steps, list)
        else []
    )
    ready_steps = [step for step in step_dicts if str(step.get("status")) == "READY"]
    if not ready_steps:
        return None

    regions: list[tuple[str, str, int]] = []
    for step in ready_steps:
        target_file = str(step.get("target_file", ""))
        target_anchor = str(step.get("target_anchor", ""))
        regions.append(
            (target_file, target_anchor, _coerce_ordinal(step.get("ordinal", 0)))
        )
    operations = _operations_from_anchor_regions(root, regions)
    if operations is None:
        return None
    for step, op in zip(ready_steps, operations, strict=True):
        allowed_raw = cast(list[object], step.get("allowed_ops", ["replace_range"]))
        op.operation = (
            str(allowed_raw[0]) if allowed_raw else "replace_range"
        )

    extra_notes: list[str] = []
    if any(not search_block_meets_min_lines(op.search) for op in operations):
        extra_notes.append(
            err_strict_search_too_short(
                min(len(op.search.splitlines()) for op in operations)
            )
        )
    artifact = StrictPatchArtifact(
        schema_version=1,
        generator_version="0.1",
        status="READY"
        if all(op.search_ready for op in operations)
        else "NEEDS_CLARIFICATION",
        apply_ready=False,
        placeholder_replace=True,
        operations=operations,
        instructions=[
            "Replace each `replace` placeholder with the final updated block.",
            "Keep the anchor marker lines inside the replacement block.",
            "Do not change `target_file`, `target_anchor`, or `search`.",
            "Auto-apply is allowed only when every SEARCH block matches exactly once.",
            *extra_notes,
        ],
    )
    return artifact.to_dict()


# === ANCHOR: STRICT_PATCH_APPLY_STRICT_PATCH_START ===
def apply_strict_patch(
    root: Path,
    strict_patch: dict[str, object],
    *,
    dry_run: bool = False,
# === ANCHOR: STRICT_PATCH_APPLY_STRICT_PATCH_END ===
) -> dict[str, Any]:
    raw_operations = strict_patch.get("operations", [])
    if not isinstance(raw_operations, list) or not raw_operations:
        return {
            "ok": False,
            "error": ERR_STRICT_OPS_EMPTY,
        }

    staged_contents: dict[Path, str] = {}
    touched_files: list[str] = []

    for raw_operation in raw_operations:
        if not isinstance(raw_operation, dict):
            return {
                "ok": False,
                "error": ERR_STRICT_OP_SHAPE,
            }
        target_file = str(raw_operation.get("target_file", ""))
        target_anchor = str(raw_operation.get("target_anchor", ""))
        search = str(raw_operation.get("search", ""))
        replace = str(raw_operation.get("replace", ""))
        if not target_file or not target_anchor or not search:
            return {
                "ok": False,
                "error": ERR_STRICT_MISSING_FIELDS,
            }
        if not replace or STRICT_PATCH_REPLACE_PLACEHOLDER in replace:
            return {
                "ok": False,
                "error": ERR_STRICT_PLACEHOLDER_REPLACE,
            }
        if not search_block_meets_min_lines(search):
            return {
                "ok": False,
                "error": err_strict_search_too_short(len(search.splitlines())),
            }
        target_path = _resolve_target_path(root, target_file)
        if target_path is None:
            return {
                "ok": False,
                "error": ERR_STRICT_PATH_TRAVERSAL.format(target_file=target_file),
            }
        if not target_path.exists():
            return {
                "ok": False,
                "error": ERR_STRICT_FILE_NOT_FOUND.format(target_file=target_file),
            }
        current_anchor_block = _read_anchor_block(target_path, target_anchor)
        if current_anchor_block is None:
            return {
                "ok": False,
                "error": ERR_STRICT_ANCHOR_READ_FAIL.format(
                    target_anchor=target_anchor, target_file=target_file
                ),
            }
        if current_anchor_block != search:
            return {
                "ok": False,
                "error": ERR_STRICT_SEARCH_MISMATCH.format(
                    target_file=target_file, target_anchor=target_anchor
                ),
            }
        search_markers = _anchor_markers(search)
        replace_markers = _anchor_markers(replace)
        if search_markers is None or replace_markers is None:
            return {
                "ok": False,
                "error": ERR_STRICT_MARKER_MISSING,
            }
        if search_markers != replace_markers:
            return {
                "ok": False,
                "error": ERR_STRICT_MARKER_DRIFT,
            }
        current_text = staged_contents.get(target_path)
        if current_text is None:
            try:
                current_text = target_path.read_text(encoding="utf-8")
            except OSError:
                return {
                    "ok": False,
                    "error": ERR_STRICT_FILE_READ.format(target_file=target_file),
                }
        match_count = _count_exact_matches(current_text, search)
        if match_count != 1:
            return {
                "ok": False,
                "error": ERR_STRICT_SEARCH_NOT_UNIQUE.format(
                    target_file=target_file, match_count=match_count
                ),
            }
        staged_contents[target_path] = current_text.replace(search, replace, 1)
        if target_file not in touched_files:
            touched_files.append(target_file)

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "checkpoint_id": None,
            "applied_files": touched_files,
            "applied_operation_count": len(raw_operations),
        }

    checkpoint = create_checkpoint(
        root,
        f"vibelign: strict patch apply ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
    )

    for path, updated_text in staged_contents.items():
        path.write_text(updated_text, encoding="utf-8")

    return {
        "ok": True,
        "dry_run": False,
        "checkpoint_id": checkpoint.checkpoint_id if checkpoint else None,
        "applied_files": touched_files,
        "applied_operation_count": len(raw_operations),
    }
# === ANCHOR: STRICT_PATCH_END ===
