import ast
import unittest
from pathlib import Path


def hidden_imports_from_spec() -> list[str]:
    module = ast.parse(Path("vib.spec").read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "hidden_imports"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, list):
            raise AssertionError("hidden_imports must be a list")
        return [str(item) for item in value]
    raise AssertionError("hidden_imports assignment not found in vib.spec")


class PyInstallerSpecTest(unittest.TestCase):
    def test_vib_runtime_bundles_all_mcp_handler_modules(self) -> None:
        imports = set(hidden_imports_from_spec())
        handler_modules = {
            f"vibelign.mcp.{path.stem}"
            for path in Path("vibelign/mcp").glob("mcp_*_handlers.py")
        }

        missing = sorted(handler_modules - imports)

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
