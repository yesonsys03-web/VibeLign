# === ANCHOR: PATCH_VALIDATION_START ===
"""Strict patch 검증 메시지·휴리스틱 (patch_upgrade §6.2 정렬).

apply_strict_patch·build_strict_patch_artifact에서 동일 문구를 쓰기 위해 한곳에 둔다.
"""

from __future__ import annotations

# §6.2: SEARCH는 최소 줄 수(앵커 마커 포함)를 만족해야 다중 매치 위험이 줄어든다.
MIN_SEARCH_BLOCK_LINES = 3

ERR_STRICT_OPS_EMPTY = "operations가 비어 있어 strict patch를 적용할 수 없어요."
ERR_STRICT_OP_SHAPE = "strict patch operation 형식이 올바르지 않아요."
ERR_STRICT_MISSING_FIELDS = (
    "target_file, target_anchor, search는 모두 필요해요."
)
ERR_STRICT_PLACEHOLDER_REPLACE = (
    "replace가 아직 placeholder 상태라 auto-apply 할 수 없어요."
)
ERR_STRICT_PATH_TRAVERSAL = "허용되지 않은 대상 파일 경로예요: {target_file}"
ERR_STRICT_FILE_NOT_FOUND = "대상 파일을 찾을 수 없어요: {target_file}"
ERR_STRICT_ANCHOR_READ_FAIL = (
    "현재 파일에서 anchor `{target_anchor}` 블록을 읽지 못했어요: {target_file}"
)
ERR_STRICT_SEARCH_MISMATCH = (
    "SEARCH 블록이 `{target_file}`의 anchor `{target_anchor}` 현재 내용과 일치하지 않아요."
)
ERR_STRICT_MARKER_MISSING = (
    "SEARCH/REPLACE 블록 모두 anchor START/END marker를 유지해야 해요."
)
ERR_STRICT_MARKER_DRIFT = (
    "replace가 기존 anchor marker를 그대로 유지하지 않아 auto-apply 할 수 없어요."
)
ERR_STRICT_FILE_READ = "대상 파일을 읽을 수 없어요: {target_file}"
ERR_STRICT_SEARCH_NOT_UNIQUE = (
    "SEARCH 블록이 `{target_file}` 안에서 정확히 한 번 매치되지 않았어요. "
    "현재 매치 수: {match_count}"
)


# === ANCHOR: PATCH_VALIDATION_SEARCH_BLOCK_MEETS_MIN_LINES_START ===
def search_block_meets_min_lines(search: str) -> bool:
    if not search:
        return False
    return len(search.splitlines()) >= MIN_SEARCH_BLOCK_LINES
# === ANCHOR: PATCH_VALIDATION_SEARCH_BLOCK_MEETS_MIN_LINES_END ===


# === ANCHOR: PATCH_VALIDATION_ERR_STRICT_SEARCH_TOO_SHORT_START ===
def err_strict_search_too_short(line_count: int) -> str:
    return (
        f"SEARCH 블록이 앵커 구간 기준 최소 {MIN_SEARCH_BLOCK_LINES}줄 미만입니다 "
        f"(현재 {line_count}줄). 유일 매치 검증을 통과하기 어려워 자동 적용을 보류합니다."
    )
# === ANCHOR: PATCH_VALIDATION_ERR_STRICT_SEARCH_TOO_SHORT_END ===
# === ANCHOR: PATCH_VALIDATION_END ===
