from pathlib import Path
import time

SOURCE_EXTS = {".py",".js",".ts",".jsx",".tsx",".rs",".go",".java",".cs",".cpp",".c",".hpp",".h"}

def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def run_watch(config):
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except Exception as e:
        raise RuntimeError("watch 모드를 사용하려면 'watchdog'을 설치해야 합니다. `pip install watchdog` 또는 `uv add watchdog`으로 설치하세요.") from e

    from vibeguard.core.watch_rules import classify_event
    from vibeguard.core.watch_state import FileSnapshot, hash_text, load_state, save_state
    from vibeguard.core.watch_reporter import emit

    class VibeGuardWatchHandler(FileSystemEventHandler):
        def __init__(self, root: Path, state_path: Path, strict: bool, json_mode: bool, log_path: Path | None, debounce_ms: int = 800):
            super().__init__()
            self.root = root
            self.state_path = state_path
            self.strict = strict
            self.json_mode = json_mode
            self.log_path = log_path
            self.debounce_ms = debounce_ms
            self.state = load_state(state_path)
            self.last_seen = {}
            from vibeguard.core.protected_files import get_protected
            self.protected = get_protected(root)

        def _eligible(self, path: Path) -> bool:
            return path.is_file() and path.suffix.lower() in SOURCE_EXTS and ".git" not in path.parts and "__pycache__" not in path.parts and "node_modules" not in path.parts and "tests" not in path.parts and "docs" not in path.parts

        def _debounced(self, path: Path) -> bool:
            now = time.time() * 1000
            key = str(path)
            prev = self.last_seen.get(key, 0)
            self.last_seen[key] = now
            return (now - prev) < self.debounce_ms

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
            warnings = classify_event(path, text, old_lines, new_lines, strict=self.strict, protected_files=self.protected)
            if not warnings:
                emit({"level": "OK", "path": rel, "message": f"{rel} 변경됨", "why": "", "action": ""}, json_mode=self.json_mode, log_path=self.log_path)
            else:
                for item in warnings:
                    item["path"] = rel
                    emit(item, json_mode=self.json_mode, log_path=self.log_path)
            self.state[rel] = FileSnapshot(rel, new_lines, new_sha)
            save_state(self.state_path, self.state)

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
    vg_dir = root / ".vibeguard"
    state_path = vg_dir / "watch_state.json"
    log_path = vg_dir / "watch.log" if write_log else None

    print("프로젝트 감시를 시작합니다...")
    print(f"루트 경로: {root}")
    print(f"엄격 모드: {strict}")
    print(f"JSON 모드: {json_mode}")
    print(f"로그 저장: {write_log}")

    handler = VibeGuardWatchHandler(root, state_path, strict, json_mode, log_path, debounce_ms)
    observer = Observer()
    observer.schedule(handler, str(root), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
