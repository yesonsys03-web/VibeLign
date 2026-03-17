from importlib import import_module
from pathlib import Path
from typing import Optional
import threading
import time


from vibelign.terminal_render import cli_print
print = cli_print

SOURCE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".rs",
    ".go",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".hpp",
    ".h",
}


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def run_watch(config):
    try:
        events_module = import_module("watchdog.events")
        observers_module = import_module("watchdog.observers")
        FileSystemEventHandler = events_module.FileSystemEventHandler
        Observer = observers_module.Observer
    except Exception as e:
        raise RuntimeError(
            "watch 모드를 사용하려면 'watchdog'을 설치해야 합니다. `pip install watchdog` 또는 `uv add watchdog`으로 설치하세요."
        ) from e

    from vibelign.core.watch_rules import classify_event
    from vibelign.core.watch_state import (
        FileSnapshot,
        hash_text,
        load_state,
        save_state,
    )
    from vibelign.core.watch_reporter import emit

    class VibeLignWatchHandler(FileSystemEventHandler):
        def __init__(
            self,
            root: Path,
            state_path: Path,
            strict: bool,
            json_mode: bool,
            log_path: Optional[Path],
            debounce_ms: int = 800,
        ):
            super().__init__()
            self.root = root
            self.state_path = state_path
            self.strict = strict
            self.json_mode = json_mode
            self.log_path = log_path
            self.debounce_ms = debounce_ms
            self.state = load_state(state_path)
            self.last_seen = {}
            self.global_timer: Optional[threading.Timer] = None
            self.pending_changes: list[str] = []
            self._lock = threading.Lock()
            from vibelign.core.protected_files import get_protected

            self.protected = get_protected(root)

        def _eligible(self, path: Path) -> bool:
            return (
                path.is_file()
                and path.suffix.lower() in SOURCE_EXTS
                and ".git" not in path.parts
                and "__pycache__" not in path.parts
                and "node_modules" not in path.parts
                and "tests" not in path.parts
                and "docs" not in path.parts
            )

        def _debounced(self, path: Path) -> bool:
            now = time.time() * 1000
            key = str(path)
            prev = self.last_seen.get(key, 0)
            self.last_seen[key] = now
            return (now - prev) < self.debounce_ms

        def _schedule_global_update(self, rel_path: str) -> None:
            with self._lock:
                self.pending_changes.append(rel_path)
                if self.global_timer is not None:
                    self.global_timer.cancel()
                self.global_timer = threading.Timer(
                    self.debounce_ms / 1000.0,
                    self._run_global_update,
                )
                self.global_timer.start()

        def _run_global_update(self) -> None:
            with self._lock:
                changed = list(dict.fromkeys(self.pending_changes))
                self.pending_changes.clear()
                self.global_timer = None
            if not changed:
                return
            self._refresh_project_map(changed)

        def _refresh_project_map(self, changed: list[str]) -> None:
            import json
            from datetime import datetime, timezone
            from vibelign.core.meta_paths import MetaPaths
            from vibelign.core.scan_cache import incremental_scan

            meta = MetaPaths(self.root)
            if not meta.project_map_path.exists():
                return
            try:
                payload = json.loads(
                    meta.project_map_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                return

            emit(
                {
                    "level": "OK",
                    "path": "",
                    "message": f"⏳ 코드맵 갱신 중... (파일 {len(changed)}개 변경)",
                    "why": "",
                    "action": "",
                },
                json_mode=self.json_mode,
                log_path=self.log_path,
            )

            try:
                scan = incremental_scan(
                    self.root,
                    meta.scan_cache_path,
                    invalidated=set(changed),
                )
                anchor_index = {
                    rel: data["anchors"]
                    for rel, data in scan.items()
                    if data.get("anchors")
                }
                files = {
                    rel: {
                        "category": data["category"],
                        "anchors": data["anchors"],
                        "line_count": data["line_count"],
                    }
                    for rel, data in scan.items()
                }
                payload["anchor_index"] = anchor_index
                payload["files"] = files
                payload["file_count"] = len(scan)
                payload["schema_version"] = 2
                payload["updated_at"] = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                tmp_path = meta.project_map_path.with_suffix(".tmp")
                tmp_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                tmp_path.replace(meta.project_map_path)

                # anchor_index.json도 최신 상태로 갱신
                anchor_index_payload = {
                    "schema_version": 1,
                    "anchors": anchor_index,
                    "files": {k: {"anchors": v} for k, v in anchor_index.items()},
                }
                ai_tmp = meta.anchor_index_path.with_suffix(".tmp")
                ai_tmp.write_text(
                    json.dumps(anchor_index_payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                ai_tmp.replace(meta.anchor_index_path)
            except Exception:
                return

            emit(
                {
                    "level": "OK",
                    "path": "",
                    "message": f"✅ 파일 {len(changed)}개 변경 감지 → 코드맵 자동 갱신 완료",
                    "why": "",
                    "action": "",
                },
                json_mode=self.json_mode,
                log_path=self.log_path,
            )

        def _process(self, src_path: str):
            path = Path(src_path)
            if not self._eligible(path) or self._debounced(path):
                return
            text = safe_read(path)
            if not text:
                return
            try:
                rel = str(path.relative_to(self.root))
            except Exception:
                rel = str(path)
            new_lines = len(text.splitlines())
            new_sha = hash_text(text)
            old = self.state.get(rel)
            old_lines = old.lines if old else None
            if old and old.sha1 == new_sha:
                return
            warnings = classify_event(
                path,
                text,
                old_lines,
                new_lines,
                strict=self.strict,
                protected_files=self.protected,
            )
            if not warnings:
                emit(
                    {
                        "level": "OK",
                        "path": rel,
                        "message": f"{rel} 변경됨",
                        "why": "",
                        "action": "",
                    },
                    json_mode=self.json_mode,
                    log_path=self.log_path,
                )
            else:
                for item in warnings:
                    item["path"] = rel
                    emit(item, json_mode=self.json_mode, log_path=self.log_path)
            self.state[rel] = FileSnapshot(rel, new_lines, new_sha)
            save_state(self.state_path, self.state)
            self._schedule_global_update(rel)

        def on_modified(self, event):
            if not event.is_directory:
                self._process(event.src_path)

        def on_created(self, event):
            if not event.is_directory:
                self._process(event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                self._process(event.dest_path)

    root = Path(config["root"])
    strict = bool(config.get("strict", False))
    json_mode = bool(config.get("json", False))
    debounce_ms = int(config.get("debounce_ms", 800))
    write_log = bool(config.get("write_log", False))
    vg_dir = root / ".vibelign"
    state_path = vg_dir / "watch_state.json"
    log_path = vg_dir / "watch.log" if write_log else None

    print("프로젝트 감시를 시작합니다...")
    print(f"루트 경로: {root}")
    print(f"엄격 모드: {strict}")
    print(f"JSON 모드: {json_mode}")
    print(f"로그 저장: {write_log}")
    print("파일이 변경되면 코드맵이 자동으로 갱신됩니다. (Ctrl+C로 종료)")

    handler = VibeLignWatchHandler(
        root, state_path, strict, json_mode, log_path, debounce_ms
    )
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
