# === ANCHOR: WATCH_ENGINE_START ===
import _thread
import json
import threading
import time
from importlib import import_module
from pathlib import Path
from typing import Protocol, TypedDict, cast


from vibelign.terminal_render import cli_print
from vibelign.core.watch_state import FileSnapshot

print = cli_print


class WatchConfig(TypedDict, total=False):
    root: str
    strict: bool
    json: bool
    debounce_ms: int
    write_log: bool


class WatchPayload(TypedDict, total=False):
    level: str
    path: str
    message: str
    why: str
    action: str


class _WatchdogHandlerBase:
    def __init__(self) -> None:
        pass


class _WatchdogObserver(Protocol):
    def schedule(
        self, event_handler: object, path: str, recursive: bool = False
    ) -> object: ...

    def start(self) -> object: ...

    def stop(self) -> object: ...

    def join(self) -> object: ...


class _WatchdogObserverFactory(Protocol):
    def __call__(self) -> _WatchdogObserver: ...


class _WatchSrcEvent(Protocol):
    is_directory: bool
    src_path: str


class _WatchMovedEvent(Protocol):
    is_directory: bool
    src_path: str
    dest_path: str


class _WatchPathLike(Protocol):
    @property
    def parts(self) -> tuple[str, ...]: ...

    @property
    def name(self) -> str: ...

    @property
    def suffix(self) -> str: ...

    def is_file(self) -> bool: ...


def _normalize_object_dict(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    source = cast(dict[object, object], raw)
    normalized: dict[str, object] = {}
    for key, value in source.items():
        normalized[str(key)] = value
    return normalized


def _config_text(config: WatchConfig, key: str, default: str) -> str:
    value = config.get(key, default)
    return str(value) if value else default


def _config_bool(config: WatchConfig, key: str, default: bool = False) -> bool:
    return bool(config.get(key, default))


def _config_int(config: WatchConfig, key: str, default: int) -> int:
    value = config.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def is_watchable_path(path: _WatchPathLike) -> bool:
    if not path.is_file():
        return False
    if any(part.lower() in WATCH_EXCLUDED_DIRS_LOWER for part in path.parts):
        return False
    if path.name.lower() in WATCH_EXCLUDED_NAMES_LOWER:
        return False
    if path.suffix.lower() in WATCH_EXCLUDED_SUFFIXES:
        return False
    return True


def is_watchable_event_path(path: Path) -> bool:
    if any(part.lower() in WATCH_EXCLUDED_DIRS_LOWER for part in path.parts):
        return False
    if path.name.lower() in WATCH_EXCLUDED_NAMES_LOWER:
        return False
    if path.suffix.lower() in WATCH_EXCLUDED_SUFFIXES:
        return False
    return True


def _import_watchdog_classes() -> tuple[
    type[_WatchdogHandlerBase], _WatchdogObserverFactory
]:
    events_module = import_module("watchdog.events")
    observers_module = import_module("watchdog.observers")
    handler_base = cast(
        type[_WatchdogHandlerBase], getattr(events_module, "FileSystemEventHandler")
    )
    observer_factory = cast(
        _WatchdogObserverFactory, getattr(observers_module, "Observer")
    )
    return handler_base, observer_factory


WATCH_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".pnpm-store",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".vibelign",
    "coverage",
    "target",
    "out",
    "bin",
    "obj",
}

WATCH_EXCLUDED_DIRS_LOWER = {part.lower() for part in WATCH_EXCLUDED_DIRS}

WATCH_EXCLUDED_NAMES = {".DS_Store", "Thumbs.db"}

WATCH_EXCLUDED_NAMES_LOWER = {name.lower() for name in WATCH_EXCLUDED_NAMES}

WATCH_EXCLUDED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svgz",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".pyc",
    ".o",
    ".a",
    ".wasm",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".mp4",
    ".mov",
    ".webm",
    ".mp3",
    ".wav",
    ".ogg",
    ".bin",
}


# === ANCHOR: WATCH_ENGINE_SAFE_READ_START ===
def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


# === ANCHOR: WATCH_ENGINE_SAFE_READ_END ===


# === ANCHOR: WATCH_ENGINE_HANDLE_DELETED_PATH_START ===
def handle_deleted_path(
    root: Path,
    state: dict[str, FileSnapshot],
    state_path: Path,
    src_path: str,
    *,
    json_mode: bool = False,
    log_path: Path | None = None,
) -> str | None:
    from vibelign.core.project_scan import relpath_str
    from vibelign.core.watch_reporter import emit
    from vibelign.core.watch_state import save_state

    path = Path(src_path)
    rel = relpath_str(root, path)
    existing = state.pop(rel, None)

    deleted_event: WatchPayload = {
        "level": "WARN",
        "path": rel,
        "message": f"{rel} 삭제됨",
        "why": "파일 삭제는 프로젝트 구조와 코드맵에 직접 영향을 줍니다.",
        "action": "삭제 의도가 맞는지 확인하고 필요하면 복원하거나 vib scan 으로 상태를 다시 확인하세요.",
    }
    emit(deleted_event, json_mode=json_mode, log_path=log_path)
    if existing is not None:
        save_state(state_path, state)
    return rel


# === ANCHOR: WATCH_ENGINE_HANDLE_DELETED_PATH_END ===


# === ANCHOR: WATCH_ENGINE_RUN_WATCH_START ===
def run_watch(config: WatchConfig) -> None:
    try:
        file_system_event_handler_base, observer_factory = _import_watchdog_classes()
    except Exception:
        from vibelign.core.auto_install import try_install_watchdog

        try_install_watchdog(print, print, print)
        try:
            file_system_event_handler_base, observer_factory = (
                _import_watchdog_classes()
            )
        except Exception as e:
            raise RuntimeError(
                "watch 모드를 사용하려면 'watchdog'을 설치해야 합니다. `pip install watchdog` 또는 `uv add watchdog`으로 설치하세요."
            ) from e

    from vibelign.core.watch_rules import classify_event
    from vibelign.core.project_scan import relpath_str
    from vibelign.core.watch_state import (
        FileSnapshot,
        hash_text,
        load_state,
        save_state,
    )
    from vibelign.core.watch_reporter import emit

    # === ANCHOR: WATCH_ENGINE_VIBELIGNWATCHHANDLER_START ===
    class VibeLignWatchHandler(file_system_event_handler_base):
        # === ANCHOR: WATCH_ENGINE___INIT___START ===
        def __init__(
            self,
            root: Path,
            state_path: Path,
            strict: bool,
            json_mode: bool,
            log_path: Path | None,
            debounce_ms: int = 800,
            # === ANCHOR: WATCH_ENGINE___INIT___END ===
        ):
            super().__init__()
            self.root: Path = root
            self.state_path: Path = state_path
            self.strict: bool = strict
            self.json_mode: bool = json_mode
            self.log_path: Path | None = log_path
            self.debounce_ms: int = debounce_ms
            self.state: dict[str, FileSnapshot] = load_state(state_path)
            self.last_seen: dict[str, float] = {}
            self.global_timer: threading.Timer | None = None
            self.pending_changes: list[str] = []
            self._lock: _thread.LockType = threading.Lock()
            from vibelign.core.protected_files import get_protected

            self.protected: set[str] = get_protected(root)

        # === ANCHOR: WATCH_ENGINE__ELIGIBLE_START ===
        def _eligible(self, path: Path) -> bool:
            return is_watchable_path(path)

        # === ANCHOR: WATCH_ENGINE__ELIGIBLE_END ===

        # === ANCHOR: WATCH_ENGINE__DEBOUNCED_START ===
        def _debounced(self, path: Path) -> bool:
            now = time.time() * 1000
            key = str(path)
            prev: float = self.last_seen.get(key, 0.0)
            self.last_seen[key] = now
            return (now - prev) < self.debounce_ms

        # === ANCHOR: WATCH_ENGINE__DEBOUNCED_END ===

        # === ANCHOR: WATCH_ENGINE__SCHEDULE_GLOBAL_UPDATE_START ===
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

        # === ANCHOR: WATCH_ENGINE__SCHEDULE_GLOBAL_UPDATE_END ===

        # === ANCHOR: WATCH_ENGINE__RUN_GLOBAL_UPDATE_START ===
        def _run_global_update(self) -> None:
            with self._lock:
                changed = list(dict.fromkeys(self.pending_changes))
                self.pending_changes.clear()
                self.global_timer = None
            if not changed:
                return
            self._refresh_project_map(changed)

        # === ANCHOR: WATCH_ENGINE__RUN_GLOBAL_UPDATE_END ===

        # === ANCHOR: WATCH_ENGINE__REFRESH_PROJECT_MAP_START ===
        def _refresh_project_map(self, changed: list[str]) -> None:
            from datetime import datetime, timezone
            from vibelign.core.meta_paths import MetaPaths
            from vibelign.core.scan_cache import incremental_scan

            meta = MetaPaths(self.root)
            if not meta.project_map_path.exists():
                return
            try:
                payload_raw = cast(
                    object,
                    json.loads(meta.project_map_path.read_text(encoding="utf-8")),
                )
            except (OSError, json.JSONDecodeError):
                return
            payload = _normalize_object_dict(payload_raw)
            if payload is None:
                return

            progress_event: WatchPayload = {
                "level": "OK",
                "path": "",
                "message": f"⏳ 코드맵 갱신 중... (파일 {len(changed)}개 변경)",
                "why": "",
                "action": "",
            }
            emit(progress_event, json_mode=self.json_mode, log_path=self.log_path)

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
                _ = tmp_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                _ = tmp_path.replace(meta.project_map_path)

                # anchor_index.json도 최신 상태로 갱신
                anchor_index_payload = {
                    "schema_version": 1,
                    "anchors": anchor_index,
                    "files": {k: {"anchors": v} for k, v in anchor_index.items()},
                }
                ai_tmp = meta.anchor_index_path.with_suffix(".tmp")
                _ = ai_tmp.write_text(
                    json.dumps(anchor_index_payload, indent=2, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
                _ = ai_tmp.replace(meta.anchor_index_path)
            except Exception:
                return

            done_event: WatchPayload = {
                "level": "OK",
                "path": "",
                "message": f"✅ 파일 {len(changed)}개 변경 감지 → 코드맵 자동 갱신 완료",
                "why": "",
                "action": "",
            }
            emit(done_event, json_mode=self.json_mode, log_path=self.log_path)

        # === ANCHOR: WATCH_ENGINE__REFRESH_PROJECT_MAP_END ===

        # === ANCHOR: WATCH_ENGINE__PROCESS_START ===
        def _process(self, src_path: str) -> None:
            path = Path(src_path)
            if not self._eligible(path) or self._debounced(path):
                return
            text = safe_read(path)
            if not text:
                return
            rel = relpath_str(self.root, path)
            new_lines = len(text.splitlines())
            new_sha = hash_text(text)
            old = self.state.get(rel)
            old_lines = old.lines if old else None
            if old and old.sha1 == new_sha:
                return
            warnings = cast(
                list[WatchPayload],
                classify_event(
                    path,
                    text,
                    old_lines,
                    new_lines,
                    strict=self.strict,
                    protected_files=self.protected,
                ),
            )
            if not warnings:
                ok_event: WatchPayload = {
                    "level": "OK",
                    "path": rel,
                    "message": f"{rel} 변경됨",
                    "why": "",
                    "action": "",
                }
                emit(ok_event, json_mode=self.json_mode, log_path=self.log_path)
            else:
                for item in warnings:
                    item["path"] = rel
                    emit(item, json_mode=self.json_mode, log_path=self.log_path)
            self.state[rel] = FileSnapshot(rel, new_lines, new_sha)
            save_state(self.state_path, self.state)
            # === ANCHOR: WATCH_ENGINE_VIBELIGNWATCHHANDLER_END ===
            self._schedule_global_update(rel)

        # === ANCHOR: WATCH_ENGINE__PROCESS_END ===

        # === ANCHOR: WATCH_ENGINE_ON_MODIFIED_START ===
        def on_modified(self, event: _WatchSrcEvent) -> None:
            if not event.is_directory:
                self._process(event.src_path)

        # === ANCHOR: WATCH_ENGINE_ON_MODIFIED_END ===

        # === ANCHOR: WATCH_ENGINE_ON_CREATED_START ===
        def on_created(self, event: _WatchSrcEvent) -> None:
            if not event.is_directory:
                self._process(event.src_path)

        # === ANCHOR: WATCH_ENGINE_ON_CREATED_END ===

        # === ANCHOR: WATCH_ENGINE_ON_MOVED_START ===
        def on_moved(self, event: _WatchMovedEvent) -> None:
            if not event.is_directory:
                src_path = Path(event.src_path)
                if is_watchable_event_path(src_path):
                    deleted_rel = handle_deleted_path(
                        self.root,
                        self.state,
                        self.state_path,
                        event.src_path,
                        json_mode=self.json_mode,
                        log_path=self.log_path,
                    )
                    if deleted_rel:
                        self._schedule_global_update(deleted_rel)
                self._process(event.dest_path)

        # === ANCHOR: WATCH_ENGINE_ON_MOVED_END ===

        # === ANCHOR: WATCH_ENGINE_ON_DELETED_START ===
        def on_deleted(self, event: _WatchSrcEvent) -> None:
            if not event.is_directory:
                path = Path(event.src_path)
                if is_watchable_event_path(path):
                    deleted_rel = handle_deleted_path(
                        self.root,
                        self.state,
                        self.state_path,
                        event.src_path,
                        json_mode=self.json_mode,
                        log_path=self.log_path,
                    )
                    if deleted_rel:
                        self._schedule_global_update(deleted_rel)

        # === ANCHOR: WATCH_ENGINE_ON_DELETED_END ===

    root = Path(_config_text(config, "root", "."))
    strict = _config_bool(config, "strict", False)
    json_mode = _config_bool(config, "json", False)
    debounce_ms = _config_int(config, "debounce_ms", 800)
    write_log = _config_bool(config, "write_log", False)
    vg_dir = root / ".vibelign"
    # === ANCHOR: WATCH_ENGINE_RUN_WATCH_END ===
    state_path = vg_dir / "watch_state.json"
    log_path = vg_dir / "watch.log" if write_log else None

    print("프로젝트 감시를 시작합니다...", flush=True)
    print(f"루트 경로: {root}", flush=True)
    print(f"엄격 모드: {strict}", flush=True)
    print(f"JSON 모드: {json_mode}", flush=True)
    print(f"로그 저장: {write_log}", flush=True)
    print("파일이 변경되면 코드맵이 자동으로 갱신됩니다. (Ctrl+C로 종료)", flush=True)

    handler = VibeLignWatchHandler(
        root, state_path, strict, json_mode, log_path, debounce_ms
    )
    observer = observer_factory()
    _ = observer.schedule(handler, str(root), recursive=True)
    _ = observer.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        _ = observer.stop()
    _ = observer.join()


# === ANCHOR: WATCH_ENGINE_END ===
