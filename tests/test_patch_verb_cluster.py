import unittest

from vibelign.core.patch_suggester import (
    _classify_request_verb,
    _classify_anchor_verb,
    _classify_intent_verb,
    _VERB_CLUSTER_MUTATE,
    _VERB_CLUSTER_CREATE,
    _VERB_CLUSTER_DELETE,
    _VERB_CLUSTER_READ,
    tokenize,
)


class ClassifyRequestVerbTest(unittest.TestCase):
    def _cluster(self, text: str):
        return _classify_request_verb(tokenize(text))

    def test_mutate_korean_change_verb(self):
        self.assertEqual(
            self._cluster("로그인 실패 시 에러 메시지를 한국어로 바꿔줘"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_mutate_korean_update_verb(self):
        self.assertEqual(
            self._cluster("프로필 수정 시 bio 길이를 200자로 제한해줘"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_mutate_korean_fix_bug(self):
        self.assertEqual(
            self._cluster("로그인 잠금이 풀리지 않는 버그 수정"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_create_korean_add_verb(self):
        self.assertEqual(
            self._cluster("회원가입 시 이메일 도메인 검사 추가"),
            _VERB_CLUSTER_CREATE,
        )

    def test_create_korean_feature_add(self):
        self.assertEqual(
            self._cluster("비밀번호 변경 기능 추가"),
            _VERB_CLUSTER_CREATE,
        )

    def test_delete_korean_remove_verb(self):
        self.assertEqual(
            self._cluster("사이드바 제거해줘"),
            _VERB_CLUSTER_DELETE,
        )

    def test_read_korean_show_verb(self):
        self.assertEqual(
            self._cluster("프로필 정보 보여줘"),
            _VERB_CLUSTER_READ,
        )

    def test_unknown_verb_returns_none(self):
        self.assertIsNone(self._cluster("이것은 특별히 동사가 없는 구절"))


class ClassifyAnchorVerbTest(unittest.TestCase):
    def test_handle_anchor_is_mutate(self):
        self.assertEqual(
            _classify_anchor_verb("LOGIN_HANDLE_LOGIN"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_update_anchor_is_mutate(self):
        self.assertEqual(
            _classify_anchor_verb("PROFILE_HANDLE_PROFILE_UPDATE"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_set_anchor_is_mutate(self):
        self.assertEqual(
            _classify_anchor_verb("CONFIG_SET_VALUE"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_render_anchor_is_read(self):
        self.assertEqual(
            _classify_anchor_verb("LOGIN_RENDER_LOGIN_ERROR"),
            _VERB_CLUSTER_READ,
        )

    def test_get_anchor_is_read(self):
        self.assertEqual(
            _classify_anchor_verb("USERS_GET_USER_PROFILE"),
            _VERB_CLUSTER_READ,
        )

    def test_validate_anchor_is_read(self):
        self.assertEqual(
            _classify_anchor_verb("VALIDATORS_VALIDATE_EMAIL_DOMAIN"),
            _VERB_CLUSTER_READ,
        )

    def test_create_anchor_is_create(self):
        self.assertEqual(
            _classify_anchor_verb("DATABASE_CREATE_USER"),
            _VERB_CLUSTER_CREATE,
        )

    def test_register_anchor_is_create(self):
        self.assertEqual(
            _classify_anchor_verb("AUTH_REGISTER_USER"),
            _VERB_CLUSTER_CREATE,
        )

    def test_delete_anchor_is_delete(self):
        self.assertEqual(
            _classify_anchor_verb("USERS_DELETE_USER"),
            _VERB_CLUSTER_DELETE,
        )

    def test_module_only_anchor_is_none(self):
        self.assertIsNone(_classify_anchor_verb("LOGIN"))

    def test_empty_anchor_is_none(self):
        self.assertIsNone(_classify_anchor_verb(""))


class ClassifyIntentVerbTest(unittest.TestCase):
    def test_intent_with_handle_verb(self):
        self.assertEqual(
            _classify_intent_verb("로그인 폼 제출을 처리합니다"),
            _VERB_CLUSTER_MUTATE,
        )

    def test_intent_with_render_verb(self):
        self.assertEqual(
            _classify_intent_verb("로그인 실패 시 오류 메시지를 보여줍니다"),
            _VERB_CLUSTER_READ,
        )

    def test_intent_without_verb_is_none(self):
        self.assertIsNone(_classify_intent_verb("로그인 정보"))


from vibelign.core.patch_suggester import choose_anchor


class ChooseAnchorVerbPreferenceTest(unittest.TestCase):
    def test_mutate_request_beats_render_sibling(self):
        """F1 regression: 바꿔줘 (MUTATE) must prefer HANDLE over RENDER.

        Recreates change_error_msg: both LOGIN_HANDLE_LOGIN and
        LOGIN_RENDER_LOGIN_ERROR live in the same file, and the current
        keyword-only scorer ranks RENDER above HANDLE because the RENDER
        intent contains literal '로그인/실패/시' keywords.
        """
        anchors = ["LOGIN", "LOGIN_HANDLE_LOGIN", "LOGIN_RENDER_LOGIN_ERROR"]
        request_tokens = tokenize("로그인 실패 시 에러 메시지를 한국어로 바꿔줘")
        anchor_meta = {
            "LOGIN_HANDLE_LOGIN": {
                "intent": "로그인 폼 제출을 처리하고 결과 응답을 반환합니다"
            },
            "LOGIN_RENDER_LOGIN_ERROR": {
                "intent": "로그인 실패 시 오류 메시지를 보여줍니다"
            },
        }
        best, _ = choose_anchor(anchors, request_tokens, anchor_meta)
        self.assertEqual(best, "LOGIN_HANDLE_LOGIN")

    def test_create_request_prefers_register_anchor(self):
        anchors = ["AUTH", "AUTH_LOGIN_USER", "AUTH_REGISTER_USER"]
        request_tokens = tokenize("새 계정 등록 기능 추가")
        anchor_meta = {
            "AUTH_LOGIN_USER": {"intent": "이메일과 비밀번호로 로그인합니다"},
            "AUTH_REGISTER_USER": {"intent": "새 사용자를 등록합니다"},
        }
        best, _ = choose_anchor(anchors, request_tokens, anchor_meta)
        self.assertEqual(best, "AUTH_REGISTER_USER")

    def test_read_request_prefers_get_anchor(self):
        anchors = ["USERS", "USERS_GET_USER_PROFILE", "USERS_UPDATE_USER_PROFILE"]
        request_tokens = tokenize("프로필 정보 보여줘")
        anchor_meta = {
            "USERS_GET_USER_PROFILE": {"intent": "사용자 프로필을 조회합니다"},
            "USERS_UPDATE_USER_PROFILE": {"intent": "프로필을 수정합니다"},
        }
        best, _ = choose_anchor(anchors, request_tokens, anchor_meta)
        self.assertEqual(best, "USERS_GET_USER_PROFILE")


import json
import tempfile
from pathlib import Path

from vibelign.core.patch_suggester import suggest_patch


class FileRankingVerbPreferenceTest(unittest.TestCase):
    def test_update_request_prefers_handle_file_over_get_file(self):
        """F3 regression: add_bio_length_limit routed to pages/profile.py
        (which contains HANDLE_PROFILE_UPDATE) instead of api/users.py
        (which contains GET_USER_PROFILE).
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "api").mkdir()
            (root / "pages").mkdir()
            (root / "api" / "users.py").write_text(
                "# === ANCHOR: USERS_START ===\n"
                "# === ANCHOR: USERS_GET_USER_PROFILE_START ===\n"
                "def get_user_profile(user_id):\n"
                "    return {'bio': ''}\n"
                "# === ANCHOR: USERS_GET_USER_PROFILE_END ===\n"
                "# === ANCHOR: USERS_END ===\n",
                encoding="utf-8",
            )
            (root / "pages" / "profile.py").write_text(
                "# === ANCHOR: PROFILE_START ===\n"
                "# === ANCHOR: PROFILE_HANDLE_PROFILE_UPDATE_START ===\n"
                "def handle_profile_update(user_id, name, bio):\n"
                "    return {'ok': True}\n"
                "# === ANCHOR: PROFILE_HANDLE_PROFILE_UPDATE_END ===\n"
                "# === ANCHOR: PROFILE_END ===\n",
                encoding="utf-8",
            )
            meta_dir = root / ".vibelign"
            meta_dir.mkdir()
            (meta_dir / "anchor_index.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "anchors": {
                            "api/users.py": ["USERS", "USERS_GET_USER_PROFILE"],
                            "pages/profile.py": [
                                "PROFILE",
                                "PROFILE_HANDLE_PROFILE_UPDATE",
                            ],
                        },
                        "files": {
                            "api/users.py": {
                                "anchors": ["USERS", "USERS_GET_USER_PROFILE"]
                            },
                            "pages/profile.py": {
                                "anchors": [
                                    "PROFILE",
                                    "PROFILE_HANDLE_PROFILE_UPDATE",
                                ]
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            (meta_dir / "anchor_meta.json").write_text(
                json.dumps(
                    {
                        "USERS_GET_USER_PROFILE": {
                            "intent": "사용자 프로필을 조회합니다"
                        },
                        "PROFILE_HANDLE_PROFILE_UPDATE": {
                            "intent": "프로필 편집 폼을 처리합니다"
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = suggest_patch(
                root, "프로필 수정 시 bio 길이를 200자로 제한해줘", use_ai=False
            )
            self.assertEqual(result.target_file, "pages/profile.py")
            self.assertEqual(result.target_anchor, "PROFILE_HANDLE_PROFILE_UPDATE")


class ChooseAnchorUIElementRenderBonus(unittest.TestCase):
    """UI element tokens (폼, 버튼, placeholder, 텍스트, 필드, 라벨) in the
    request should prefer render anchors even when the verb is MUTATE."""

    def test_button_text_change_prefers_render_over_handle(self):
        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        request_tokens = tokenize("회원가입 버튼 텍스트를 '가입하기'로 바꿔줘")
        best, _ = choose_anchor(anchors, request_tokens)
        self.assertEqual(best, "SIGNUP_RENDER_SIGNUP_FORM")

    def test_placeholder_change_prefers_render_over_handle(self):
        anchors = ["LOGIN", "LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN", "LOGIN_RENDER_LOGIN_ERROR"]
        request_tokens = tokenize("로그인 폼 placeholder를 한국어로 바꿔줘")
        best, _ = choose_anchor(anchors, request_tokens)
        self.assertEqual(best, "LOGIN_RENDER_LOGIN_FORM")

    def test_field_add_prefers_render_over_handle(self):
        anchors = ["PROFILE", "PROFILE_RENDER_PROFILE", "PROFILE_HANDLE_PROFILE_UPDATE"]
        request_tokens = tokenize("프로필 수정 가능 필드에 email도 추가해줘")
        best, _ = choose_anchor(anchors, request_tokens)
        self.assertEqual(best, "PROFILE_RENDER_PROFILE")

    def test_non_ui_mutate_still_prefers_handle(self):
        """Regression guard: logic changes must still pick handle."""
        anchors = ["LOGIN", "LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN"]
        request_tokens = tokenize("로그인 실패 시 에러 메시지를 한국어로 바꿔줘")
        best, _ = choose_anchor(anchors, request_tokens)
        self.assertEqual(best, "LOGIN_HANDLE_LOGIN")

    def test_delete_verb_with_ui_tokens_still_prefers_handle(self):
        """Regression guard: DELETE verb must not trigger render bonus."""
        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        request_tokens = tokenize("회원가입 폼에서 비밀번호 확인 필드 제거해줘")
        best, _ = choose_anchor(anchors, request_tokens)
        self.assertEqual(best, "SIGNUP_HANDLE_SIGNUP")


if __name__ == "__main__":
    unittest.main()
