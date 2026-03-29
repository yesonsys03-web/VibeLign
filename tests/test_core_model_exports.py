import unittest

from vibelign.core import IntentIR as ExportedIntentIR
from vibelign.core import PatchContract as ExportedPatchContract
from vibelign.core import PatchPlan as ExportedPatchPlan
from vibelign.core import PatchStep as ExportedPatchStep
from vibelign.core.intent_ir import IntentIR
from vibelign.core.patch_contract import PatchContract
from vibelign.core.patch_plan import PatchPlan, PatchStep


class CoreModelExportsTest(unittest.TestCase):
    def test_intent_ir_export_uses_dedicated_module_class(self):
        self.assertIs(ExportedIntentIR, IntentIR)

    def test_patch_plan_export_uses_dedicated_module_class(self):
        self.assertIs(ExportedPatchPlan, PatchPlan)

    def test_patch_step_export_uses_dedicated_module_class(self):
        self.assertIs(ExportedPatchStep, PatchStep)

    def test_patch_contract_export_uses_dedicated_module_class(self):
        self.assertIs(ExportedPatchContract, PatchContract)


if __name__ == "__main__":
    _ = unittest.main()
