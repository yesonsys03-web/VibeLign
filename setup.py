# === ANCHOR: PYTHON_PACKAGE_RUST_ENGINE_BUNDLE_START ===
"""Customize bdist_wheel to emit a platform-tagged, ABI-agnostic wheel.

The bundled vibelign-engine is built and copied into vibelign/_bundled by
cibuildwheel's CIBW_BEFORE_ALL step (cargo build + install_bundled_engine.py),
and is invoked via subprocess at runtime — so a single py3-none-<plat> wheel
serves all CPython 3.x per platform.
"""
from __future__ import annotations

from setuptools import setup
from setuptools.dist import Distribution as _Distribution

try:
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel


class BinaryDistribution(_Distribution):
    def has_ext_modules(self) -> bool:
        return True


class bdist_wheel(_bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        _python_tag, _abi_tag, platform_tag = super().get_tag()
        return "py3", "none", platform_tag


setup(cmdclass={"bdist_wheel": bdist_wheel}, distclass=BinaryDistribution)
# === ANCHOR: PYTHON_PACKAGE_RUST_ENGINE_BUNDLE_END ===
