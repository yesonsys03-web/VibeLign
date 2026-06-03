# === ANCHOR: INSTALL_BUNDLED_ENGINE_START ===
"""Copy compiled vibelign-engine into vibelign/_bundled/ with sha256 manifest.

Called from CI after `cargo build --release`. Idempotent.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_DIR = ROOT / "vibelign" / "_bundled"


# === ANCHOR: INSTALL_BUNDLED_ENGINE__SHA256_START ===
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
# === ANCHOR: INSTALL_BUNDLED_ENGINE__SHA256_END ===


# === ANCHOR: INSTALL_BUNDLED_ENGINE_MAIN_START ===
def main() -> int:
    binary_name = "vibelign-engine.exe" if sys.platform == "win32" else "vibelign-engine"
    src = ROOT / "vibelign-core" / "target" / "release" / binary_name
    if not src.exists():
        sys.stderr.write(f"engine binary not found: {src}\n")
        return 1
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    dest = TARGET_DIR / binary_name
    shutil.copy2(src, dest)
    manifest = dest.with_suffix(dest.suffix + ".sha256")
    manifest.write_text(f"{_sha256(dest)}  {dest.name}\n", encoding="utf-8")
    print(f"installed {dest} ({dest.stat().st_size} bytes)")
    return 0
# === ANCHOR: INSTALL_BUNDLED_ENGINE_MAIN_END ===


if __name__ == "__main__":
    raise SystemExit(main())
# === ANCHOR: INSTALL_BUNDLED_ENGINE_END ===
