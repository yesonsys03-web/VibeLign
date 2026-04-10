import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from email.message import Message

import urllib.request

from vibelign.core import http_retry


class HttpRetryTest(unittest.TestCase):
    def test_retry_after_from_headers_reads_numeric_header(self) -> None:
        delay = http_retry._retry_after_from_headers({"Retry-After": "3.5"})
        self.assertEqual(delay, 3.5)

    def test_retry_delay_from_gemini_error_body_parses_seconds_suffix(self) -> None:
        body = json.dumps(
            {
                "error": {
                    "code": 429,
                    "details": [
                        {
                            "@type": "google.rpc.RetryInfo",
                            "retryDelay": "46s",
                        }
                    ],
                }
            }
        ).encode()
        delay = http_retry._retry_delay_from_gemini_error_body(body)
        self.assertEqual(delay, 46.0)

    def test_urlopen_read_with_retry_succeeds_after_one_429(self) -> None:
        ok_payload = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        ).encode()

        err_fp = io.BytesIO(
            json.dumps(
                {
                    "error": {
                        "details": [{"retryDelay": "0.01s"}],
                    }
                }
            ).encode()
        )

        class OkResp:
            def read(self) -> bytes:
                return ok_payload

            def __enter__(self) -> "OkResp":
                return self

            def __exit__(self, *args: object) -> bool:
                return False

        headers = Message()

        err = urllib.error.HTTPError(
            "https://example.com",
            429,
            "Too Many",
            headers,
            err_fp,
        )

        with (
            patch("urllib.request.urlopen", side_effect=[err, OkResp()]) as m,
            patch("vibelign.core.http_retry.time.sleep"),
        ):
            req = urllib.request.Request(
                "https://example.com",
                data=b"{}",
                method="POST",
            )
            out = http_retry.urlopen_read_with_retry(
                req,
                timeout=5,
                max_attempts=4,
                base_delay=0.01,
                max_delay=1.0,
            )
        self.assertEqual(out, ok_payload)
        self.assertEqual(m.call_count, 2)


if __name__ == "__main__":
    unittest.main()
