# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_DISCOVERY_START ===
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RustEngineAvailability:
    available: bool
    binary_path: Path | None
    reason: str | None = None
    code: str | None = None


def _binary_name() -> str:
    return "vibelign-engine.exe" if sys.platform == "win32" else "vibelign-engine"


def _candidate_paths(root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get("VIBELIGN_ENGINE_PATH")
    if env_path:
        candidates.append(Path(env_path))
    pyinstaller_root = getattr(sys, "_MEIPASS", None)
    if isinstance(pyinstaller_root, str) and pyinstaller_root:
        candidates.append(Path(pyinstaller_root) / "vibelign" / "_bundled" / _binary_name())
    if sys.executable:
        candidates.append(
            Path(sys.executable).resolve().parent
            / "_internal"
            / "vibelign"
            / "_bundled"
            / _binary_name()
        )
    candidates.extend(
        [
            root / "vibelign-core" / "target" / "debug" / _binary_name(),
            root / "vibelign-core" / "target" / "release" / _binary_name(),
            Path(__file__).resolve().parents[3] / "_bundled" / _binary_name(),
        ]
    )
    return candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_integrity(binary_path: Path) -> str | None:
    manifest_path = binary_path.with_suffix(binary_path.suffix + ".sha256")
    if not manifest_path.exists():
        # Dev 빌드 경로(`vibelign-core/target/{debug,release}`)에서는 cargo build
        # 직후 매니페스트가 빠질 수 있다. 사용자가 어찌할 수 없는 환경 결함이고
        # tamper 탐지 목적도 약하므로(쓰기 가능한 위치) 자동 생성으로 회복한다.
        # 그 외 위치(번들/설치본)에서 매니페스트가 없으면 기존대로 실패 — 빌드/
        # 배포 단계 누락 신호.
        if _is_dev_build_path(binary_path) and _try_write_manifest(binary_path, manifest_path):
            expected = manifest_path.read_text(encoding="utf-8").split()[0].strip().lower()
        else:
            return "integrity manifest missing"
    else:
        expected = manifest_path.read_text(encoding="utf-8").split()[0].strip().lower()
    if not expected:
        return "integrity manifest empty"
    actual = _sha256(binary_path).lower()
    if actual != expected:
        return "integrity check failed"
    return None


def _is_dev_build_path(binary_path: Path) -> bool:
    # Why case-fold: Windows NTFS 는 case-preserving 이라 사용자가 cloned 디렉토리
    # 이름을 다른 케이스로 가지고 있을 수 있다 (e.g. `Vibelign-core/Target/Debug`).
    # 표준 Cargo 빌드는 항상 소문자지만, 다른 cross-platform 매칭 로직 (예:
    # `project_scan.rs::is_ignored`) 도 lowercase 비교를 쓰므로 일관성 차원에서
    # case-insensitive 로 통일.
    parts = tuple(part.lower() for part in binary_path.parts)
    if len(parts) < 4:
        return False
    return parts[-3:-1] in (("target", "debug"), ("target", "release")) and "vibelign-core" in parts


def _try_write_manifest(binary_path: Path, manifest_path: Path) -> bool:
    try:
        digest = _sha256(binary_path)
        manifest_path.write_text(f"{digest}  {binary_path.name}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def find_rust_engine(root: Path) -> RustEngineAvailability:
    integrity_failure: RustEngineAvailability | None = None
    for candidate in _candidate_paths(root):
        if not candidate.exists() or not candidate.is_file():
            continue
        integrity_error = _verify_integrity(candidate)
        if integrity_error:
            integrity_failure = RustEngineAvailability(
                False, candidate, integrity_error, "RUST_ENGINE_INTEGRITY_FAILED"
            )
            continue
        return RustEngineAvailability(True, candidate, None, None)
    if integrity_failure is not None:
        return integrity_failure
    return RustEngineAvailability(
        False, None, "rust engine binary missing", "RUST_ENGINE_UNAVAILABLE"
    )


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_DISCOVERY_END ===
