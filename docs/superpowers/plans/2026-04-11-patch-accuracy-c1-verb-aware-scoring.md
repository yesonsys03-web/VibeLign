# Patch Accuracy C1 — Verb-Aware Anchor Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add verb-cluster matching (MUTATE / CREATE / DELETE / READ) to `vibelign/core/patch_suggester.py` so that requests with action verbs ("바꿔줘", "수정", "추가") are routed to anchors whose name or intent describes the matching operation, fixing failure types F1 (wrong-sibling-anchor) and F3 (verb ignored).

**Architecture:** Add a small verb-classification layer to `patch_suggester.py` that maps (a) request tokens to a verb cluster and (b) anchor name tokens / intent text to the same cluster space. Then inject cluster-bonus/penalty into the two existing scoring sites — `_score_anchor_names` (file-level anchor ranking, used inside `score_path`) and `choose_anchor` (per-file anchor selection). Keep existing keyword-overlap scoring intact as the base; verb logic only adds a bonus (+5) or penalty (−2) when both sides classify cleanly.

**Tech Stack:** Python 3, existing `vibelign.core.patch_suggester` module, `unittest` with `tempfile.TemporaryDirectory` for isolation (matches existing test patterns).

**Source of truth for behavior:** `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md` §4 (F1, F3), §6 C1 row.

---

## File Structure

- **Modify:** `vibelign/core/patch_suggester.py`
  - Add new constants: `_VERB_CLUSTER_MUTATE`, `_VERB_CLUSTER_CREATE`, `_VERB_CLUSTER_DELETE`, `_VERB_CLUSTER_READ`
  - Add new functions: `_classify_request_verb`, `_classify_anchor_verb`, `_classify_intent_verb`, `_verb_cluster_bonus`
  - Modify: `_score_anchor_names` (line ~277) — call `_verb_cluster_bonus` once per anchor
  - Modify: `choose_anchor` (line ~710) — classify request verb once before loop, call `_verb_cluster_bonus` per anchor inside loop

- **Create:** `tests/test_patch_verb_cluster.py`
  - Unit tests for verb classifier functions (request, anchor name, intent)

- **Create:** `tests/test_patch_accuracy_scenarios.py`
  - End-to-end regression test encoding the 5 benchmark scenarios from `tests/benchmark/scenarios.json`. Each scenario builds a temp project with anchors + anchor_meta and asserts `suggest_patch` returns the expected `target_file` / `target_anchor`.

- **Do not touch:** existing tests (`test_patch_anchor_priority.py`, `test_patch_suggested_anchor.py`, etc.) — they must continue to pass unchanged.

---

## Task 1 — Verb cluster constants and classifier functions

**Files:**
- Create: `tests/test_patch_verb_cluster.py`
- Modify: `vibelign/core/patch_suggester.py` (add constants + functions near the existing `_LOGIC_INTENT_TOKENS` block, ~line 702)

- [ ] **Step 1.1: Write the failing unit tests**

Create `tests/test_patch_verb_cluster.py` with the following contents:

```python
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
```

- [ ] **Step 1.2: Run the tests and verify they fail**

Run: `cd "/Users/user/Documents/coding/VibeLign" && python -m pytest tests/test_patch_verb_cluster.py -v`

Expected: `ImportError` on `_classify_request_verb` (module does not define it yet). All tests fail to collect.

- [ ] **Step 1.3: Add verb cluster constants and classifiers to patch_suggester.py**

In `vibelign/core/patch_suggester.py`, locate the block ending with `_LOGIC_INTENT_TOKENS = { ... }` (around line 700) and add the following **immediately after** that block, before `def _has_style_token`:

```python
# --- Verb cluster classification (C1 — F1/F3 fix) ---
_VERB_CLUSTER_MUTATE = "MUTATE"
_VERB_CLUSTER_CREATE = "CREATE"
_VERB_CLUSTER_DELETE = "DELETE"
_VERB_CLUSTER_READ = "READ"

# Request-side verb tokens (Korean stems + English). Tokens compared against
# the output of `tokenize(request)`, which lowercases and strips Korean
# particles. Prefix match (startswith) is used so that inflected forms like
# "바꿔" / "바꿔줘" / "바꿨" all map through a single stem.
_REQUEST_VERB_STEMS: tuple[tuple[str, str], ...] = (
    # MUTATE — modify existing state
    ("바꿔", _VERB_CLUSTER_MUTATE),
    ("바꾸", _VERB_CLUSTER_MUTATE),
    ("변경", _VERB_CLUSTER_MUTATE),
    ("수정", _VERB_CLUSTER_MUTATE),
    ("고쳐", _VERB_CLUSTER_MUTATE),
    ("고치", _VERB_CLUSTER_MUTATE),
    ("버그", _VERB_CLUSTER_MUTATE),
    ("갱신", _VERB_CLUSTER_MUTATE),
    ("업데이트", _VERB_CLUSTER_MUTATE),
    ("update", _VERB_CLUSTER_MUTATE),
    ("change", _VERB_CLUSTER_MUTATE),
    ("fix", _VERB_CLUSTER_MUTATE),
    ("modify", _VERB_CLUSTER_MUTATE),
    ("set", _VERB_CLUSTER_MUTATE),
    # CREATE — add new behavior/state
    ("추가", _VERB_CLUSTER_CREATE),
    ("생성", _VERB_CLUSTER_CREATE),
    ("만들", _VERB_CLUSTER_CREATE),
    ("신규", _VERB_CLUSTER_CREATE),
    ("add", _VERB_CLUSTER_CREATE),
    ("create", _VERB_CLUSTER_CREATE),
    ("new", _VERB_CLUSTER_CREATE),
    ("register", _VERB_CLUSTER_CREATE),
    # DELETE — remove existing behavior/state
    ("삭제", _VERB_CLUSTER_DELETE),
    ("제거", _VERB_CLUSTER_DELETE),
    ("없애", _VERB_CLUSTER_DELETE),
    ("지워", _VERB_CLUSTER_DELETE),
    ("delete", _VERB_CLUSTER_DELETE),
    ("remove", _VERB_CLUSTER_DELETE),
    ("drop", _VERB_CLUSTER_DELETE),
    # READ — display or retrieve without modifying
    ("보여", _VERB_CLUSTER_READ),
    ("조회", _VERB_CLUSTER_READ),
    ("표시", _VERB_CLUSTER_READ),
    ("출력", _VERB_CLUSTER_READ),
    ("show", _VERB_CLUSTER_READ),
    ("display", _VERB_CLUSTER_READ),
    ("render", _VERB_CLUSTER_READ),
    ("get", _VERB_CLUSTER_READ),
    ("read", _VERB_CLUSTER_READ),
    ("list", _VERB_CLUSTER_READ),
    ("view", _VERB_CLUSTER_READ),
)

# Anchor-name token → cluster. Anchor names are ALL_CAPS snake case; we
# lowercase them and match tokens against the keys below.
_ANCHOR_VERB_TOKENS: dict[str, str] = {
    "handle": _VERB_CLUSTER_MUTATE,
    "update": _VERB_CLUSTER_MUTATE,
    "set": _VERB_CLUSTER_MUTATE,
    "write": _VERB_CLUSTER_MUTATE,
    "save": _VERB_CLUSTER_MUTATE,
    "patch": _VERB_CLUSTER_MUTATE,
    "edit": _VERB_CLUSTER_MUTATE,
    "modify": _VERB_CLUSTER_MUTATE,
    "process": _VERB_CLUSTER_MUTATE,
    "submit": _VERB_CLUSTER_MUTATE,
    "create": _VERB_CLUSTER_CREATE,
    "add": _VERB_CLUSTER_CREATE,
    "insert": _VERB_CLUSTER_CREATE,
    "register": _VERB_CLUSTER_CREATE,
    "new": _VERB_CLUSTER_CREATE,
    "delete": _VERB_CLUSTER_DELETE,
    "remove": _VERB_CLUSTER_DELETE,
    "drop": _VERB_CLUSTER_DELETE,
    "clear": _VERB_CLUSTER_DELETE,
    "get": _VERB_CLUSTER_READ,
    "read": _VERB_CLUSTER_READ,
    "load": _VERB_CLUSTER_READ,
    "fetch": _VERB_CLUSTER_READ,
    "find": _VERB_CLUSTER_READ,
    "list": _VERB_CLUSTER_READ,
    "render": _VERB_CLUSTER_READ,
    "show": _VERB_CLUSTER_READ,
    "display": _VERB_CLUSTER_READ,
    "view": _VERB_CLUSTER_READ,
    "validate": _VERB_CLUSTER_READ,
    "check": _VERB_CLUSTER_READ,
}


def _classify_request_verb(request_tokens: Iterable[str]) -> Optional[str]:
    """Return the verb cluster implied by a tokenized request, or None.

    Scans each request token and returns the FIRST cluster whose stem
    prefix-matches. Order in _REQUEST_VERB_STEMS matters: MUTATE before CREATE
    so that "버그 수정" (fix a bug) maps to MUTATE, not CREATE, even though
    "fix" adds something new conceptually.
    """
    token_list = list(request_tokens)
    for token in token_list:
        for stem, cluster in _REQUEST_VERB_STEMS:
            if token.startswith(stem):
                return cluster
    return None


def _classify_anchor_verb(anchor_name: str) -> Optional[str]:
    """Return the verb cluster implied by an anchor name, or None.

    Splits the anchor name on underscores and looks up each token in
    _ANCHOR_VERB_TOKENS. Returns the cluster of the LAST verb token found,
    because anchor naming convention places the verb after the module/object
    prefix (e.g. LOGIN_HANDLE_LOGIN → HANDLE, PROFILE_HANDLE_PROFILE_UPDATE
    → UPDATE). Later tokens describe the specific operation.
    """
    if not anchor_name:
        return None
    last_cluster: Optional[str] = None
    for part in anchor_name.lower().split("_"):
        cluster = _ANCHOR_VERB_TOKENS.get(part)
        if cluster is not None:
            last_cluster = cluster
    return last_cluster


def _classify_intent_verb(intent_text: str) -> Optional[str]:
    """Return the verb cluster implied by an anchor intent string, or None.

    Reuses the request-verb stem table since intents are written in Korean
    natural language like "로그인 폼 제출을 처리합니다" or
    "로그인 실패 시 오류 메시지를 보여줍니다".
    """
    if not intent_text:
        return None
    tokens = list(_intent_tokens(intent_text))
    # Also include word-level splits since _intent_tokens already handles this.
    for token in tokens:
        for stem, cluster in _REQUEST_VERB_STEMS:
            if token.startswith(stem):
                return cluster
    # Fallback: check whole text contains stem as substring (for verbs like
    # "처리" that may be embedded in "처리합니다").
    lowered = intent_text.lower()
    processing_stems = (
        ("처리", _VERB_CLUSTER_MUTATE),
        ("저장", _VERB_CLUSTER_MUTATE),
        ("보여", _VERB_CLUSTER_READ),
        ("표시", _VERB_CLUSTER_READ),
    )
    for stem, cluster in processing_stems:
        if stem in lowered:
            return cluster
    return None
```

- [ ] **Step 1.4: Run the tests and verify they pass**

Run: `python -m pytest tests/test_patch_verb_cluster.py -v`

Expected: all tests in `ClassifyRequestVerbTest`, `ClassifyAnchorVerbTest`, `ClassifyIntentVerbTest` pass.

- [ ] **Step 1.5: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_patch_verb_cluster.py
git commit -m "feat(patch-suggester): add verb cluster classifier (C1 part 1/3)"
```

---

## Task 2 — Integrate verb cluster bonus into `choose_anchor`

**Files:**
- Modify: `vibelign/core/patch_suggester.py:710-759` (the `choose_anchor` function)
- Create: new test class inside `tests/test_patch_verb_cluster.py`

- [ ] **Step 2.1: Write the failing test for `choose_anchor` verb preference**

Append the following test class to `tests/test_patch_verb_cluster.py`:

```python
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
```

- [ ] **Step 2.2: Run the new tests and verify they fail**

Run: `python -m pytest tests/test_patch_verb_cluster.py::ChooseAnchorVerbPreferenceTest -v`

Expected: `test_mutate_request_beats_render_sibling` FAILS. Actual selected anchor will be `LOGIN_RENDER_LOGIN_ERROR`. The other two may already pass incidentally (keyword-overlap already favors them) — that's fine; the failing one is the forcing function.

- [ ] **Step 2.3: Add `_verb_cluster_bonus` helper and integrate into `choose_anchor`**

In `patch_suggester.py`, immediately after `_classify_intent_verb` (added in Task 1), add:

```python
def _verb_cluster_bonus(
    request_cluster: Optional[str],
    anchor_cluster: Optional[str],
) -> tuple[int, Optional[str]]:
    """Return (score_delta, rationale_text_or_None) for a single comparison."""
    if request_cluster is None or anchor_cluster is None:
        return 0, None
    if request_cluster == anchor_cluster:
        return 5, f"요청 동사 클러스터({request_cluster})가 앵커와 일치"
    return -2, f"요청 동사 클러스터({request_cluster}) ↔ 앵커({anchor_cluster}) 불일치"
```

Then modify `choose_anchor` (currently around line 710). Replace the function body (from `if not anchors:` down to `return best_anchor, best_rationale`) with the version below — the only changes are (a) classifying the request verb once before the loop, (b) classifying each anchor, and (c) applying name-based and intent-based cluster bonuses. Everything else is preserved verbatim:

```python
def choose_anchor(
    anchors: list[str],
    request_tokens: list[str],
    anchor_meta: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> tuple[str, list[str]]:
    if not anchors:
        return "[먼저 앵커를 추가하세요]", ["이 파일에는 아직 앵커가 없습니다"]
    is_style_request = _has_style_token(request_tokens)
    request_verb_cluster = _classify_request_verb(request_tokens)
    best_anchor = anchors[0]
    best_score = -1
    best_rationale = [f"첫 번째 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in anchors:
        score = 0
        rationale = []
        anchor_tokens = _path_tokens(anchor)
        for token in _meaningful_overlap(request_tokens, anchor_tokens):
            score += 3
            rationale.append(f"앵커에 키워드 '{token}'이 포함됨")
        score -= _anchor_quality_penalty(anchor_tokens)
        if any(token in anchor_tokens for token in ["core", "logic", "worker"]):
            score += 1
        name_cluster = _classify_anchor_verb(anchor)
        name_delta, name_reason = _verb_cluster_bonus(
            request_verb_cluster, name_cluster
        )
        if name_delta:
            score += name_delta
            if name_reason:
                rationale.append(name_reason)
        # intent 정보가 있으면 자연어 매칭 점수 추가
        if anchor_meta and anchor in anchor_meta:
            meta = anchor_meta[anchor]
            intent = meta.get("intent", "").lower()
            if intent:
                intent_tokens = _intent_tokens(intent)
                for token in _meaningful_overlap(request_tokens, intent_tokens):
                    score += 4
                    rationale.append(
                        f"앵커 의도('{intent[:30]}...')에 키워드 '{token}'이 포함됨"
                        if len(intent) > 30
                        else f"앵커 의도('{intent}')에 키워드 '{token}'이 포함됨"
                    )
                intent_cluster = _classify_intent_verb(intent)
                intent_delta, intent_reason = _verb_cluster_bonus(
                    request_verb_cluster, intent_cluster
                )
                if intent_delta:
                    score += intent_delta
                    if intent_reason:
                        rationale.append(f"의도 동사: {intent_reason}")
                # 스타일 요청인데 intent가 로직 성격이면 페널티
                if is_style_request and any(
                    t in intent_tokens for t in _LOGIC_INTENT_TOKENS
                ):
                    score -= 5
                    rationale.append("스타일 요청인데 로직 성격 앵커라 우선순위 낮춤")
            warning = meta.get("warning")
            if warning:
                rationale.append(f"⚠️ {warning}")
        if score > best_score:
            best_score = score
            best_anchor = anchor
            best_rationale = rationale or [
                f"사용 가능한 앵커 중 '{anchor}'를 최선으로 선택"
            ]
    return best_anchor, best_rationale
```

- [ ] **Step 2.4: Run the new tests and verify they pass**

Run: `python -m pytest tests/test_patch_verb_cluster.py::ChooseAnchorVerbPreferenceTest -v`

Expected: all three `ChooseAnchorVerbPreferenceTest` methods pass.

- [ ] **Step 2.5: Run the full existing patch_suggester test surface and verify no regressions**

Run: `python -m pytest tests/test_patch_anchor_priority.py tests/test_patch_suggested_anchor.py tests/test_patch_targeting_regressions.py tests/test_anchor_suggestions.py tests/test_edge_patch_codespeak.py -v`

Expected: all pre-existing tests still pass. If any existing test fails, inspect whether the verb bonus is making a previously-correct anchor lose to a verb-matched sibling; if so, widen the rationale but keep the verb bonus — the old test may have been depending on keyword-overlap-only behavior that C1 is intentionally changing. Flag it in the commit message.

- [ ] **Step 2.6: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_patch_verb_cluster.py
git commit -m "feat(patch-suggester): verb cluster bonus in choose_anchor (C1 part 2/3)"
```

---

## Task 3 — Integrate verb cluster bonus into `_score_anchor_names` (file-level)

**Files:**
- Modify: `vibelign/core/patch_suggester.py:277-312` (the `_score_anchor_names` function)
- Modify: `vibelign/core/patch_suggester.py:647-666` (intent-matching block inside `score_path`)
- Create: new test class inside `tests/test_patch_verb_cluster.py`

- [ ] **Step 3.1: Write the failing test for file-level scoring**

`_score_anchor_names` is called from `score_path` which scores each candidate file. The C1 fix needs to raise files that contain verb-matching anchors above files whose anchors have mismatching verbs. The cleanest way to test this is through `suggest_patch` on a temp project with two files — one with a read-only anchor, one with a mutate anchor — and assert the mutate file wins for a mutate request.

Append to `tests/test_patch_verb_cluster.py`:

```python
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
```

- [ ] **Step 3.2: Run the new test and verify it fails**

Run: `python -m pytest tests/test_patch_verb_cluster.py::FileRankingVerbPreferenceTest -v`

Expected: FAIL. Current output will likely be `api/users.py / USERS_GET_USER_PROFILE` because Task 2 only changed the within-file choice, not the between-file ranking.

- [ ] **Step 3.3: Integrate verb cluster bonus into `_score_anchor_names`**

Replace the existing `_score_anchor_names` function (around line 277) with:

```python
def _score_anchor_names(
    anchor_names: Iterable[str],
    request_tokens: Iterable[str],
    label: str,
) -> tuple[int, list[str]]:
    score = 0
    rationale: list[str] = []
    request_cluster = _classify_request_verb(request_tokens)
    for anchor in anchor_names:
        anchor_tokens = _path_tokens(anchor)
        local_score = 0
        local_matches = _meaningful_overlap(request_tokens, anchor_tokens)
        match_count = len(local_matches)
        local_score += match_count * 3
        if label == "추천 앵커":
            if anchor.startswith("_"):
                local_score -= 2
            if any(
                part in anchor_tokens
                for part in [
                    "load",
                    "get",
                    "build",
                    "run",
                    "parse",
                    "flush",
                    "normalize",
                ]
            ):
                local_score -= 1
            if match_count < 2:
                local_score -= 3
        else:
            local_score -= _anchor_quality_penalty(anchor_tokens)
        anchor_cluster = _classify_anchor_verb(anchor)
        verb_delta, verb_reason = _verb_cluster_bonus(request_cluster, anchor_cluster)
        if verb_delta:
            local_score += verb_delta
        if local_score > 0:
            score = max(score, local_score)
            joined = ", ".join(dict.fromkeys(local_matches))
            rationale_line = f"{label} '{anchor}'에 키워드 {joined} 이(가) 포함됨"
            if verb_reason and verb_delta > 0:
                rationale_line += f" · {verb_reason}"
            rationale = [rationale_line]
    return score, rationale
```

Key points vs the original:
- Call `_classify_request_verb` once outside the loop.
- For each anchor, add `_verb_cluster_bonus` delta to `local_score`.
- Append the verb reason to the rationale line **only when** the delta is positive (we don't want a pile of "불일치" messages).

- [ ] **Step 3.4: Also extend the intent-match block inside `score_path` to use the cluster bonus**

Locate the block around line 647 inside `score_path`:

```python
    if isinstance(intent_meta, dict):
        file_anchors = (
            set(anchor_meta.get("anchors", []))
            if isinstance(anchor_meta, dict)
            else set()
        )
        for anchor_name, meta_entry in intent_meta.items():
            if file_anchors and anchor_name not in file_anchors:
                continue
            intent = meta_entry.get("intent", "").lower()
            if not intent:
                continue
            intent_tokens = _intent_tokens(intent)
            matched = _meaningful_overlap(request_tokens, intent_tokens)
            if matched:
                score += len(matched) * 3
                rationale.append(
                    f"앵커 intent에 키워드 '{', '.join(matched)}'이 포함됨"
                )
                break
```

Replace it with:

```python
    if isinstance(intent_meta, dict):
        file_anchors = (
            set(anchor_meta.get("anchors", []))
            if isinstance(anchor_meta, dict)
            else set()
        )
        request_cluster = _classify_request_verb(request_tokens)
        for anchor_name, meta_entry in intent_meta.items():
            if file_anchors and anchor_name not in file_anchors:
                continue
            intent = meta_entry.get("intent", "").lower()
            if not intent:
                continue
            intent_tokens = _intent_tokens(intent)
            matched = _meaningful_overlap(request_tokens, intent_tokens)
            if matched:
                score += len(matched) * 3
                rationale.append(
                    f"앵커 intent에 키워드 '{', '.join(matched)}'이 포함됨"
                )
                anchor_cluster = _classify_anchor_verb(anchor_name)
                intent_cluster = _classify_intent_verb(intent)
                effective_cluster = anchor_cluster or intent_cluster
                verb_delta, verb_reason = _verb_cluster_bonus(
                    request_cluster, effective_cluster
                )
                if verb_delta:
                    score += verb_delta
                    if verb_reason and verb_delta > 0:
                        rationale.append(f"intent 동사 일치: {verb_reason}")
                break
```

- [ ] **Step 3.5: Run the new test and verify it passes**

Run: `python -m pytest tests/test_patch_verb_cluster.py::FileRankingVerbPreferenceTest -v`

Expected: PASS — `target_file` is `pages/profile.py`, `target_anchor` is `PROFILE_HANDLE_PROFILE_UPDATE`.

- [ ] **Step 3.6: Run the full existing test surface and verify no regressions**

Run: `python -m pytest tests/test_patch_anchor_priority.py tests/test_patch_suggested_anchor.py tests/test_patch_targeting_regressions.py tests/test_anchor_suggestions.py tests/test_edge_patch_codespeak.py tests/test_patch_verb_cluster.py -v`

Expected: all tests pass. If `test_patch_targeting_regressions.py` or similar fails, inspect the test — the old behavior may have depended on keyword-only scoring and the new verb bonus is legitimately changing the answer. Update the expectation only if the new answer is objectively better; otherwise tune the bonus magnitude (consider dropping the penalty from −2 to −1 before weakening the +5 bonus).

- [ ] **Step 3.7: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_patch_verb_cluster.py
git commit -m "feat(patch-suggester): verb cluster bonus in file ranking (C1 part 3/3)"
```

---

## Task 4 — End-to-end regression suite encoding the 5 benchmark scenarios

**Files:**
- Create: `tests/test_patch_accuracy_scenarios.py`
- Reference: `tests/benchmark/scenarios.json`, `tests/benchmark/sample_project/`

- [ ] **Step 4.1: Write the regression test file**

Create `tests/test_patch_accuracy_scenarios.py` with the following contents. This test builds a temp project, runs `vib anchor --auto` to inject anchors the same way the sandbox did, then asserts the patch plan for each scenario. It is the long-term guard for C1 and any future round.

```python
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


def _prepare_sandbox(tmp: Path) -> Path:
    """Copy sample_project into tmp and insert anchors via `vib anchor --auto`.

    Returns the sandbox root path.
    """
    dst = tmp / "project"
    shutil.copytree(SAMPLE_PROJECT, dst)
    # `vib start` initializes .vibelign/ without prompting when stdin is closed.
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

    def _run(self, scenario_id: str):
        sc = self.scenarios[scenario_id]
        return suggest_patch(self.sandbox, sc["request"], use_ai=False)

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


if __name__ == "__main__":
    unittest.main()
```

Note the intentional scope: only the three scenarios that C1 is supposed to fix or preserve.
- `change_error_msg` — F1 fix target
- `fix_login_lock_bug` — was already passing, must remain passing (anti-regression)
- `add_bio_length_limit` — F3 fix target

`add_email_domain_check` (F2) and `add_password_change` (F2 + F4) are intentionally **not** included — they are the responsibility of the next ICE round (C2, C4). Adding them here would force this plan to grow beyond scope.

- [ ] **Step 4.2: Run the regression suite**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py -v`

Expected: all three tests pass. If `change_error_msg` or `add_bio_length_limit` still fails, re-verify Tasks 2/3 actually took effect and that anchor intents generated by `vib anchor --auto` are of a shape the verb classifier recognizes (run `cat project/.vibelign/anchor_meta.json` in the temp dir to inspect). If intent text differs from the sandbox run in §2 of the spec, extend `_classify_intent_verb`'s processing_stems fallback.

- [ ] **Step 4.3: Run the complete test surface one more time**

Run: `python -m pytest tests/ -x --ignore=tests/benchmark -q`

Expected: zero failures. The `-x` stops on first failure for quick diagnosis; `--ignore=tests/benchmark` skips the benchmark sample project contents (they are not tests).

- [ ] **Step 4.4: Commit**

```bash
git add tests/test_patch_accuracy_scenarios.py
git commit -m "test(patch-suggester): 5-scenario regression suite for C1"
```

---

## Task 5 — End-to-end sandbox validation and update spec §3

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md` (§3 집계 section — add "post-C1" row)

- [ ] **Step 5.1: Re-run the same 5 scenarios in the sandbox used during the ICE session**

Run (same loop as ICE session):

```bash
rm -rf /tmp/vibelign-ice-sandbox-postC1
cp -R "/Users/user/Documents/coding/VibeLign/tests/benchmark/sample_project" /tmp/vibelign-ice-sandbox-postC1
cd /tmp/vibelign-ice-sandbox-postC1
vib start < /dev/null > /dev/null 2>&1
vib anchor --auto < /dev/null

for req in \
  "로그인 실패 시 에러 메시지를 한국어로 바꿔줘|change_error_msg" \
  "회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가|add_email_domain_check" \
  "로그인 잠금이 풀리지 않는 버그 수정 — 로그인 성공 시 login_attempts를 0으로 리셋해야 함|fix_login_lock_bug" \
  "프로필 수정 시 bio 길이를 200자로 제한해줘|add_bio_length_limit" \
  "비밀번호 변경 기능 추가 — 현재 비밀번호 확인 후 새 비밀번호로 변경|add_password_change"; do
  request="${req%|*}"
  id="${req#*|}"
  echo "=== $id ==="
  vib patch --json "$request" | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d['data']['patch_plan']
print(f\"  file: {p.get('target_file')}\")
print(f\"  anchor: {p.get('target_anchor')}\")
print(f\"  confidence: {p.get('confidence')}\")
"
done
```

Expected changes vs the pre-C1 baseline in spec §2:
- `change_error_msg` anchor: `LOGIN_RENDER_LOGIN_ERROR` → `LOGIN_HANDLE_LOGIN` ✅
- `add_bio_length_limit` file: `api/users.py` → `pages/profile.py` ✅ and anchor: `USERS_GET_USER_PROFILE` → `PROFILE_HANDLE_PROFILE_UPDATE` ✅
- `fix_login_lock_bug`: unchanged ✅
- `add_email_domain_check`: **still wrong** — F2 is out of scope for C1
- `add_password_change`: **still wrong** — F2 + F4 out of scope

Post-C1 target: **files 3/5 (60%), anchor 3/4 (75%), overall 3/5 (60%)** — up from 1/5, 1/4, 1/5.

- [ ] **Step 5.2: Append post-C1 results to spec §3**

Add a new subsection under the existing "집계" list in `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md`. The exact insertion point is after the line:

```
- overall 정확도: **1 / 5** (20%)
```

Insert:

```markdown

### Post-C1 재측정 (YYYY-MM-DD)

| 시나리오 ID | files_ok | anchor_ok | overall | 변화 |
|---|---|---|---|---|
| change_error_msg       | ✅ | ✅ | ✅ | F1 fix |
| add_email_domain_check | ❌ | ❌ | ❌ | F2 잔존 (예상) |
| fix_login_lock_bug     | ✅ | ✅ | ✅ | 유지 |
| add_bio_length_limit   | ✅ | ✅ | ✅ | F3 fix |
| add_password_change    | ❌ | N/A | ❌ | F2/F4 잔존 (예상) |

- files 정확도: **3 / 5** (60%) ← +40%p
- anchor 정확도: **3 / 4** (75%) ← +50%p
- overall 정확도: **3 / 5** (60%) ← +40%p
```

Replace `YYYY-MM-DD` with the actual run date. Replace values with actual outputs if they differ (e.g. if `add_email_domain_check` happens to flip to correct, record that).

- [ ] **Step 5.3: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md
git commit -m "docs(spec): record post-C1 benchmark results"
```

- [ ] **Step 5.4: Final verification**

Run: `python -m pytest tests/ --ignore=tests/benchmark -q`

Expected: zero failures.

Run: `vib doctor --strict`

Expected: green/no errors.

If both pass, the C1 implementation is complete. File a follow-up note in the session to start writing the C5 plan (benchmark runner automation) per spec §9.

---

## Out of Scope (explicit)

- **F2 (layer routing)** — `add_email_domain_check`, `add_password_change`. Next ICE round (C2).
- **F4 (multi-intent fanout)** — `add_password_change`. Next ICE round (C4).
- **`--ai` path behavior** (C3) — requires separate measurement; C5 runner will make this cheap.
- **New verb clusters beyond MUTATE/CREATE/DELETE/READ** — e.g. MIGRATE, VALIDATE-as-its-own-cluster. If Task 3.6 surfaces a legitimate need, add to backlog, do not extend this plan.

## Rollback

If Tasks 2 or 3 cause cascading regressions that cannot be resolved by tuning the ±5/−2 magnitudes, roll back with:

```bash
git revert <commit-sha-of-task-3> <commit-sha-of-task-2>
```

Keep Task 1 (verb classifier constants) committed — the classifier alone has no behavior impact and is useful for future experimentation.
