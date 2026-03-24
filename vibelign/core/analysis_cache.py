# === ANCHOR: ANALYSIS_CACHE_START ===
"""분석 결과 캐시.

두 번째 실행부터 캐시를 사용해 속도를 높인다.
캐시 무효화 조건:
  1. feature_flags 상태 변경
  2. 프로젝트 파일 변경 (mtime 합산 해시)
  3. force=True

원자 쓰기: scan_cache.py와 동일한 tmp → replace 패턴 적용.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from vibelign.core.feature_flags import is_enabled

ANALYSIS_CACHE_SCHEMA = 1

_FLAGS_TO_TRACK = ["USE_ACTION_ENGINE"]


def _current_flag_state() -> Dict[str, bool]:
    return {flag: is_enabled(flag) for flag in _FLAGS_TO_TRACK}


def _project_mtime_hash(root: Path) -> str:
    """소스 파일의 mtime 합산으로 변경 여부를 빠르게 감지한다."""
    from vibelign.core.project_scan import iter_source_files

    entries = []
    try:
        for path in sorted(iter_source_files(root)):
            try:
                mtime = os.stat(path).st_mtime
                entries.append(f"{path}:{mtime:.3f}")
            except OSError:
                pass
    except Exception:
        pass

    digest = hashlib.md5("\n".join(entries).encode()).hexdigest()
    return digest


def load_analysis_cache(cache_path: Path, root: Path, force: bool = False) -> Optional[Dict[str, Any]]:
    """캐시가 유효하면 DoctorV2Report dict 반환. 무효면 None."""
    if force or not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("schema_version") != ANALYSIS_CACHE_SCHEMA:
        return None

    # feature_flags 상태 비교
    if payload.get("feature_flags") != _current_flag_state():
        return None

    # 파일 변경 여부 확인
    if payload.get("project_mtime_hash") != _project_mtime_hash(root):
        return None

    return payload.get("report")


def save_analysis_cache(
    cache_path: Path,
    root: Path,
    report_dict: Dict[str, Any],
    generated_at: str,
) -> None:
    """분석 결과를 캐시에 원자적으로 저장한다."""
    try:
        payload = {
            "schema_version": ANALYSIS_CACHE_SCHEMA,
            "generated_at": generated_at,
            "feature_flags": _current_flag_state(),
            "project_mtime_hash": _project_mtime_hash(root),
            "report": report_dict,
        }
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(cache_path)
    except OSError:
        pass
# === ANCHOR: ANALYSIS_CACHE_END ===
