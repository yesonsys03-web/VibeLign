import importlib
import json
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.local_checkpoints import list_checkpoints


@dataclass
class TextContent:
    type: str
    text: str


checkpoint_handlers = importlib.import_module("vibelign.mcp.mcp_checkpoint_handlers")
handle_checkpoint_create = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_create,
)
handle_checkpoint_list = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_list,
)
handle_checkpoint_restore = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_restore,
)
handle_checkpoint_diff = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_diff,
)
handle_checkpoint_preview_restore = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_preview_restore,
)
handle_checkpoint_restore_files = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_restore_files,
)
handle_checkpoint_restore_suggestions = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_restore_suggestions,
)
handle_checkpoint_has_changes = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_has_changes,
)
handle_retention_apply = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_retention_apply,
)


def _payload(result: list[TextContent]) -> dict[str, object]:
    return cast(dict[str, object], json.loads(result[0].text))


class McpCheckpointHandlersTest(unittest.TestCase):
    def test_handle_checkpoint_create_creates_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")

            result = handle_checkpoint_create(root, {"message": "save"}, TextContent)

            self.assertEqual(len(result), 1)
            self.assertIn("체크포인트 저장 완료", result[0].text)
            self.assertEqual(len(list_checkpoints(root)), 1)

    def test_handle_checkpoint_create_writes_metadata_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            secret_text = "tok" + "en=fixtureSecretValue1234"

            _ = handle_checkpoint_create(root, {"message": f"save {secret_text}"}, TextContent)
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")
            payload = json.loads(audit_text.splitlines()[-1])

            self.assertEqual(payload["event"], "checkpoint_create")
            self.assertEqual(payload["tool"], "mcp")
            self.assertEqual(payload["result"], "success")
            self.assertTrue(payload["sandwich_checkpoint_id"])
            self.assertNotIn("fixtureSecretValue1234", audit_text)
            self.assertNotIn("save token", audit_text)

    def test_handle_checkpoint_create_audits_no_change_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            _ = handle_checkpoint_create(root, {"message": "empty"}, TextContent)
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")
            payload = json.loads(audit_text.splitlines()[-1])

            self.assertEqual(payload["event"], "checkpoint_create")
            self.assertEqual(payload["result"], "blocked")
            self.assertIsNone(payload["sandwich_checkpoint_id"])

    def test_handle_checkpoint_list_returns_saved_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            _ = handle_checkpoint_create(root, {"message": "save"}, TextContent)

            result = handle_checkpoint_list(root, TextContent)

            self.assertEqual(len(result), 1)
            self.assertIn("# 체크포인트 목록", result[0].text)
            self.assertIn("save", result[0].text)

    def test_handle_checkpoint_restore_requires_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = handle_checkpoint_restore(root, {}, TextContent)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].text, "오류: checkpoint_id가 필요합니다.")

    def test_handle_checkpoint_diff_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.diff_checkpoints",
                return_value={"summary": {"added_count": 1}},
            ):
                payload = _payload(
                    handle_checkpoint_diff(
                        root,
                        {"from_checkpoint_id": "old", "to_checkpoint_id": "new"},
                        TextContent,
                    )
                )

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["diff"], {"summary": {"added_count": 1}})

    def test_handle_checkpoint_preview_restore_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.preview_restore",
                return_value={"changes": []},
            ):
                payload = _payload(
                    handle_checkpoint_preview_restore(
                        root, {"checkpoint_id": "cp1", "relative_paths": ["app.py"]}, TextContent
                    )
                )

            self.assertEqual(payload, {"ok": True, "preview": {"changes": []}})

    def test_handle_checkpoint_restore_files_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.restore_files",
                return_value=2,
            ):
                payload = _payload(
                    handle_checkpoint_restore_files(
                        root, {"checkpoint_id": "cp1", "relative_paths": ["a.py", "b.py"]}, TextContent
                    )
                )

            self.assertEqual(payload, {"ok": True, "restored_count": 2})

    def test_handle_checkpoint_restore_suggestions_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.restore_suggestions",
                return_value={"suggestions": [{"relative_path": "app.py"}], "legacy_notice": None},
            ):
                payload = _payload(
                    handle_checkpoint_restore_suggestions(root, {"checkpoint_id": "cp1"}, TextContent)
                )

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["suggestions"], [{"relative_path": "app.py"}])

    def test_handle_checkpoint_has_changes_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.has_changes_since_checkpoint",
                return_value=True,
            ):
                payload = _payload(handle_checkpoint_has_changes(root, {"checkpoint_id": "cp1"}, TextContent))

            self.assertEqual(payload, {"has_changes": True, "ok": True})

    def test_handle_retention_apply_returns_json(self) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.core.checkpoint_engine.router.apply_retention",
                return_value={"count": 1},
            ):
                payload = _payload(handle_retention_apply(root, {}, TextContent))

            self.assertEqual(payload, {"cleanup": {"count": 1}, "ok": True})


if __name__ == "__main__":
    _ = unittest.main()
