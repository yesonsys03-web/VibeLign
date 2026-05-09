"""Pin Python `scan_unified_diff_for_secrets` output to committed goldens.

Why: Rust port (`vibelign-core/src/secret_scan.rs`) verifies its parity against
`tests/fixtures/secret_scan_diffs/*.expected.json`. Without this test the goldens
silently go stale if Python's secret_scan refactors — making the Rust parity tests
a one-shot photograph rather than a living invariant.

Run `uv run python tests/fixtures/secret_scan_diffs/_regenerate.py` only when an
intentional Python contract change has been agreed.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from vibelign.core import secret_scan as secret_scan_module
from vibelign.core.secret_scan import (
    SecretFinding,
    _scan_unified_diff_routed,
    scan_unified_diff_for_secrets,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "secret_scan_diffs"


def _fixture_diffs() -> list[Path]:
    return sorted(path for path in _FIXTURES_DIR.glob("*.diff"))


@pytest.mark.parametrize("diff_path", _fixture_diffs(), ids=lambda path: path.name)
def test_python_scan_matches_committed_goldens(diff_path: Path) -> None:
    expected_path = diff_path.with_suffix(".expected.json")
    assert expected_path.exists(), f"missing golden: {expected_path.name}"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    findings = scan_unified_diff_for_secrets(
        diff_path.read_text(encoding="utf-8"),
        expected["path_hint"],
    )
    actual = [asdict(finding) for finding in findings]
    assert actual == expected["findings"]


def test_scan_unified_diff_routed_default_uses_python(tmp_path: Path) -> None:
    diff_text = (_FIXTURES_DIR / "02_high_confidence_aws.diff").read_text(encoding="utf-8")

    with patch.dict("os.environ", {"VIBELIGN_SECRET_SCAN_RUST": ""}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.scan_secrets_diff_with_rust"
    ) as rust_call:
        findings = _scan_unified_diff_routed(tmp_path, diff_text, "config/.env")

    assert len(findings) == 1
    assert findings[0].rule_id == "aws-access-key"
    rust_call.assert_not_called()


def test_scan_unified_diff_routed_uses_rust_when_opted_in(tmp_path: Path) -> None:
    diff_text = (_FIXTURES_DIR / "02_high_confidence_aws.diff").read_text(encoding="utf-8")
    rust_payload = [
        {"path": "config/.env", "rule_id": "aws-access-key", "line_number": 2, "snippet": "...MPLE"},
    ]

    with patch.dict("os.environ", {"VIBELIGN_SECRET_SCAN_RUST": "1"}, clear=False), patch.object(
        secret_scan_module, "scan_unified_diff_for_secrets"
    ) as python_fallback, patch(
        "vibelign.core.checkpoint_engine.rust_engine.scan_secrets_diff_with_rust",
        return_value=(rust_payload, None),
    ) as rust_call:
        findings = _scan_unified_diff_routed(tmp_path, diff_text, "config/.env")

    assert findings == [
        SecretFinding(path="config/.env", rule_id="aws-access-key", line_number=2, snippet="...MPLE"),
    ]
    rust_call.assert_called_once_with(tmp_path, diff_text, "config/.env")
    python_fallback.assert_not_called()


def test_scan_unified_diff_routed_falls_back_when_rust_warns(tmp_path: Path) -> None:
    diff_text = (_FIXTURES_DIR / "02_high_confidence_aws.diff").read_text(encoding="utf-8")

    with patch.dict("os.environ", {"VIBELIGN_SECRET_SCAN_RUST": "1"}, clear=False), patch(
        "vibelign.core.checkpoint_engine.rust_engine.scan_secrets_diff_with_rust",
        return_value=(None, "RUST_ENGINE_UNAVAILABLE"),
    ):
        findings = _scan_unified_diff_routed(tmp_path, diff_text, "config/.env")

    assert len(findings) == 1
    assert findings[0].rule_id == "aws-access-key"
    assert findings[0].snippet == "...MPLE"
