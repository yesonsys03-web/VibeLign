import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.project_scan import (
    classify_file,
    extract_imports,
    iter_project_files,
    iter_source_files,
    relpath_str,
)


class ProjectScanTest(unittest.TestCase):
    def test_iter_project_files_excludes_generated_and_non_scan_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "target").mkdir()
            _ = (root / "target" / "bundle.js").write_text("bundle\n", encoding="utf-8")
            (root / "docs").mkdir()
            _ = (root / "docs" / "guide.md").write_text("docs\n", encoding="utf-8")
            (root / "tests").mkdir()
            _ = (root / "tests" / "test_app.py").write_text("pass\n", encoding="utf-8")
            (root / ".vibelign").mkdir()
            _ = (root / ".vibelign" / "project_map.json").write_text(
                "{}\n", encoding="utf-8"
            )

            files = {
                path.relative_to(root).as_posix() for path in iter_project_files(root)
            }

        self.assertEqual(files, {"src/app.py"})

    def test_iter_source_files_uses_shared_source_extensions_without_fd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            _ = (root / "src" / "notes.txt").write_text("notes\n", encoding="utf-8")

            with patch("vibelign.core.fast_tools.has_fd", return_value=False):
                files = {
                    path.relative_to(root).as_posix()
                    for path in iter_source_files(root)
                }

        self.assertEqual(files, {"src/app.py"})

    def test_iter_source_files_uses_rust_project_scan_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict("os.environ", {}, clear=True), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {"path": "main.py", "category": "entry", "imports": []},
                            {"path": "ui/views/panel.tsx", "category": "ui", "imports": []},
                        ],
                    },
                    None,
                ),
            ) as rust_scan, patch("vibelign.core.fast_tools.has_fd", return_value=False):
                files = sorted(path.relative_to(root).as_posix() for path in iter_source_files(root))

        self.assertEqual(files, ["main.py", "ui/views/panel.tsx"])
        rust_scan.assert_called_once_with(root)

    def test_iter_source_files_can_disable_rust_project_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")

            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "0"}, clear=False), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
            ) as rust_scan, patch("vibelign.core.fast_tools.has_fd", return_value=False):
                files = sorted(path.relative_to(root).as_posix() for path in iter_source_files(root))

        self.assertEqual(files, ["src/app.py"])
        rust_scan.assert_not_called()

    def test_iter_source_files_falls_back_when_rust_project_scan_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "1"}, clear=False), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(None, "RUST_ENGINE_UNAVAILABLE: missing"),
            ), patch("vibelign.core.fast_tools.has_fd", return_value=False):
                files = sorted(path.relative_to(root).as_posix() for path in iter_source_files(root))

        self.assertEqual(files, ["src/app.py"])

    def test_classify_file_uses_shared_core_entry_policy(self):
        self.assertEqual(
            classify_file(Path("vibelign/vib_cli.py"), "vibelign/vib_cli.py"),
            "entry",
        )
        self.assertEqual(
            classify_file(Path("vibelign/mcp_server.py"), "vibelign/mcp_server.py"),
            "entry",
        )

    @unittest.skipUnless(sys.platform == "win32", "Windows extended-length paths require Windows")
    def test_windows_extended_length_root_keeps_project_scan_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path("\\\\?\\" + str(Path(tmp).resolve()))
            (root / "src").mkdir()
            _ = (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "Node_Modules" / "pkg").mkdir(parents=True)
            _ = (root / "Node_Modules" / "pkg" / "index.js").write_text(
                "console.log('ignored')\n",
                encoding="utf-8",
            )

            project_files = sorted(relpath_str(root, path) for path in iter_project_files(root))
            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "0"}, clear=False), patch(
                "vibelign.core.fast_tools.has_fd", return_value=False
            ):
                source_files = sorted(relpath_str(root, path) for path in iter_source_files(root))

        self.assertEqual(project_files, ["src/app.py"])
        self.assertEqual(source_files, ["src/app.py"])

    def test_phase2_project_scan_contract_fixture_for_rust_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "main.py": "from services.api_client import fetch\nprint(fetch())\n",
                "ui/views/panel.tsx": "import React from 'react';\nimport { api } from '../../services/api';\n",
                "services/api_client.py": "import requests\nfrom core.guard import check\n",
                "services/도우미.py": "import os\n",
                "services/emoji_😀.py": "import pathlib\n",
                "core/guard.py": "def check():\n    return True\n",
                "scripts/migrate.rs": "fn main() {}\n",
                "docs/guide.py": "print('ignored docs')\n",
                "tests/test_app.py": "print('ignored tests')\n",
                "node_modules/pkg/index.js": "console.log('ignored dependency')\n",
                "target/debug/build.rs": "fn main() {}\n",
                ".vibelign/project_map.json": "{}\n",
                ".vibelign/anchor_meta.json": "{}\n",
                ".vibelign/engine.sock": "ignored daemon artifact\n",
                ".vibelign/app.py": "print('ignored vibelign source')\n",
            }
            for rel, content in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                _ = path.write_text(content, encoding="utf-8")

            project_files = sorted(relpath_str(root, path) for path in iter_project_files(root))
            with patch("vibelign.core.fast_tools.has_fd", return_value=False):
                source_files = sorted(relpath_str(root, path) for path in iter_source_files(root))
            main_imports = extract_imports(root / "main.py")
            service_imports = extract_imports(root / "services/api_client.py")
            ui_imports = extract_imports(root / "ui/views/panel.tsx")

        self.assertEqual(
            project_files,
            [
                "core/guard.py",
                "main.py",
                "scripts/migrate.rs",
                "services/api_client.py",
                "services/emoji_😀.py",
                "services/도우미.py",
                "ui/views/panel.tsx",
            ],
        )
        self.assertEqual(source_files, project_files)
        self.assertEqual(classify_file(Path("main.py"), "main.py"), "entry")
        self.assertEqual(classify_file(Path("ui/views/panel.tsx"), "ui/views/panel.tsx"), "ui")
        self.assertEqual(classify_file(Path("services/api_client.py"), "services/api_client.py"), "service")
        self.assertEqual(classify_file(Path("services/emoji_😀.py"), "services/emoji_😀.py"), "service")
        self.assertEqual(classify_file(Path("services/도우미.py"), "services/도우미.py"), "service")
        self.assertEqual(classify_file(Path("core/guard.py"), "core/guard.py"), "core")
        self.assertEqual(classify_file(Path("scripts/migrate.rs"), "scripts/migrate.rs"), "other")
        self.assertEqual(main_imports, ["services.api_client"])
        self.assertEqual(service_imports, ["requests", "core.guard"])
        self.assertEqual(ui_imports, ["react", "../../services/api"])


if __name__ == "__main__":
    _ = unittest.main()
