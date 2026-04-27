import importlib.util
import io
import json
import sys
import types
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(path)]
    sys.modules[name] = pkg


_stub("vibelign", ROOT / "vibelign")
_stub("vibelign.core", ROOT / "vibelign" / "core")
_load("vibelign.core.keys_store", ROOT / "vibelign" / "core" / "keys_store.py")
_load("vibelign.core.http_retry", ROOT / "vibelign" / "core" / "http_retry.py")
enhance = _load(
    "vibelign.core.docs_ai_enhance",
    ROOT / "vibelign" / "core" / "docs_ai_enhance.py",
)


class AIEnhanceParsingTest(unittest.TestCase):
    def test_builds_prompt_with_source_text(self):
        prompt = enhance.build_prompt("# Title\n\nbody.")
        self.assertIn("Title", prompt)
        self.assertIn("body.", prompt)
        self.assertIn("tldr_one_liner", prompt)

    def test_parses_valid_anthropic_response(self):
        fake_body = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "tldr_one_liner": "짧은 요약",
                        "key_rules": ["규칙1"],
                        "success_criteria": ["기준1"],
                        "edge_cases": ["예외1"],
                        "components": ["파서 — AST"],
                    }),
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        parsed = enhance.parse_anthropic_response(fake_body)
        self.assertEqual(parsed["fields"]["tldr_one_liner"], "짧은 요약")
        self.assertEqual(parsed["tokens_input"], 100)
        self.assertEqual(parsed["tokens_output"], 50)

    def test_rejects_non_json_content(self):
        fake_body = {"content": [{"type": "text", "text": "not json"}]}
        with self.assertRaises(ValueError):
            enhance.parse_anthropic_response(fake_body)

    def test_formats_gemini_http_error_with_response_body(self):
        body = json.dumps({
            "error": {
                "status": "INVALID_ARGUMENT",
                "message": "model does not support responseMimeType",
            }
        }).encode("utf-8")
        error = urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent",
            400,
            "Bad Request",
            {},
            io.BytesIO(body),
        )

        message = enhance._format_http_error("Gemini", "test-model", error)

        self.assertIn("HTTP 400 Bad Request", message)
        self.assertIn("model=test-model", message)
        self.assertIn("INVALID_ARGUMENT", message)
        self.assertIn("responseMimeType", message)


if __name__ == "__main__":
    unittest.main()
