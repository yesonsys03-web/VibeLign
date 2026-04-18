import unittest

from vibelign.__main__ import main as package_main
from vibelign.cli import main as cli_main


class MainEntrypointTest(unittest.TestCase):
    def test_python_module_entrypoint_matches_vibelign_cli(self) -> None:
        self.assertIs(package_main, cli_main)


if __name__ == "__main__":
    _ = unittest.main()
