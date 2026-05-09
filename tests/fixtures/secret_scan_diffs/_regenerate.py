"""Regenerate .expected.json goldens by running Python scan_unified_diff_for_secrets.

Run from repo root: `uv run python tests/fixtures/secret_scan_diffs/_regenerate.py`.
Python output is the source of truth; Rust port must match.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from vibelign.core.secret_scan import scan_unified_diff_for_secrets


_PATH_HINT_OVERRIDES: dict[str, str] = {
    "10_unicode_path_and_body.diff": "services/도우미_😀.py",
}


def _path_hint_for(diff_name: str) -> str:
    override = _PATH_HINT_OVERRIDES.get(diff_name)
    if override is not None:
        return override
    return diff_name.removesuffix(".diff") + ".py"


def main() -> int:
    fixtures_dir = Path(__file__).parent
    for diff_path in sorted(fixtures_dir.glob("*.diff")):
        diff_text = diff_path.read_text(encoding="utf-8")
        path_hint = _path_hint_for(diff_path.name)
        findings = scan_unified_diff_for_secrets(diff_text, path_hint)
        expected_path = diff_path.with_suffix(".expected.json")
        expected_path.write_text(
            json.dumps(
                {
                    "path_hint": path_hint,
                    "findings": [asdict(finding) for finding in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {expected_path.name}: {len(findings)} finding(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
