import tempfile
import unittest
from pathlib import Path

from vibelign.core.watch_engine import is_watchable_path


class WatchEngineEligibilityTest(unittest.TestCase):
    def test_broad_project_files_are_watchable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            readme = root / "README.md"
            _ = readme.write_text("hello\n", encoding="utf-8")

            config_dir = root / "config"
            config_dir.mkdir()
            yaml_file = config_dir / "app.yaml"
            _ = yaml_file.write_text("name: vib\n", encoding="utf-8")

            self.assertTrue(is_watchable_path(readme))
            self.assertTrue(is_watchable_path(yaml_file))

    def test_generated_and_binary_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            dist_dir = root / "dist"
            dist_dir.mkdir()
            bundle = dist_dir / "bundle.js"
            _ = bundle.write_text("console.log('x')\n", encoding="utf-8")

            dot_dir = root / ".vibelign"
            dot_dir.mkdir()
            cache = dot_dir / "watch_state.json"
            _ = cache.write_text("{}\n", encoding="utf-8")

            image = root / "logo.png"
            _ = image.write_bytes(b"\x89PNG\r\n\x1a\n")

            self.assertFalse(is_watchable_path(bundle))
            self.assertFalse(is_watchable_path(cache))
            self.assertFalse(is_watchable_path(image))


if __name__ == "__main__":
    _ = unittest.main()
