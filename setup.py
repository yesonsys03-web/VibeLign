"""Customize bdist_wheel to emit a platform-tagged, ABI-agnostic wheel.

The bundled vibelign-engine is invoked via subprocess (not Python C API),
so a single py3-none-<plat> wheel serves all CPython 3.x per platform.
"""
from __future__ import annotations

from setuptools import setup

try:
    from setuptools.command.bdist_wheel import bdist_wheel
except ImportError:
    from wheel.bdist_wheel import bdist_wheel


class PlatformBdistWheel(bdist_wheel):
    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False

    def get_tag(self) -> tuple[str, str, str]:
        _python, _abi, plat = super().get_tag()
        return ("py3", "none", plat)


setup(cmdclass={"bdist_wheel": PlatformBdistWheel})
