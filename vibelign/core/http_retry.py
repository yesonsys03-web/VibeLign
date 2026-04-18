# === ANCHOR: HTTP_RETRY_START ===
"""HTTP(S) 요청 지수 백오프 재시도 (Gemini 등 429/5xx).

`Retry-After` 헤더와 Google `generateContent` 오류 JSON의 `retryDelay`(예: \"46s\")를 우선한다.
환경변수(선택): `GEMINI_HTTP_MAX_ATTEMPTS`, `GEMINI_HTTP_RETRY_BASE`, `GEMINI_HTTP_RETRY_CAP`.
"""

from __future__ import annotations

import json
import os
import random
import ssl
import time
from collections.abc import Mapping
import urllib.error
import urllib.request
from email.message import Message


# certifi SSL context (macOS GUI 앱 등 시스템 인증서 미포함 환경 대응)
def _make_ssl_ctx() -> ssl.SSLContext | None:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


_SSL_CTX = _make_ssl_ctx()


# === ANCHOR: HTTP_RETRY__ENV_INT_START ===
def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


# === ANCHOR: HTTP_RETRY__ENV_INT_END ===


# === ANCHOR: HTTP_RETRY__ENV_FLOAT_START ===
def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.1, float(raw))
    except ValueError:
        return default


# === ANCHOR: HTTP_RETRY__ENV_FLOAT_END ===


# === ANCHOR: HTTP_RETRY__RETRY_AFTER_FROM_HEADERS_START ===
def _retry_after_from_headers(
    headers: Message[str, str] | Mapping[str, str] | None,
) -> float | None:
    if headers is None:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


# === ANCHOR: HTTP_RETRY__RETRY_AFTER_FROM_HEADERS_END ===


# === ANCHOR: HTTP_RETRY__RETRY_DELAY_FROM_GEMINI_ERROR_BODY_START ===
def _retry_delay_from_gemini_error_body(body: bytes) -> float | None:
    try:
        data = json.loads(body.decode("utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    err = data.get("error")
    if not isinstance(err, dict):
        return None
    details = err.get("details")
    if not isinstance(details, list):
        return None
    for item in details:
        if not isinstance(item, dict):
            continue
        delay = item.get("retryDelay")
        if not isinstance(delay, str):
            continue
        s = delay.strip()
        if s.endswith("s"):
            s = s[:-1].strip()
        try:
            return float(s)
        except ValueError:
            continue
    return None


# === ANCHOR: HTTP_RETRY__RETRY_DELAY_FROM_GEMINI_ERROR_BODY_END ===


# === ANCHOR: HTTP_RETRY__COMPUTE_BACKOFF_WAIT_START ===
def _compute_backoff_wait(
    attempt: int,
    base_delay: float,
    max_delay: float,
    jitter_ratio: float = 0.12,
    # === ANCHOR: HTTP_RETRY__COMPUTE_BACKOFF_WAIT_END ===
) -> float:
    raw = min(max_delay, base_delay * (2**attempt))
    jitter = 1.0 + random.uniform(-jitter_ratio, jitter_ratio)
    return max(0.25, min(max_delay, raw * jitter))


# === ANCHOR: HTTP_RETRY_URLOPEN_READ_WITH_RETRY_START ===
def urlopen_read_with_retry(
    request: urllib.request.Request,
    *,
    timeout: float = 60,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
    # === ANCHOR: HTTP_RETRY_URLOPEN_READ_WITH_RETRY_END ===
) -> bytes:
    """`urllib.request.urlopen` 후 본문을 읽어 반환. 429·502·503·504에 지수 백오프로 재시도."""
    attempts = max_attempts or _env_int("GEMINI_HTTP_MAX_ATTEMPTS", 6)
    base = (
        base_delay
        if base_delay is not None
        else _env_float("GEMINI_HTTP_RETRY_BASE", 1.5)
    )
    cap = (
        max_delay
        if max_delay is not None
        else _env_float("GEMINI_HTTP_RETRY_CAP", 120.0)
    )

    last_exc: BaseException | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=_SSL_CTX
            ) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code not in (429, 502, 503, 504) or attempt >= attempts - 1:
                raise
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            wait = _retry_after_from_headers(e.headers)
            if wait is None:
                wait = _retry_delay_from_gemini_error_body(body)
            if wait is None:
                wait = _compute_backoff_wait(attempt, base, cap)
            else:
                # 서버가 Retry-After / retryDelay 를 지정한 경우에는 지터를 걸지 않는다.
                # Why: 서버가 지정한 최소 대기값 아래로 지터가 당기면 다시 429 를 받는다.
                wait = max(0.25, min(cap, wait))
            time.sleep(wait)
        except urllib.error.URLError as e:
            last_exc = e
            if attempt >= attempts - 1:
                raise
            time.sleep(_compute_backoff_wait(attempt, base, cap))

    raise RuntimeError(
        "urlopen_read_with_retry: exhausted without result"
    ) from last_exc


# === ANCHOR: HTTP_RETRY_END ===
