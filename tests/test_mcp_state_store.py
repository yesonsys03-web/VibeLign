import importlib
import tempfile
import unittest
from pathlib import Path
from typing import Callable, cast

from vibelign.core.meta_paths import MetaPaths

state_store = importlib.import_module("vibelign.mcp.mcp_state_store")
load_patch_session = cast(
    Callable[[MetaPaths], dict[str, object] | None], state_store.load_patch_session
)
load_state = cast(Callable[[MetaPaths], dict[str, object]], state_store.load_state)
new_patch_session_id = cast(Callable[[], str], state_store.new_patch_session_id)
patch_session_now = cast(Callable[[], str], state_store.patch_session_now)
save_patch_session = cast(
    Callable[[MetaPaths, dict[str, object] | None], None],
    state_store.save_patch_session,
)
save_state = cast(
    Callable[[MetaPaths, dict[str, object]], None], state_store.save_state
)


class McpStateStoreTest(unittest.TestCase):
    def test_save_and_load_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta = MetaPaths(Path(tmp))
            save_state(meta, {"hello": "world"})

            loaded = load_state(meta)

        self.assertEqual(loaded, {"hello": "world"})

    def test_save_and_load_patch_session_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta = MetaPaths(Path(tmp))
            session: dict[str, object] = {
                "session_id": "abc",
                "needs_verification": True,
            }
            save_patch_session(meta, session)

            loaded = load_patch_session(meta)

        self.assertEqual(loaded, session)

    def test_save_patch_session_none_clears_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta = MetaPaths(Path(tmp))
            save_patch_session(meta, {"session_id": "abc"})
            save_patch_session(meta, None)

            loaded = load_patch_session(meta)

        self.assertIsNone(loaded)

    def test_patch_session_helpers_return_strings(self) -> None:
        self.assertIsInstance(patch_session_now(), str)
        self.assertIsInstance(new_patch_session_id(), str)


if __name__ == "__main__":
    _ = unittest.main()
