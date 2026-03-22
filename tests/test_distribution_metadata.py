import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DistributionMetadataTest(unittest.TestCase):
    def test_project_urls_and_keywords_exist(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = data["project"]

        self.assertIn("urls", project)
        self.assertEqual(
            sorted(project["urls"].keys()),
            ["Documentation", "Homepage", "Issues", "Releases", "Repository"],
        )

        keywords = set(project.get("keywords", []))
        self.assertTrue({"vibelign", "ai", "cli", "mcp"}.issubset(keywords))

    def test_project_has_license_and_classifiers(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = data["project"]

        self.assertEqual(project["license"], "MIT")
        classifiers = set(project.get("classifiers", []))
        self.assertIn("Programming Language :: Python :: 3", classifiers)


if __name__ == "__main__":
    _ = unittest.main()
