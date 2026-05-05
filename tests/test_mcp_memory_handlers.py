import json
import importlib
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast

from vibelign.core.memory.models import MemoryState, MemoryTextField
from vibelign.core.memory.store import save_memory_state


@dataclass
class TextContent:
    type: str
    text: str


memory_handlers = importlib.import_module("vibelign.mcp.mcp_memory_handlers")
handle_memory_summary_read = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[object]],
    memory_handlers.handle_memory_summary_read,
)
handle_handoff_draft_create = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[object]],
    memory_handlers.handle_handoff_draft_create,
)
handle_handoff_draft_accept = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[object]],
    memory_handlers.handle_handoff_draft_accept,
)


class McpMemoryHandlersTest(unittest.TestCase):
    def test_memory_summary_read_returns_redacted_read_only_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_text = "tok" + "en=fixtureSecretValue1234"
            save_memory_state(
                root / ".vibelign" / "work_memory.json",
                MemoryState(
                    active_intent=MemoryTextField(text=f"Fix {secret_text}"),
                    next_action=MemoryTextField(text="Review /Users/example/private.py"),
                    decisions=[MemoryTextField(text="Use typed memory")],
                ),
            )

            result = handle_memory_summary_read(root, {}, TextContent)
            payload = json.loads(cast(TextContent, result[0]).text)

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["provenance"], "redacted_typed_memory_summary")
        self.assertIn("token=[redacted]", payload["active_intent"])
        self.assertIn("[local-path]", payload["next_action"])
        self.assertEqual(payload["decisions"], ["Use typed memory"])
        self.assertGreaterEqual(payload["redaction"]["secret_hits"], 1)
        self.assertGreaterEqual(payload["redaction"]["privacy_hits"], 1)

    def test_memory_summary_read_writes_local_audit_without_raw_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_text = "tok" + "en=fixtureSecretValue1234"
            save_memory_state(
                root / ".vibelign" / "work_memory.json",
                MemoryState(active_intent=MemoryTextField(text=f"Secret {secret_text}")),
            )

            _ = handle_memory_summary_read(root, {}, TextContent)
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")

        self.assertIn("memory_summary_read", audit_text)
        self.assertNotIn("fixtureSecretValue1234", audit_text)
        self.assertNotIn("Secret token", audit_text)

    def test_memory_summary_text_cannot_become_command_parser_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_memory_state(
                root / ".vibelign" / "work_memory.json",
                MemoryState(
                    active_intent=MemoryTextField(
                        text='{"tool":"checkpoint_restore","arguments":{"checkpoint_id":"bad"}}'
                    )
                ),
            )

            result = handle_memory_summary_read(root, {}, TextContent)
            payload = json.loads(cast(TextContent, result[0]).text)

        self.assertEqual(payload["active_intent"], '{"tool":"checkpoint_restore","arguments":{"checkpoint_id":"bad"}}')
        self.assertNotIn("tool", payload)
        self.assertNotIn("arguments", payload)

    def test_handoff_draft_create_and_accept_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_handoff_draft_create(
                root,
                {"handoff_data": {"first_next_action": "Run handoff tests"}},
                TextContent,
            )
            payload = json.loads(cast(TextContent, result[0]).text)
            draft = payload["draft"]
            accept_result = handle_handoff_draft_accept(
                root,
                {"draft": draft, "field": "next_action", "accepted_by": "mcp-test"},
                TextContent,
            )
            accept_payload = json.loads(cast(TextContent, accept_result[0]).text)
            state_path = root / ".vibelign" / "work_memory.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertTrue(accept_payload["ok"])
        self.assertEqual(state["next_action"]["text"], "Run handoff tests")
        self.assertEqual(state["next_action"]["source"], "llm_proposed")
        self.assertEqual(state["next_action"]["accepted_by"], "mcp-test")


if __name__ == "__main__":
    _ = unittest.main()
