import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from vibelign.core.patch_suggester import suggest_patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PROJECT = REPO_ROOT / "tests" / "benchmark" / "sample_project"
SCENARIOS_PATH = REPO_ROOT / "tests" / "benchmark" / "scenarios.json"

# Pinned anchor intents so the test is hermetic. `vib anchor --auto` calls an
# LLM to generate intents, which is non-deterministic; we let it insert the
# markers + build anchor_index.json (both deterministic), then overwrite
# anchor_meta.json with this fixture so the patch-ranking assertions are
# reproducible across machines and runs.
_PINNED_INTENTS: dict[str, str] = {
    "DATABASE_INIT_DB": "데이터를 저장할 빈 공간을 처음 준비합니다.",
    "DATABASE_CREATE_USER": "회원 정보를 새로 만들어 명부에 등록합니다.",
    "DATABASE_FIND_USER_BY_EMAIL": "이메일로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_FIND_USER_BY_ID": "고유 번호로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_UPDATE_USER": "회원의 등록 정보를 최신으로 수정합니다.",
    "DATABASE_UPDATE_LOGIN_ATTEMPTS": "로그인 시도 횟수를 기록하고 업데이트합니다.",
    "AUTH__HASH_PASSWORD": "비밀번호를 안전하게 암호로 바꿉니다.",
    "AUTH__GENERATE_TOKEN": "사용자 인증을 위한 암호 키를 만듭니다.",
    "AUTH_LOGIN_USER": "이메일과 비밀번호로 로그인을 처리합니다.",
    "AUTH_REGISTER_USER": "새로운 사용자의 회원가입을 처리합니다.",
    "APP_MAIN": "프로그램을 실행하고 서버를 시작합니다.",
    "USERS_GET_USER_PROFILE": "공개 가능한 사용자 정보를 가져옵니다.",
    "USERS_UPDATE_USER_PROFILE": "사용자의 이름과 소개글을 수정합니다.",
    "VALIDATORS_VALIDATE_EMAIL": "이메일 주소 형식이 올바른지 확인합니다.",
    "VALIDATORS_VALIDATE_EMAIL_DOMAIN": "허용된 이메일 도메인인지 확인합니다.",
    "VALIDATORS_VALIDATE_PASSWORD": "비밀번호가 조건에 맞는지 확인합니다.",
    "SIGNUP_RENDER_SIGNUP_FORM": "회원가입 화면을 보여줄 양식을 만듭니다.",
    "SIGNUP_HANDLE_SIGNUP": "입력한 회원가입 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_FORM": "로그인 화면을 보여줄 양식을 만듭니다.",
    "LOGIN_HANDLE_LOGIN": "입력한 로그인 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_ERROR": "로그인 실패 시 오류 메시지를 보여줍니다.",
    "PROFILE_RENDER_PROFILE": "사용자 프로필 화면을 보여줄 양식을 만듭니다.",
    "PROFILE_HANDLE_PROFILE_UPDATE": "수정된 프로필 정보를 받아 저장합니다.",
    "CONFIG": "프로그램 설정 값을 모아 놓은 곳입니다.",
}


def _prepare_sandbox(tmp: Path) -> Path:
    """Copy sample_project into tmp, insert anchors via `vib anchor --auto`,
    then overwrite anchor_meta.json with pinned intents.

    Returns the sandbox root path.
    """
    dst = tmp / "project"
    shutil.copytree(SAMPLE_PROJECT, dst)
    subprocess.run(
        ["vib", "start"],
        cwd=dst,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["vib", "anchor", "--auto"],
        cwd=dst,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    meta_path = dst / ".vibelign" / "anchor_meta.json"
    meta_path.write_text(
        json.dumps(
            {name: {"intent": text} for name, text in _PINNED_INTENTS.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return dst


class PatchAccuracyScenarioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = _prepare_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = {s["id"]: s for s in json.load(fh)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _run(self, scenario_id: str, *, use_ai: bool = False):
        sc = self.scenarios[scenario_id]
        return suggest_patch(self.sandbox, sc["request"], use_ai=use_ai)

    def test_change_error_msg_selects_handle_login(self):
        result = self._run("change_error_msg")
        self.assertEqual(result.target_file, "pages/login.py")
        self.assertEqual(result.target_anchor, "LOGIN_HANDLE_LOGIN")

    def test_fix_login_lock_bug_selects_auth_login_user(self):
        result = self._run("fix_login_lock_bug")
        self.assertEqual(result.target_file, "api/auth.py")
        self.assertEqual(result.target_anchor, "AUTH_LOGIN_USER")

    def test_add_bio_length_limit_selects_profile_update(self):
        result = self._run("add_bio_length_limit")
        self.assertEqual(result.target_file, "pages/profile.py")
        self.assertEqual(result.target_anchor, "PROFILE_HANDLE_PROFILE_UPDATE")


class TestAIDeference(unittest.TestCase):
    """`--ai` (use_ai=True) must NOT override a high-confidence deterministic pick.

    C1 (verb-aware scoring) pushes the correct anchor to top-1 with `high`
    confidence on `add_bio_length_limit`. The pre-C6 code called
    `_ai_select_file` unconditionally when `use_ai=True`, and the AI then
    routed the request to `core/validators.py` (a validation utility), undoing
    C1's gain. C6 adds a deference rule: when deterministic confidence is
    `high`, the AI selector is skipped entirely.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = _prepare_sandbox(Path(cls._tmp.name))
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as fh:
            cls.scenarios = {s["id"]: s for s in json.load(fh)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_high_confidence_deterministic_result_is_preserved_under_ai(self):
        """With use_ai=True, a high-confidence deterministic pick must survive.

        Guarantee via mock: if the deference rule works, `_ai_select_file`
        is NEVER invoked on this scenario. We make the mock raise on call —
        any invocation fails the test.
        """
        from unittest.mock import patch as mock_patch

        sc = self.scenarios["add_bio_length_limit"]

        def _fail_if_called(*args, **kwargs):
            raise AssertionError(
                "_ai_select_file was called despite high-confidence deterministic pick"
            )

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            side_effect=_fail_if_called,
        ):
            result = suggest_patch(self.sandbox, sc["request"], use_ai=True)

        self.assertEqual(result.target_file, "pages/profile.py")
        self.assertEqual(result.target_anchor, "PROFILE_HANDLE_PROFILE_UPDATE")
        self.assertEqual(result.confidence, "high")

    def test_low_confidence_still_invokes_ai_when_flag_set(self):
        """Low-confidence path must still call the AI selector.

        The deference rule only applies to `high` confidence. This guards
        against an over-broad fix that turns `--ai` into a no-op. With
        pinned intents `fix_login_lock_bug` is the only scenario whose
        deterministic run produces `low` confidence.
        """
        from unittest.mock import patch as mock_patch

        sc = self.scenarios["fix_login_lock_bug"]
        precheck = suggest_patch(self.sandbox, sc["request"], use_ai=False)
        self.assertEqual(
            precheck.confidence, "low",
            "test premise broken: fix_login_lock_bug must be low confidence "
            "under the pinned-intent sandbox for this guard to be meaningful",
        )

        called = {"count": 0}

        def _record(*args, **kwargs):
            called["count"] += 1
            return None  # let suggest_patch fall back to deterministic pick

        with mock_patch(
            "vibelign.core.patch_suggester._ai_select_file",
            side_effect=_record,
        ):
            _ = suggest_patch(self.sandbox, sc["request"], use_ai=True)

        self.assertGreaterEqual(
            called["count"], 1,
            "AI selector must be called on low-confidence `fix_login_lock_bug`",
        )


if __name__ == "__main__":
    unittest.main()
