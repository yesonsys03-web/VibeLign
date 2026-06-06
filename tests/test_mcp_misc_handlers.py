import importlib
import json
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass
class TextContent:
    type: str
    text: str


misc_handlers = importlib.import_module("vibelign.mcp.mcp_misc_handlers")
handle_anchor_list = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    misc_handlers.handle_anchor_list,
)
handle_config_get = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    misc_handlers.handle_config_get,
)
handle_planning_get = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    misc_handlers.handle_planning_get,
)


def _write_plan_session(
    root: Path,
    sid: str,
    *,
    output_path: str | None,
    created_at: str,
    content: str = "# 기획안\n본문",
) -> None:
    sess_dir = root / ".vibelign" / "planning" / sid
    sess_dir.mkdir(parents=True, exist_ok=True)
    session: dict[str, object] = {
        "schema_version": 1,
        "session_id": sid,
        "created_at": created_at,
    }
    if output_path is not None:
        session["output_path"] = output_path
        md = root / output_path
        md.parent.mkdir(parents=True, exist_ok=True)
        _ = md.write_text(content, encoding="utf-8")
    _ = (sess_dir / "session.json").write_text(
        json.dumps(session, ensure_ascii=False), encoding="utf-8"
    )


class McpMiscHandlersTest(unittest.TestCase):
    def test_handle_anchor_list_requires_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_anchor_list(root, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("앵커 인덱스가 없습니다", result[0].text)

    def test_handle_anchor_list_returns_index_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(parents=True, exist_ok=True)
            _ = (meta_dir / "anchor_index.json").write_text(
                json.dumps({"anchors": []}, ensure_ascii=False), encoding="utf-8"
            )

            result = handle_anchor_list(root, TextContent)

        payload = cast(dict[str, object], json.loads(result[0].text))
        self.assertIn("anchors", payload)

    def test_handle_config_get_returns_missing_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_config_get(root, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("설정 파일이 없습니다", result[0].text)

    def test_planning_get_requires_planning_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = handle_planning_get(Path(tmp), {}, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("저장된 기획안이 없습니다", result[0].text)

    def test_planning_get_returns_latest_saved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_plan_session(
                root,
                "plan_20260601_000000_aaaaaa",
                output_path="plans/old.md",
                created_at="2026-06-01T00:00:00+00:00",
                content="# 옛 기획안",
            )
            _write_plan_session(
                root,
                "plan_20260605_000000_bbbbbb",
                output_path="plans/new.md",
                created_at="2026-06-05T00:00:00+00:00",
                content="# 새 기획안\n최신 본문",
            )
            result = handle_planning_get(root, {}, TextContent)

        text = result[0].text
        self.assertIn("새 기획안", text)
        self.assertIn("session_id=plan_20260605_000000_bbbbbb", text)
        self.assertIn("source=plans/new.md", text)
        self.assertNotIn("옛 기획안", text)

    def test_planning_get_skips_unsaved_chat_session(self) -> None:
        # GUI 채팅 세션은 저장 전 output_path 가 없다. 이런 세션이 더
        # 최근이어도, 실제 plan 파일이 있는 더 오래된 세션을 돌려줘야 한다.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_plan_session(
                root,
                "plan_20260601_000000_aaaaaa",
                output_path="plans/real.md",
                created_at="2026-06-01T00:00:00+00:00",
                content="# 진짜 기획안",
            )
            _write_plan_session(
                root,
                "chat_20260609_000000_cccccc",
                output_path=None,
                created_at="2026-06-09T00:00:00+00:00",
            )
            result = handle_planning_get(root, {}, TextContent)

        text = result[0].text
        self.assertIn("진짜 기획안", text)
        self.assertIn("source=plans/real.md", text)

    def test_planning_get_specific_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_plan_session(
                root,
                "plan_20260601_000000_aaaaaa",
                output_path="plans/old.md",
                created_at="2026-06-01T00:00:00+00:00",
                content="# 옛 기획안",
            )
            _write_plan_session(
                root,
                "plan_20260605_000000_bbbbbb",
                output_path="plans/new.md",
                created_at="2026-06-05T00:00:00+00:00",
                content="# 새 기획안",
            )
            result = handle_planning_get(
                root,
                {"session_id": "plan_20260601_000000_aaaaaa"},
                TextContent,
            )

        text = result[0].text
        self.assertIn("옛 기획안", text)
        self.assertIn("source=plans/old.md", text)


if __name__ == "__main__":
    _ = unittest.main()
