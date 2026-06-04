import importlib.util
import unittest

from vibelign.core import IntentIR as ExportedIntentIR
from vibelign.core import JsonObject
from vibelign.core.intent_ir import IntentIR


class CoreModelExportsTest(unittest.TestCase):
    def test_intent_ir_export_uses_dedicated_module_class(self):
        self.assertIs(ExportedIntentIR, IntentIR)

    def test_supported_json_export_remains_available(self):
        payload: JsonObject = {"ok": True}
        self.assertEqual(payload["ok"], True)

    def test_patch_core_modules_are_removed(self):
        removed = [
            "vibelign.core.codespeak",
            "vibelign.core.ai_codespeak",
            "vibelign.core.patch_suggester",
            "vibelign.core.strict_patch",
            "vibelign.core.patch_contract",
            "vibelign.core.patch_validation",
            "vibelign.patch",
        ]
        for name in removed:
            self.assertIsNone(importlib.util.find_spec(name), name)

    def test_patch_models_are_not_exported(self):
        import vibelign.core as core

        for name in ["PatchContract", "PatchPlan", "PatchStep", "TargetResolution"]:
            self.assertFalse(hasattr(core, name), name)


if __name__ == "__main__":
    _ = unittest.main()
