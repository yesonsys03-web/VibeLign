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


if __name__ == "__main__":
    unittest.main()
