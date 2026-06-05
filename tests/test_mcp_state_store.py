import importlib
import tempfile
import unittest
from pathlib import Path
from typing import Callable, cast

from vibelign.core.meta_paths import MetaPaths

state_store = importlib.import_module("vibelign.mcp.mcp_state_store")
load_state = cast(Callable[[MetaPaths], dict[str, object]], state_store.load_state)
state_timestamp = cast(Callable[[], str], state_store.state_timestamp)
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

    def test_patch_session_storage_helpers_are_removed(self) -> None:
        self.assertFalse(hasattr(state_store, "load_patch_session"))
        self.assertFalse(hasattr(state_store, "save_patch_session"))
        self.assertFalse(hasattr(state_store, "new_patch_session_id"))
        self.assertFalse(hasattr(state_store, "patch_session_now"))
        self.assertIsInstance(state_timestamp(), str)


if __name__ == "__main__":
    _ = unittest.main()
