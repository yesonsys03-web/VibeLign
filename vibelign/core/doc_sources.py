# === ANCHOR: DOC_SOURCES_START ===
"""추가 문서 소스(extra doc sources) 설정 파일 I/O 및 정규화 정책 전담 모듈.

설정은 `.vibelign/doc_sources.json` 에 원자적으로 기록되며,
add/remove/list/fingerprint 헬퍼가 공개 API를 이룬다.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .meta_paths import MetaPaths

# === ANCHOR: DOC_SOURCES_CONSTANTS_START ===
MAX_FILES_PER_SOURCE: int = 2000
DOC_SOURCES_SCHEMA_VERSION: int = 1

# built-in source paths that can never be removed via the remove() API.
# These are relative POSIX paths as stored in the config.
_BUILTIN_SOURCE_PATHS: frozenset[str] = frozenset(
    [
        "docs",
        "docs/wiki",
        "docs/superpowers/plans",
        "docs/superpowers/specs",
        "PROJECT_CONTEXT.md",
        "README.md",
        "docs/MANUAL.md",
    ]
)
# === ANCHOR: DOC_SOURCES_CONSTANTS_END ===


# === ANCHOR: DOC_SOURCES_DATACLASS_START ===
@dataclass
class DocSources:
    """정규화·정렬·중복제거된 추가 문서 소스 목록."""
    sources: list[str] = field(default_factory=list)
# === ANCHOR: DOC_SOURCES_DATACLASS_END ===


# === ANCHOR: DOC_SOURCES_LOAD_START ===
def load(meta: "MetaPaths") -> DocSources:
    """doc_sources.json 을 읽어 DocSources 를 반환한다.
    파일 없음 / 빈 파일 / 손상된 JSON 모두 DocSources(sources=[]) 로 graceful fallback.
    절대 예외를 던지지 않는다.
    """
    try:
        raw = meta.doc_sources_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DocSources(sources=[])
    except OSError:
        return DocSources(sources=[])

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return DocSources(sources=[])

    if not isinstance(payload, dict):
        return DocSources(sources=[])

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        return DocSources(sources=[])

    sources = [s for s in raw_sources if isinstance(s, str)]
    return DocSources(sources=sorted(set(sources)))
# === ANCHOR: DOC_SOURCES_LOAD_END ===


# === ANCHOR: DOC_SOURCES_SAVE_START ===
def save(meta: "MetaPaths", sources: DocSources) -> None:
    """DocSources 를 doc_sources.json 에 원자적으로 기록한다.

    docs_index_cache.write_docs_index_cache 와 동일한 tempfile + os.replace 패턴.
    Windows 에서 replace 실패 시 한 번 재시도한다.
    """
    meta.ensure_vibelign_dir()
    target = meta.doc_sources_path
    payload = {
        "version": DOC_SOURCES_SCHEMA_VERSION,
        "sources": sorted(set(sources.sources)),
    }
    serialized = json.dumps(payload, ensure_ascii=False)

    fd, tmp_name = tempfile.mkstemp(
        prefix=".doc_sources.", suffix=".tmp", dir=str(meta.vibelign_dir)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(tmp_path, target)
        except OSError:
            if sys.platform == "win32":
                time.sleep(0.05)
                os.replace(tmp_path, target)
            else:
                raise
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise
# === ANCHOR: DOC_SOURCES_SAVE_END ===


# === ANCHOR: DOC_SOURCES_NORMALIZE_START ===
def normalize_source(root: Path, raw: str) -> str:
    """raw 입력을 검증하고 정규화된 relative POSIX path 를 반환한다.

    거부 조건:
    - 빈 문자열 / 공백만
    - 절대 경로 또는 루트를 벗어나는 경로 (`..`)
    - 존재하지 않는 디렉토리 (파일도 거부)
    - resolve() 후 project root 바깥인 경로
    - symlink/junction 이 루트 밖으로 나가는 경우

    ValueError 를 GUI 에 직접 노출 가능한 사용자 친화적 메시지와 함께 발생시킨다.
    """
    if not raw or not raw.strip():
        raise ValueError("경로가 비어 있습니다. 유효한 디렉토리 경로를 입력해 주세요.")

    # Windows 역슬래시 정규화
    normalized_raw = raw.replace("\\", "/").strip()

    # 절대 경로 거부 (정규화 후 체크)
    if Path(normalized_raw).is_absolute():
        raise ValueError(
            f"절대 경로는 등록할 수 없습니다: '{raw}'\n"
            "프로젝트 루트 기준 상대 경로를 입력해 주세요."
        )

    # `..` 세그먼트 포함 거부 (resolve 전 early reject)
    parts = Path(normalized_raw).parts
    if ".." in parts:
        raise ValueError(
            f"상위 디렉토리 참조('..')가 포함된 경로는 등록할 수 없습니다: '{raw}'"
        )

    candidate = root / normalized_raw

    # 존재 여부 및 디렉토리 여부 확인
    if not candidate.exists():
        raise ValueError(
            f"경로가 존재하지 않습니다: '{raw}'\n"
            "프로젝트 내에 실제로 존재하는 디렉토리 경로를 입력해 주세요."
        )
    if not candidate.is_dir():
        raise ValueError(
            f"파일 경로는 등록할 수 없습니다: '{raw}'\n"
            "디렉토리 경로만 추가 문서 소스로 등록할 수 있습니다."
        )

    # resolve() 로 canonical path 확보 (symlink/junction 포함)
    try:
        resolved_candidate = candidate.resolve()
        resolved_root = root.resolve()
    except OSError as e:
        raise ValueError(
            f"경로를 확인하는 중 오류가 발생했습니다: '{raw}'\n오류: {e}"
        )

    # 루트 밖으로 벗어나는지 확인
    try:
        rel = resolved_candidate.relative_to(resolved_root)
    except ValueError:
        raise ValueError(
            f"프로젝트 루트 바깥 경로는 등록할 수 없습니다: '{raw}'\n"
            f"루트: {resolved_root}"
        )

    return rel.as_posix()
# === ANCHOR: DOC_SOURCES_NORMALIZE_END ===


# === ANCHOR: DOC_SOURCES_ADD_START ===
def add(meta: "MetaPaths", raw: str) -> DocSources:
    """raw 경로를 정규화하여 추가 문서 소스에 등록한다.

    중복 등록 시 ValueError 를 발생시킨다.
    성공 시 갱신된 DocSources 를 반환한다.
    """
    normalized = normalize_source(meta.root, raw)
    current = load(meta)

    if normalized in current.sources:
        raise ValueError(
            f"이미 등록된 경로입니다: '{normalized}'\n"
            "중복 등록은 허용되지 않습니다."
        )

    new_sources = sorted(set(current.sources) | {normalized})
    updated = DocSources(sources=new_sources)
    save(meta, updated)
    return updated
# === ANCHOR: DOC_SOURCES_ADD_END ===


# === ANCHOR: DOC_SOURCES_REMOVE_START ===
def remove(meta: "MetaPaths", raw: str) -> DocSources:
    """raw 경로를 정규화하여 추가 문서 소스에서 제거한다.

    built-in source 경로는 제거할 수 없다.
    미등록 경로 제거 시도 시 ValueError 를 발생시킨다.
    성공 시 갱신된 DocSources 를 반환한다.
    """
    # built-in 체크는 normalize 이전에 가볍게 수행 (non-existent dir 오류 방지)
    # Windows 역슬래시 경량 정규화만 수행한 후 비교
    lightly_normalized = raw.replace("\\", "/").strip().strip("/")
    if lightly_normalized in _BUILTIN_SOURCE_PATHS:
        raise ValueError(
            f"기본 제공 경로는 제거할 수 없습니다: '{raw}'\n"
            "PROJECT_CONTEXT.md, docs/, README.md 등 내장 소스는 항상 유지됩니다."
        )

    # 이후 표준 normalize 로 target 확정 (비built-in이라도 유효성 검증 필요)
    # 그러나 remove 는 등록된 경로를 삭제하는 것이므로,
    # 디렉토리가 이미 삭제된 상황도 고려해야 한다.
    # → 먼저 load 된 sources 목록에서 lightly_normalized 로 매칭을 시도하고,
    #   정확한 매칭이 있으면 그걸 제거한다.
    current = load(meta)

    # 저장된 sources 에서 직접 매칭 (이미 정규화된 값끼리 비교)
    if lightly_normalized not in current.sources:
        # normalize 를 시도해서 같은 값이 나오는지 확인 (존재 여부는 선택적)
        try:
            normalized = normalize_source(meta.root, raw)
        except ValueError:
            normalized = lightly_normalized

        if normalized not in current.sources:
            raise ValueError(
                f"등록되지 않은 경로입니다: '{raw}'\n"
                "먼저 추가 문서 소스로 등록된 경로만 제거할 수 있습니다."
            )
        target = normalized
    else:
        target = lightly_normalized

    new_sources = sorted(s for s in current.sources if s != target)
    updated = DocSources(sources=new_sources)
    save(meta, updated)
    return updated
# === ANCHOR: DOC_SOURCES_REMOVE_END ===


# === ANCHOR: DOC_SOURCES_FINGERPRINT_START ===
def fingerprint(sources: list[str]) -> str:
    """sources 목록의 SHA-256 fingerprint 를 반환한다.

    입력 순서와 무관하게 결정적(deterministic) 결과를 보장한다.
    빈 리스트도 정상 처리된다.
    """
    sorted_sources = sorted(sources)
    payload = json.dumps(sorted_sources, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
# === ANCHOR: DOC_SOURCES_FINGERPRINT_END ===
# === ANCHOR: DOC_SOURCES_END ===
