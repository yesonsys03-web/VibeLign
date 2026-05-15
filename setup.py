# === ANCHOR: PYTHON_PACKAGE_RUST_ENGINE_BUNDLE_START ===
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.dist import Distribution as _Distribution
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel


ROOT = Path(__file__).resolve().parent
RUST_MANIFEST = ROOT / "vibelign-core" / "Cargo.toml"
RUST_BINARY_NAME = "vibelign-engine.exe" if sys.platform == "win32" else "vibelign-engine"
BUNDLED_DIR = ROOT / "vibelign" / "_bundled"


class BinaryDistribution(_Distribution):
    def has_ext_modules(self) -> bool:
        return True


class build_py(_build_py):
    def run(self) -> None:
        _bundle_rust_engine()
        super().run()


class bdist_wheel(_bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        _python_tag, _abi_tag, platform_tag = super().get_tag()
        return "py3", "none", platform_tag


def _bundle_rust_engine() -> None:
    if not RUST_MANIFEST.exists():
        bundled_binary = BUNDLED_DIR / RUST_BINARY_NAME
        if bundled_binary.exists() and _manifest_path(bundled_binary).exists():
            return
        raise RuntimeError("vibelign-core/Cargo.toml is required to bundle vibelign-engine")

    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--manifest-path",
            str(RUST_MANIFEST),
            "--bin",
            "vibelign-engine",
        ],
        cwd=ROOT,
        check=True,
    )

    built_binary = RUST_MANIFEST.parent / "target" / "release" / RUST_BINARY_NAME
    if not built_binary.exists():
        raise RuntimeError(f"cargo build did not produce {built_binary}")

    BUNDLED_DIR.mkdir(parents=True, exist_ok=True)
    bundled_binary = BUNDLED_DIR / RUST_BINARY_NAME
    shutil.copy2(built_binary, bundled_binary)
    _manifest_path(bundled_binary).write_text(
        f"{_sha256(bundled_binary)}  {bundled_binary.name}\n",
        encoding="utf-8",
    )


def _manifest_path(binary_path: Path) -> Path:
    return binary_path.with_suffix(binary_path.suffix + ".sha256")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


setup(cmdclass={"build_py": build_py, "bdist_wheel": bdist_wheel}, distclass=BinaryDistribution)
# === ANCHOR: PYTHON_PACKAGE_RUST_ENGINE_BUNDLE_END ===
