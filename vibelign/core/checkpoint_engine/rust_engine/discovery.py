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
        return "integrity manifest missing"
    expected = manifest_path.read_text(encoding="utf-8").split()[0].strip().lower()
    if not expected:
        return "integrity manifest empty"
    actual = _sha256(binary_path).lower()
    if actual != expected:
        return "integrity check failed"
    return None


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
