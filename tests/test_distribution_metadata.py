import importlib
import importlib.util
import unittest
import ast
import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

tomllib = (
    importlib.import_module("tomllib")
    if importlib.util.find_spec("tomllib") is not None
    else None
)


ROOT = Path(__file__).resolve().parents[1]


class DistributionMetadataTest(unittest.TestCase):
    def _load_project(self) -> dict[str, object]:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        if tomllib is not None:
            loads = cast(Callable[[str], object], getattr(tomllib, "loads"))
            loaded = loads(text)
            return cast(dict[str, object], loaded)

        project: dict[str, object] = {}
        urls: dict[str, str] = {}
        in_project = False
        in_urls = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line == "[project]":
                in_project = True
                in_urls = False
                continue
            if line == "[project.urls]":
                in_project = False
                in_urls = True
                continue
            if line.startswith("[") and line.endswith("]"):
                in_project = False
                in_urls = False
                continue
            if in_project and line.startswith("license = "):
                project["license"] = ast.literal_eval(line.split("=", 1)[1].strip())
            elif in_project and line.startswith("keywords = "):
                project["keywords"] = ast.literal_eval(line.split("=", 1)[1].strip())
            elif in_urls:
                match = re.match(r"^(\w+)\s*=\s*(.+)$", line)
                if match:
                    urls[match.group(1)] = ast.literal_eval(match.group(2))
        classifiers_match = re.search(r"classifiers\s*=\s*\[(.*?)\]", text, re.S)
        if classifiers_match:
            project["classifiers"] = ast.literal_eval(
                "[" + classifiers_match.group(1) + "]"
            )
        project["urls"] = urls
        return {"project": project}

    def test_project_urls_and_keywords_exist(self):
        data = self._load_project()
        project = cast(dict[str, object], data["project"])

        self.assertIn("urls", project)
        self.assertEqual(
            sorted(cast(dict[str, str], project["urls"]).keys()),
            ["Documentation", "Homepage", "Issues", "Releases", "Repository"],
        )

        keywords = set(cast(list[str], project.get("keywords", [])))
        self.assertTrue({"vibelign", "ai", "cli", "mcp"}.issubset(keywords))

    def test_project_has_license_and_classifiers(self):
        data = self._load_project()
        project = cast(dict[str, object], data["project"])

        self.assertEqual(project["license"], "MIT")
        classifiers = set(cast(list[str], project.get("classifiers", [])))
        self.assertIn("Programming Language :: Python :: 3", classifiers)

    def test_project_scripts_target_refactored_packages(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('vibelign = "vibelign.cli:main"', text)
        self.assertIn('vib = "vibelign.cli.vib_cli:main"', text)
        self.assertIn('vibelign-mcp = "vibelign.mcp.mcp_server:main"', text)

    def test_rust_sidecar_is_declared_as_package_data(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[tool.setuptools.package-data]", text)
        self.assertIn('"_bundled/vibelign-engine"', text)
        self.assertIn('"_bundled/vibelign-engine.exe"', text)
        self.assertIn('"_bundled/vibelign-engine.sha256"', text)
        self.assertIn('"_bundled/vibelign-engine.exe.sha256"', text)

    def test_pyinstaller_spec_bundles_rust_sidecar_and_checkpoint_engine(self):
        text = (ROOT / "vib.spec").read_text(encoding="utf-8")

        self.assertIn('"vibelign.core.checkpoint_engine.rust_engine"', text)
        self.assertIn('"vibelign.core.checkpoint_engine.rust_checkpoint_engine"', text)
        self.assertIn('datas.append(("vibelign/_bundled", "vibelign/_bundled"))', text)
        self.assertNotIn('"vibelign.commands.history_cmd"', text)
        self.assertNotIn('"vibelign.commands.undo_cmd"', text)

    def test_checkpoint_cutover_notice_is_user_visible(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        migration = (ROOT / "MIGRATION_v1_to_v2.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_ko = (ROOT / "README.ko.md").read_text(encoding="utf-8")

        self.assertIn("Rust/SQLite", changelog)
        self.assertIn("not automatically imported or merged", changelog)
        self.assertIn("Rust/SQLite 체크포인트 엔진", migration)
        self.assertIn("자동 import/병합하지 않습니다", migration)
        self.assertIn("Back up `.vibelign/checkpoints/`", readme)
        self.assertIn("업그레이드 전에 `.vibelign/checkpoints/`를 백업", readme_ko)


if __name__ == "__main__":
    _ = unittest.main()
