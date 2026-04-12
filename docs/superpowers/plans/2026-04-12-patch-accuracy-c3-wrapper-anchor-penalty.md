# C3: Wrapper Anchor Penalty — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push anchor_ok from 3/4 to 4/4 by penalizing file-level wrapper anchors in `choose_anchor`.

**Architecture:** Add `_is_wrapper_anchor` detection helper + `_WRAPPER_ANCHOR_PENALTY = 5` constant. Apply penalty inside `choose_anchor`'s scoring loop, after `_anchor_quality_penalty`. The wrapper detection uses token-set inclusion: single-token anchor whose token appears in all siblings.

**Tech Stack:** Python 3.12, unittest, `uv run python -m pytest`, `vib bench --patch`

---

**File map:**

| File | Responsibility |
|---|---|
| `vibelign/core/patch_suggester.py` | `_is_wrapper_anchor` helper + `_WRAPPER_ANCHOR_PENALTY` constant + `choose_anchor` modification |
| `tests/test_wrapper_anchor_penalty.py` | Unit tests for wrapper detection and scoring effect |
| `tests/test_patch_accuracy_scenarios.py` | Tighten `add_email_domain_check` anchor assertions |
| `tests/benchmark/patch_accuracy_baseline.json` | Updated via CLI |

---

## Task 1: Write failing unit tests (TDD red)

**Files:**
- Create: `tests/test_wrapper_anchor_penalty.py`

- [ ] **Step 1: `_is_wrapper_anchor` detection tests**

```python
"""Unit tests for wrapper anchor detection and penalty (C3).

Covers _is_wrapper_anchor detection logic and the scoring effect
of _WRAPPER_ANCHOR_PENALTY in choose_anchor.
"""
import unittest


class IsWrapperAnchorTest(unittest.TestCase):
    def test_single_token_prefix_of_all_siblings_is_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        self.assertTrue(_is_wrapper_anchor("SIGNUP", anchors))

    def test_multi_token_anchor_is_not_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        self.assertFalse(_is_wrapper_anchor("SIGNUP_HANDLE_SIGNUP", anchors))

    def test_single_anchor_file_has_no_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["CONFIG"]
        self.assertFalse(_is_wrapper_anchor("CONFIG", anchors))

    def test_single_token_not_in_all_siblings_is_not_wrapper(self):
        from vibelign.core.patch_suggester import _is_wrapper_anchor

        anchors = ["AUTH", "AUTH_LOGIN_USER", "HELPERS_HASH"]
        self.assertFalse(_is_wrapper_anchor("AUTH", anchors))
```

- [ ] **Step 2: Scoring effect test**

Append to the same file:

```python
class WrapperAnchorScoringTest(unittest.TestCase):
    def test_wrapper_penalty_lets_leaf_win_over_wrapper(self):
        """The exact add_email_domain_check scenario.

        Without C3, SIGNUP (score 0) beats SIGNUP_HANDLE_SIGNUP (score -4).
        With C3, SIGNUP gets -5 penalty → -5, so SIGNUP_HANDLE_SIGNUP (-4) wins.
        """
        from vibelign.core.patch_suggester import choose_anchor, tokenize

        anchors = ["SIGNUP", "SIGNUP_RENDER_SIGNUP_FORM", "SIGNUP_HANDLE_SIGNUP"]
        request = "회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가"
        tokens = tokenize(request)
        chosen, _ = choose_anchor(anchors, tokens, None)
        self.assertEqual(chosen, "SIGNUP_HANDLE_SIGNUP")

    def test_wrapper_penalty_does_not_regress_verb_match_winner(self):
        """change_error_msg: LOGIN_HANDLE_LOGIN (+5) must still beat LOGIN (-5)."""
        from vibelign.core.patch_suggester import choose_anchor, tokenize

        anchors = ["LOGIN", "LOGIN_RENDER_LOGIN_FORM", "LOGIN_HANDLE_LOGIN", "LOGIN_RENDER_LOGIN_ERROR"]
        request = "로그인 에러 메시지 변경 — 사용자 경험 개선"
        tokens = tokenize(request)
        chosen, _ = choose_anchor(anchors, tokens, None)
        self.assertEqual(chosen, "LOGIN_HANDLE_LOGIN")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_wrapper_anchor_penalty.py -v`
Expected: 4 `_is_wrapper_anchor` tests FAIL with `ImportError: cannot import name '_is_wrapper_anchor'`. 2 scoring tests may PASS or FAIL depending on current behavior (LOGIN test should PASS since it already works, SIGNUP test should FAIL).

- [ ] **Step 4: Commit red stage**

```bash
git add tests/test_wrapper_anchor_penalty.py
git commit -m "$(cat <<'EOF'
test(c3): wrapper anchor penalty unit tests (red stage)

6 tests: 4 for _is_wrapper_anchor detection, 2 for scoring effect.
Detection tests fail with ImportError pending implementation.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement `_is_wrapper_anchor` and penalty (TDD green)

**Files:**
- Modify: `vibelign/core/patch_suggester.py:923` (before `choose_anchor`)

- [ ] **Step 1: Add constant and helper before `choose_anchor`**

Insert immediately before `def choose_anchor(` (line 923):

```python
_WRAPPER_ANCHOR_PENALTY = 5


def _is_wrapper_anchor(anchor: str, all_anchors: list[str]) -> bool:
    if len(all_anchors) < 2:
        return False
    tokens = _path_tokens(anchor)
    if len(tokens) != 1:
        return False
    token = next(iter(tokens))
    return all(
        token in _path_tokens(other)
        for other in all_anchors
        if other != anchor
    )
```

- [ ] **Step 2: Apply penalty inside `choose_anchor` scoring loop**

In `choose_anchor`, after line `score -= _anchor_quality_penalty(anchor_tokens)` (currently line 942), add:

```python
        if _is_wrapper_anchor(anchor, anchors):
            score -= _WRAPPER_ANCHOR_PENALTY
            rationale.append("파일 전체를 감싸는 wrapper 앵커라 우선순위 낮춤")
```

- [ ] **Step 3: Run unit tests**

Run: `uv run python -m pytest tests/test_wrapper_anchor_penalty.py -v`
Expected: **6/6 PASS**.

- [ ] **Step 4: Run existing anchor-related tests for regression**

Run: `uv run python -m pytest tests/test_patch_suggested_anchor.py tests/test_patch_anchor_priority.py tests/test_patch_verb_cluster.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit green stage**

```bash
git add vibelign/core/patch_suggester.py
git commit -m "$(cat <<'EOF'
feat(anchor): wrapper anchor penalty for C3

Adds _is_wrapper_anchor detection and _WRAPPER_ANCHOR_PENALTY = 5.
File-scope wrapper anchors (single-token prefix of all siblings)
are penalized so that more-specific leaf anchors win even when
they carry a verb-cluster mismatch.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Tighten scenario regression guard

**Files:**
- Modify: `tests/test_patch_accuracy_scenarios.py:51-79`

- [ ] **Step 1: Change `startswith("SIGNUP")` to exact match**

Replace in `test_add_email_domain_check_routes_to_signup_page`:

```python
        self.assertTrue(
            result.target_anchor.startswith("SIGNUP"),
            f"expected a SIGNUP* anchor, got {result.target_anchor!r}",
        )
```

→

```python
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")
```

Replace in `test_add_email_domain_check_ai_mode_also_routes_to_signup`:

```python
        self.assertTrue(
            result.target_anchor.startswith("SIGNUP"),
            f"expected a SIGNUP* anchor, got {result.target_anchor!r}",
        )
```

→

```python
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")
```

- [ ] **Step 2: Run scenario tests**

Run: `uv run python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: **7/7 PASS**.

- [ ] **Step 3: Commit**

```bash
git add tests/test_patch_accuracy_scenarios.py
git commit -m "$(cat <<'EOF'
test(c3): tighten add_email_domain_check anchor to exact match

C3 wrapper penalty now ensures SIGNUP_HANDLE_SIGNUP is chosen over
the outer SIGNUP wrapper. Upgrade from startswith guard to assertEqual.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Update baseline

**Files:**
- Modify: `tests/benchmark/patch_accuracy_baseline.json` (via CLI)

- [ ] **Step 1: Reinstall vib tool**

Run: `uv tool install --reinstall --force .`
Expected: Success message with `vibelign==1.7.2`.

- [ ] **Step 2: Check current state**

Run: `vib bench --patch`
Expected: `anchor_ok` shows `4/4 (+1)` for both det/ai. `improvements` includes `add_email_domain_check anchor_ok: False -> True`. Zero regressions.

- [ ] **Step 3: Update baseline**

Run: `vib bench --patch --update-baseline`
Expected: Exit code 0.

- [ ] **Step 4: Verify clean baseline**

Run: `vib bench --patch`
Expected: All `(=)`, `regressions: none`, `improvements: none`. Totals: `files_ok: 5/5`, `anchor_ok: 4/4`, `recall@3: 5/5`.

- [ ] **Step 5: Commit baseline**

```bash
git add tests/benchmark/patch_accuracy_baseline.json
git commit -m "$(cat <<'EOF'
chore(bench): update patch accuracy baseline for C3

Post-C3 baseline: det/ai 5/5 files, 4/4 anchor, 5/5 recall@3.
add_email_domain_check anchor_ok flipped from false to true via
wrapper anchor penalty. All scenarios now at maximum achievable
scores within the current 5-scenario framework.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Full verification + cleanup

**Files:**
- Run-only. No code changes.

- [ ] **Step 1: Full test suite**

Run: `uv run python -m pytest tests/ -v 2>&1 | tail -20`
Expected: All tests pass (613+ — 607 existing + 6 new).

- [ ] **Step 2: Commit chain review**

Run: `git log --oneline -6`
Expected:
1. `docs(spec): patch accuracy C3 wrapper anchor penalty design`
2. `test(c3): wrapper anchor penalty unit tests (red stage)`
3. `feat(anchor): wrapper anchor penalty for C3`
4. `test(c3): tighten add_email_domain_check anchor to exact match`
5. `chore(bench): update patch accuracy baseline for C3`

- [ ] **Step 3: Acceptance criteria check (spec §5)**

Verify:
- `vib bench --patch`: anchor_ok == 4/4 ✓
- files_ok == 5/5 ✓
- recall@3 == 5/5 ✓
- regressions == [] ✓
- add_email_domain_check anchor assertion is exact match ✓
- _is_wrapper_anchor has ≥4 test cases ✓

---

## Rollback Plan

All commits are independent. `git revert <hash>` for any single commit. Task 2 (implementation) is the only one that changes production code — reverting it restores pre-C3 behavior and the unit tests in Task 1 will fail (expected).

## Self-Review

- **Spec coverage**: §3.1 wrapper detection → Task 2 Step 1. §3.2 penalty → Task 2 Step 2. §3.3 helper → Task 2 Step 1. §4 edge cases → Task 1 Step 1. §5 acceptance → Task 5 Step 3. §6 files → all tasks. ✓
- **Placeholder scan**: No TBD/TODO/placeholders. All code blocks complete. ✓
- **Type consistency**: `_is_wrapper_anchor(anchor: str, all_anchors: list[str]) -> bool` signature matches across Task 1 tests and Task 2 implementation. `_WRAPPER_ANCHOR_PENALTY = 5` used in Task 2 only. `choose_anchor` and `tokenize` imports consistent. ✓
