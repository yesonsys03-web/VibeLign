# === ANCHOR: FILE_LOCK_START ===
from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, cast


class _FileHandle(Protocol):
    def fileno(self) -> int: ...


@contextlib.contextmanager
def file_lock(path: Path, timeout_seconds: float = 5.0) -> Iterator[bool]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as handle:
        deadline = time.monotonic() + timeout_seconds
        while True:
            if _try_lock(handle):
                try:
                    yield True
                finally:
                    _unlock(handle)
                return
            if time.monotonic() >= deadline:
                yield False
                return
            time.sleep(0.05)


def _try_lock(handle: object) -> bool:
    file_handle = cast(_FileHandle, handle)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl

    try:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(handle: object) -> None:
    file_handle = cast(_FileHandle, handle)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError as exc:
            _ = exc
        return
    import fcntl

    try:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        _ = exc
# === ANCHOR: FILE_LOCK_END ===
