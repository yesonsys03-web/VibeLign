import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from vibelign.core.watch_engine import handle_deleted_path, is_watchable_path, run_watch
from vibelign.core.watch_state import FileSnapshot, load_state, save_state


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


class WatchEngineDeleteHandlingTest(unittest.TestCase):
    def test_handle_deleted_path_removes_state_and_logs_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deleted = root / "src" / "main.py"
            deleted.parent.mkdir(parents=True)
            state_path = root / ".vibelign" / "watch_state.json"
            log_path = root / ".vibelign" / "watch.log"
            state = {
                "src/main.py": FileSnapshot(
                    path="src/main.py", lines=10, sha1="deadbeef"
                )
            }

            rel = handle_deleted_path(
                root,
                state,
                state_path,
                str(deleted),
                json_mode=False,
                log_path=log_path,
            )

            self.assertEqual("src/main.py", rel)
            self.assertEqual({}, state)
            saved = load_state(state_path)
            self.assertEqual({}, saved)
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn('"message": "src/main.py 삭제됨"', log_text)

    def test_handle_deleted_path_ignores_unknown_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".vibelign" / "watch_state.json"
            log_path = root / ".vibelign" / "watch.log"
            state = {"src/main.py": FileSnapshot(path="src/main.py", lines=1, sha1="x")}

            rel = handle_deleted_path(
                root,
                state,
                state_path,
                str(root / "src" / "other.py"),
                log_path=log_path,
            )

            self.assertEqual("src/other.py", rel)
            self.assertIn("src/main.py", state)
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn('"message": "src/other.py 삭제됨"', log_text)

    def test_run_watch_ignores_deleted_vibelign_meta_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            log_path = vg_dir / "watch.log"
            meta_file = vg_dir / "project_map.tmp"
            meta_file.write_text("{}\n", encoding="utf-8")

            class FakeHandlerBase:
                pass

            class FakeObserver:
                def __init__(self, callback) -> None:
                    self.callback = callback
                    self.handler = None

                def schedule(
                    self, event_handler: object, path: str, recursive: bool = False
                ) -> None:
                    _ = path
                    _ = recursive
                    self.handler = event_handler

                def start(self) -> None:
                    assert self.handler is not None
                    self.callback(self.handler)

                def stop(self) -> None:
                    return None

                def join(self) -> None:
                    return None

            def observer_factory():
                return FakeObserver(
                    lambda handler: handler.on_deleted(
                        SimpleNamespace(is_directory=False, src_path=str(meta_file))
                    )
                )

            with (
                patch(
                    "vibelign.core.watch_engine._import_watchdog_classes",
                    return_value=(FakeHandlerBase, observer_factory),
                ),
                patch(
                    "vibelign.core.watch_engine.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                run_watch({"root": str(root), "write_log": True})

            if log_path.exists():
                log_text = log_path.read_text(encoding="utf-8")
                self.assertNotIn("project_map.tmp 삭제됨", log_text)

    def test_run_watch_on_deleted_updates_state_and_project_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            state_path = vg_dir / "watch_state.json"
            log_path = vg_dir / "watch.log"
            project_map_path = vg_dir / "project_map.json"
            deleted = root / "src" / "main.py"
            deleted.parent.mkdir(parents=True)
            deleted.write_text("print('hello')\n", encoding="utf-8")
            save_state(
                state_path,
                {
                    "src/main.py": FileSnapshot(
                        path="src/main.py", lines=1, sha1="deadbeef"
                    )
                },
            )
            project_map_path.write_text("{}\n", encoding="utf-8")

            deleted.unlink()

            class FakeHandlerBase:
                pass

            class FakeTimer:
                def __init__(self, _delay: float, callback):
                    self._callback = callback

                def start(self) -> None:
                    return None

                def cancel(self) -> None:
                    return None

                def fire(self) -> None:
                    self._callback()

            class FakeObserver:
                def __init__(self, callback) -> None:
                    self.callback = callback
                    self.handler = None

                def schedule(
                    self, event_handler: object, path: str, recursive: bool = False
                ) -> None:
                    _ = path
                    _ = recursive
                    self.handler = event_handler

                def start(self) -> None:
                    assert self.handler is not None
                    self.callback(self.handler)
                    timer = getattr(self.handler, "global_timer", None)
                    if timer is not None:
                        timer.fire()

                def stop(self) -> None:
                    return None

                def join(self) -> None:
                    return None

            def observer_factory():
                return FakeObserver(
                    lambda handler: handler.on_deleted(
                        SimpleNamespace(is_directory=False, src_path=str(deleted))
                    )
                )

            with (
                patch(
                    "vibelign.core.watch_engine._import_watchdog_classes",
                    return_value=(FakeHandlerBase, observer_factory),
                ),
                patch("vibelign.core.watch_engine.threading.Timer", FakeTimer),
                patch(
                    "vibelign.core.watch_engine.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                run_watch({"root": str(root), "write_log": True})

            saved = load_state(state_path)
            self.assertEqual({}, saved)
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn('"message": "src/main.py 삭제됨"', log_text)
            project_map = project_map_path.read_text(encoding="utf-8")
            self.assertIn('"file_count": 0', project_map)

    def test_run_watch_auto_fix_inserts_anchors_for_new_python_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            log_path = vg_dir / "watch.log"
            created = root / "src" / "module.py"
            created.parent.mkdir(parents=True)
            created.write_text("def run():\n    return True\n", encoding="utf-8")

            class FakeHandlerBase:
                pass

            class FakeObserver:
                def __init__(self, callback) -> None:
                    self.callback = callback
                    self.handler = None

                def schedule(
                    self, event_handler: object, path: str, recursive: bool = False
                ) -> None:
                    _ = path
                    _ = recursive
                    self.handler = event_handler

                def start(self) -> None:
                    assert self.handler is not None
                    self.callback(self.handler)

                def stop(self) -> None:
                    return None

                def join(self) -> None:
                    return None

            def observer_factory():
                return FakeObserver(
                    lambda handler: handler.on_created(
                        SimpleNamespace(is_directory=False, src_path=str(created))
                    )
                )

            with (
                patch(
                    "vibelign.core.watch_engine._import_watchdog_classes",
                    return_value=(FakeHandlerBase, observer_factory),
                ),
                patch(
                    "vibelign.core.watch_engine.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                run_watch({"root": str(root), "write_log": True, "auto_fix": True})

            text = created.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: MODULE_START", text)
            self.assertIn("ANCHOR: MODULE_RUN_START", text)
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("[auto-fix] 앵커 삽입: src/module.py", log_text)

    def test_run_watch_on_moved_replaces_old_state_with_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            state_path = vg_dir / "watch_state.json"
            project_map_path = vg_dir / "project_map.json"
            src = root / "src" / "old.py"
            dest = root / "src" / "new.py"
            src.parent.mkdir(parents=True)
            save_state(
                state_path,
                {
                    "src/old.py": FileSnapshot(
                        path="src/old.py", lines=1, sha1="deadbeef"
                    )
                },
            )
            project_map_path.write_text("{}\n", encoding="utf-8")
            dest.write_text("print('moved')\n", encoding="utf-8")

            class FakeHandlerBase:
                pass

            class FakeTimer:
                def __init__(self, _delay: float, callback):
                    self._callback = callback

                def start(self) -> None:
                    return None

                def cancel(self) -> None:
                    return None

                def fire(self) -> None:
                    self._callback()

            class FakeObserver:
                def __init__(self, callback) -> None:
                    self.callback = callback
                    self.handler = None

                def schedule(
                    self, event_handler: object, path: str, recursive: bool = False
                ) -> None:
                    _ = path
                    _ = recursive
                    self.handler = event_handler

                def start(self) -> None:
                    assert self.handler is not None
                    self.callback(self.handler)
                    timer = getattr(self.handler, "global_timer", None)
                    if timer is not None:
                        timer.fire()

                def stop(self) -> None:
                    return None

                def join(self) -> None:
                    return None

            def observer_factory():
                return FakeObserver(
                    lambda handler: handler.on_moved(
                        SimpleNamespace(
                            is_directory=False,
                            src_path=str(src),
                            dest_path=str(dest),
                        )
                    )
                )

            with (
                patch(
                    "vibelign.core.watch_engine._import_watchdog_classes",
                    return_value=(FakeHandlerBase, observer_factory),
                ),
                patch("vibelign.core.watch_engine.threading.Timer", FakeTimer),
                patch(
                    "vibelign.core.watch_engine.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                run_watch({"root": str(root)})

            saved = load_state(state_path)
            self.assertNotIn("src/old.py", saved)
            self.assertIn("src/new.py", saved)
            project_map = project_map_path.read_text(encoding="utf-8")
            self.assertIn('"src/new.py"', project_map)
            self.assertNotIn('"src/old.py"', project_map)

    def test_run_watch_logs_delete_when_file_is_deleted_before_state_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            state_path = vg_dir / "watch_state.json"
            log_path = vg_dir / "watch.log"
            project_map_path = vg_dir / "project_map.json"
            created = root / "src" / "temp.py"
            created.parent.mkdir(parents=True)
            created.write_text("print('hello')\n", encoding="utf-8")
            project_map_path.write_text("{}\n", encoding="utf-8")

            class FakeHandlerBase:
                pass

            class FakeTimer:
                def __init__(self, _delay: float, callback):
                    self._callback = callback

                def start(self) -> None:
                    return None

                def cancel(self) -> None:
                    return None

                def fire(self) -> None:
                    self._callback()

            class FakeObserver:
                def __init__(self, callback) -> None:
                    self.callback = callback
                    self.handler = None

                def schedule(
                    self, event_handler: object, path: str, recursive: bool = False
                ) -> None:
                    _ = path
                    _ = recursive
                    self.handler = event_handler

                def start(self) -> None:
                    assert self.handler is not None
                    self.callback(self.handler)
                    timer = getattr(self.handler, "global_timer", None)
                    if timer is not None:
                        timer.fire()

                def stop(self) -> None:
                    return None

                def join(self) -> None:
                    return None

            def observer_factory():
                return FakeObserver(
                    lambda handler: handler.on_created(
                        SimpleNamespace(is_directory=False, src_path=str(created))
                    )
                )

            real_save_state = save_state
            delete_fired = False

            def save_state_with_delete(
                path: Path, state: dict[str, FileSnapshot]
            ) -> None:
                nonlocal delete_fired
                if not delete_fired:
                    delete_fired = True
                    created.unlink()
                    assert observer.handler is not None
                    handler = cast(Any, observer.handler)
                    handler.on_deleted(
                        SimpleNamespace(is_directory=False, src_path=str(created))
                    )
                real_save_state(path, state)

            observer = observer_factory()

            with (
                patch(
                    "vibelign.core.watch_engine._import_watchdog_classes",
                    return_value=(FakeHandlerBase, lambda: observer),
                ),
                patch("vibelign.core.watch_engine.threading.Timer", FakeTimer),
                patch(
                    "vibelign.core.watch_state.save_state",
                    side_effect=save_state_with_delete,
                ),
                patch(
                    "vibelign.core.watch_engine.time.sleep",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                run_watch({"root": str(root), "write_log": True})

            saved = load_state(state_path)
            self.assertEqual({}, saved)
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn('"message": "src/temp.py 삭제됨"', log_text)
            project_map = project_map_path.read_text(encoding="utf-8")
            self.assertIn('"file_count": 0', project_map)


if __name__ == "__main__":
    _ = unittest.main()
