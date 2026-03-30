import importlib
import importlib.util
import unittest
import ast
import re
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
            return cast(dict[str, object], tomllib.loads(text))

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


if __name__ == "__main__":
    _ = unittest.main()
