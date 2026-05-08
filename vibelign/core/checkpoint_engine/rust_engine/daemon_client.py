# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_DAEMON_CLIENT_START ===
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import cast

from vibelign.core.checkpoint_engine.rust_engine.discovery import find_rust_engine
from vibelign.core.checkpoint_engine.rust_engine.transport_oneshot import (
    RustEngineResult,
)
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

_DAEMON_STARTUP_TIMEOUT_SECONDS = 2.0
_DAEMON_LOG_MAX_BYTES = 10 * 1024 * 1024
_DAEMON_LOG_BACKUPS = 3


def call_rust_engine_daemon(
    root: Path,
    request: dict[str, object],
    timeout_seconds: int = 30,
    *,
    start_if_missing: bool = False,
) -> RustEngineResult:
    if not _daemon_transport_supported():
        return _unsupported_daemon_transport_result()

    result = _send_daemon_request(root, request, timeout_seconds)
    if result.error_code == "RUST_ENGINE_DAEMON_UNAVAILABLE":
        retry_result = _send_daemon_request(root, request, timeout_seconds)
        if retry_result.ok or retry_result.error_code != "RUST_ENGINE_DAEMON_UNAVAILABLE":
            return retry_result
    if (
        result.error_code == "RUST_ENGINE_DAEMON_UNAVAILABLE"
        and start_if_missing
    ):
        started = start_rust_engine_daemon(root, timeout_seconds=timeout_seconds)
        if not started.ok:
            return started
        return _send_daemon_request(root, request, timeout_seconds)
    return result


def shutdown_rust_engine_daemon(root: Path, timeout_seconds: int = 30) -> RustEngineResult:
    return _send_daemon_request(
        root,
        {"command": "shutdown"},
        timeout_seconds,
        require_payload=False,
    )


def healthcheck_rust_engine_daemon(root: Path, timeout_seconds: int = 1) -> RustEngineResult:
    return _send_daemon_request(root, {"command": "engine_info"}, timeout_seconds)


def is_rust_engine_daemon_running(root: Path, timeout_seconds: int = 1) -> bool:
    return healthcheck_rust_engine_daemon(root, timeout_seconds=timeout_seconds).ok


def start_rust_engine_daemon(root: Path, timeout_seconds: int = 30) -> RustEngineResult:
    if not _daemon_transport_supported():
        return _unsupported_daemon_transport_result()

    if is_rust_engine_daemon_running(root, timeout_seconds=1):
        return RustEngineResult(
            ok=True,
            payload={"status": "ok", "result": "daemon_started"},
        )

    availability = find_rust_engine(root)
    if not availability.available or availability.binary_path is None:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code=availability.code or "RUST_ENGINE_UNAVAILABLE",
            error_message=availability.reason or "rust engine unavailable",
        )

    log_handle = None
    try:
        log_path = root / ".vibelign" / "engine.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_daemon_log(log_path)
        log_handle = log_path.open("ab")
        process = subprocess.Popen(
            [str(availability.binary_path), "--daemon", "--root", str(root)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=log_handle,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
            start_new_session=os.name != "nt",
        )
    except (FileNotFoundError, OSError) as error:
        if log_handle is not None:
            log_handle.close()
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_STARTUP_FAILED",
            error_message=str(error),
        )

    socket_path = root / ".vibelign" / "engine.sock"
    pid_path = root / ".vibelign" / "engine.pid"
    deadline = time.monotonic() + min(
        max(float(timeout_seconds), 0.1), _DAEMON_STARTUP_TIMEOUT_SECONDS
    )
    while time.monotonic() < deadline:
        if _daemon_artifacts_ready(socket_path, pid_path):
            if log_handle is not None:
                log_handle.close()
            return RustEngineResult(
                ok=True,
                payload={"status": "ok", "result": "daemon_started"},
            )
        exit_code = process.poll()
        if exit_code is not None:
            if log_handle is not None:
                log_handle.close()
            return RustEngineResult(
                ok=False,
                payload={},
                error_code="RUST_ENGINE_DAEMON_STARTUP_FAILED",
                error_message=f"rust engine daemon exited during startup: {exit_code}",
            )
        time.sleep(0.02)

    if process.poll() is None:
        process.terminate()
    if log_handle is not None:
        log_handle.close()
    return RustEngineResult(
        ok=False,
        payload={},
        error_code="RUST_ENGINE_DAEMON_STARTUP_TIMEOUT",
        error_message="rust engine daemon did not create socket before timeout",
    )


def _daemon_artifacts_ready(socket_path: Path, pid_path: Path) -> bool:
    return socket_path.exists() and pid_path.exists()


def _daemon_transport_supported() -> bool:
    return hasattr(socket, "AF_UNIX")


def _unsupported_daemon_transport_result() -> RustEngineResult:
    return RustEngineResult(
        ok=False,
        payload={},
        error_code="RUST_ENGINE_DAEMON_UNSUPPORTED",
        error_message=(
            "rust engine daemon transport is unsupported on this platform; "
            "Windows named pipe transport is not implemented yet"
        ),
    )


def _rotate_daemon_log(
    log_path: Path,
    *,
    max_bytes: int = _DAEMON_LOG_MAX_BYTES,
    backups: int = _DAEMON_LOG_BACKUPS,
) -> None:
    try:
        if max_bytes <= 0 or backups <= 0 or not log_path.exists():
            return
        if log_path.stat().st_size < max_bytes:
            return
        oldest = log_path.with_name(f"{log_path.name}.{backups}")
        if oldest.exists():
            oldest.unlink()
        for index in range(backups - 1, 0, -1):
            source = log_path.with_name(f"{log_path.name}.{index}")
            if source.exists():
                source.rename(log_path.with_name(f"{log_path.name}.{index + 1}"))
        log_path.rename(log_path.with_name(f"{log_path.name}.1"))
    except OSError:
        return


def _send_daemon_request(
    root: Path,
    request: dict[str, object],
    timeout_seconds: int,
    *,
    require_payload: bool = True,
) -> RustEngineResult:
    if not _daemon_transport_supported():
        return _unsupported_daemon_transport_result()

    request_id = uuid.uuid4().hex
    socket_path = root / ".vibelign" / "engine.sock"
    envelope = {"request_id": request_id, "payload": request}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout_seconds)
            client.connect(str(socket_path))
            client.sendall(json.dumps(envelope, ensure_ascii=False).encode("utf-8") + b"\n")
            response_text = _read_line(client)
    except (FileNotFoundError, OSError, TimeoutError, socket.timeout) as error:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_UNAVAILABLE",
            error_message=str(error),
        )

    try:
        response = cast(dict[str, object], json.loads(response_text or "{}"))
    except json.JSONDecodeError as error:
        return RustEngineResult(
            ok=False,
            payload={},
            error_code="RUST_ENGINE_DAEMON_INVALID_JSON",
            error_message=str(error),
        )

    if response.get("request_id") != request_id:
        return RustEngineResult(
            ok=False,
            payload=response,
            error_code="RUST_ENGINE_DAEMON_REQUEST_MISMATCH",
            error_message="daemon response request_id did not match request",
        )
    if response.get("status") != "ok":
        return RustEngineResult(
            ok=False,
            payload=response,
            error_code=str(response.get("code", "RUST_ENGINE_DAEMON_ERROR")),
            error_message=str(response.get("message", "rust engine daemon error")),
        )

    payload = response.get("payload")
    if not require_payload:
        return RustEngineResult(
            ok=True,
            payload={
                "status": "ok",
                "result": str(response.get("result", "daemon_control")),
            },
        )
    if not isinstance(payload, dict):
        return RustEngineResult(
            ok=False,
            payload=response,
            error_code="RUST_ENGINE_DAEMON_INVALID_PAYLOAD",
            error_message="daemon response payload was not an object",
        )
    if payload.get("status") == "ok":
        return RustEngineResult(ok=True, payload=cast(dict[str, object], payload))
    return RustEngineResult(
        ok=False,
        payload=cast(dict[str, object], payload),
        error_code=str(payload.get("code", "RUST_ENGINE_ERROR")),
        error_message=str(payload.get("message", "rust engine error")),
    )


def _read_line(client: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        chunk = client.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    data = b"".join(chunks)
    line = data.split(b"\n", 1)[0]
    return line.decode("utf-8")


# === ANCHOR: CHECKPOINT_ENGINE_RUST_ENGINE_DAEMON_CLIENT_END ===
