import json
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from vibelign.commands.doctor_cmd import run_doctor


@dataclass
class DoctorArgsLike:
    json: bool
    strict: bool


class DoctorCmdWrapperTest(unittest.TestCase):
    def test_run_doctor_delegates_text_output_building(self) -> None:
        with patch(
            "vibelign.commands.doctor_cmd.build_legacy_doctor_output",
            return_value=("legacy text\n", False),
        ) as mocked:
            with patch("vibelign.commands.doctor_cmd.print_ai_response") as renderer:
                run_doctor(DoctorArgsLike(json=False, strict=False))

        mocked.assert_called_once()
        renderer.assert_called_once_with("legacy text\n")

    def test_run_doctor_delegates_json_output_building(self) -> None:
        payload = json.dumps({"score": 1}, ensure_ascii=False)
        with patch(
            "vibelign.commands.doctor_cmd.build_legacy_doctor_output",
            return_value=(payload, True),
        ) as mocked:
            with patch("vibelign.commands.doctor_cmd.print") as printer:
                run_doctor(DoctorArgsLike(json=True, strict=True))

        mocked.assert_called_once()
        printer.assert_called_once_with(payload)


if __name__ == "__main__":
    _ = unittest.main()
