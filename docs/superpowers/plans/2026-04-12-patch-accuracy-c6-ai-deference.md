# Patch Accuracy C6 — AI Deference Rule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vib patch --ai` 가 deterministic 상위 결과(`high` confidence) 를 뒤집어 정확도를 떨어뜨리는 회귀를 해소한다. C1 verb-aware 스코어링이 올린 precision 이 `_ai_select_file` 에 의해 소실되지 않도록, AI 호출 조건에 **deference 룰** 을 추가한다.

**Architecture:** `suggest_patch` (`vibelign/core/patch_suggester.py:1140-1264`) 의 `should_use_ai` 결정 로직(1212-1219)을 수정한다. 현재 `--ai` 플래그는 confidence 와 무관하게 AI 를 호출해 deterministic top-1 을 덮어쓸 수 있다. 변경: `high` confidence 에서는 `--ai` 가 있어도 AI 호출을 건너뛴다. `low`/`medium` confidence 에서는 기존 동작 유지. 이는 "deterministic = prefilter + ranking / AI = low-confidence final judge" 설계 철학과 코드를 일치시키는 최소 변경이다.

**Tech Stack:** Python 3.11+, pytest / unittest, `unittest.mock.patch`.

**Context for the engineer:**

- `vib` CLI 는 uv-tool 격리 환경 (`~/.local/share/uv/tools/vibelign/`) 에 설치되어 있어 로컬 repo 변경이 자동 반영되지 **않는다**. CLI 기반 E2E 검증 전에 반드시 `uv tool install --reinstall --force .` 를 먼저 실행.
- 기존 `tests/test_patch_accuracy_scenarios.py` 는 **pinned intents** (LLM 비결정성을 회피하기 위한 고정 intent 테이블) 로 돌아간다. C6 의 단위 테스트는 이 파일에 추가하되, `use_ai=True` 를 사용하고 `_ai_select_file` 을 mock 으로 대체해 "AI 호출 여부" 를 단언한다 (실제 AI API 호출 없음).
- 2026-04-12 측정에서 `--ai` 모드가 C1 deterministic 보다 -20%p 낮음. 구체 회귀: `add_bio_length_limit` 이 deterministic (`high`) 에서 `pages/profile.py::PROFILE_HANDLE_PROFILE_UPDATE` 로 정답을 맞추는데, `--ai` 에서는 `core/validators.py` 로 덮어쓰임. 자세한 측정 내역: `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md` §3 "`--ai` 모드 베이스라인 (2026-04-12)".
- **Deference 룰 설계 (Option B):**
  - `confidence == "high"` + `use_ai=True` → AI 호출 **건너뜀**. Deterministic top-1 을 그대로 사용.
  - `confidence == "medium"` + `use_ai=True` → AI 호출 (기존 동작 유지, 사용자 escape hatch).
  - `confidence == "low"` → AI 호출 (use_ai 무관, 기존 동작 유지).
  - `use_ai=False` + `confidence != "low"` → AI 호출 안 함 (기존 동작 유지).

**File Structure:**

- Modify: `vibelign/core/patch_suggester.py`
  - `suggest_patch` 함수 내 `should_use_ai` 계산 (line 1212-1219) — deference 조건 추가.
- Modify: `tests/test_patch_accuracy_scenarios.py`
  - `_run` 헬퍼에 `use_ai` 파라미터 추가.
  - `TestAIDeference` 클래스 신설 (pinned-intent 샌드박스 재사용 + `unittest.mock.patch` 로 `_ai_select_file` mock).
- Modify: `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md`
  - §3 에 "Post-C6 재측정" 서브섹션 추가.

---

## Task 1: Failing regression test — high-confidence deference

**Files:**
- Modify: `tests/test_patch_accuracy_scenarios.py` (append `TestAIDeference` class + helper refactor)

- [ ] **Step 1.1: Refactor `_run` helper to accept `use_ai`**

In `tests/test_patch_accuracy_scenarios.py`, replace the existing `_run` method (line 95-97) with a version that threads `use_ai`:

```python
    def _run(self, scenario_id: str, *, use_ai: bool = False):
        sc = self.scenarios[scenario_id]
        return suggest_patch(self.sandbox, sc["request"], use_ai=use_ai)
```

- [ ] **Step 1.2: Verify the existing suite still passes with the refactor**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: the three existing tests (`test_change_error_msg_selects_handle_login`, `test_fix_login_lock_bug_selects_auth_login_user`, `test_add_bio_length_limit_selects_profile_update`) all PASS. The default `use_ai=False` keeps them unchanged.

- [ ] **Step 1.3: Add `TestAIDeference` class with the failing test**

Append to `tests/test_patch_accuracy_scenarios.py` (after `PatchAccuracyScenarioTest`, before `if __name__`):

```python
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
        against an over-broad fix that turns `--ai` into a no-op.
        """
        from unittest.mock import patch as mock_patch

        sc = self.scenarios["change_error_msg"]
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
            "AI selector must be called on low-confidence `change_error_msg`",
        )
```

- [ ] **Step 1.4: Run the new tests and confirm they fail**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py::TestAIDeference -v`
Expected:
- `test_high_confidence_deterministic_result_is_preserved_under_ai` **FAILS** with `AssertionError: _ai_select_file was called despite high-confidence deterministic pick` (because current code calls AI unconditionally when `use_ai=True`).
- `test_low_confidence_still_invokes_ai_when_flag_set` PASSES (the current code already calls the AI selector on low confidence).

If `test_high_confidence_deterministic_result_is_preserved_under_ai` instead errors on something else (import, fixture), stop and investigate — the mock must target the exact import path used by `suggest_patch` (`vibelign.core.patch_suggester._ai_select_file`).

- [ ] **Step 1.5: Commit the failing test**

```bash
git add tests/test_patch_accuracy_scenarios.py
git commit -m "test(patch-suggester): failing regression for --ai high-confidence deference (C6)"
```

---

## Task 2: Implement the deference rule

**Files:**
- Modify: `vibelign/core/patch_suggester.py:1208-1219` (`should_use_ai` calculation inside `suggest_patch`)

- [ ] **Step 2.1: Apply the deference condition**

In `vibelign/core/patch_suggester.py`, locate the block at lines 1208-1219:

```python
    stateful_ui_request = _is_stateful_ui_request(request_tokens)
    # --ai 명시: confidence 무관하게 AI가 파일 선택
    # --ai 없음: confidence LOW일 때만 AI 폴백
    best_path_tokens = _path_tokens(relpath_str(root, best_path))
    best_is_frontend = best_path.suffix.lower() in _FRONTEND_EXTS
    should_use_ai = confidence == "low" or (
        use_ai
        and not (
            stateful_ui_request
            and best_is_frontend
            and any(token in best_path_tokens for token in _STATE_OWNER_FILE_HINTS)
        )
    )
```

Replace it with:

```python
    stateful_ui_request = _is_stateful_ui_request(request_tokens)
    # Deference rule (C6, 2026-04-12):
    # - confidence == "low": AI always invoked (use_ai flag irrelevant)
    # - confidence == "medium" + use_ai: AI invoked (user escape hatch)
    # - confidence == "high" + use_ai: AI **skipped** — deterministic top-1
    #   is trusted. Prevents --ai from overriding C1 verb-aware ranking on
    #   scenarios where deterministic already found the right file.
    # - use_ai=False + confidence != "low": AI not invoked (unchanged)
    best_path_tokens = _path_tokens(relpath_str(root, best_path))
    best_is_frontend = best_path.suffix.lower() in _FRONTEND_EXTS
    ai_override_blocked_by_state_hint = (
        stateful_ui_request
        and best_is_frontend
        and any(token in best_path_tokens for token in _STATE_OWNER_FILE_HINTS)
    )
    should_use_ai = confidence == "low" or (
        use_ai
        and confidence != "high"
        and not ai_override_blocked_by_state_hint
    )
```

- [ ] **Step 2.2: Run the new tests and confirm they pass**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py::TestAIDeference -v`
Expected: both tests PASS.

- [ ] **Step 2.3: Run the full patch-accuracy suite to confirm no regression**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: all 5 tests PASS (3 existing + 2 new).

- [ ] **Step 2.4: Commit the implementation**

```bash
git add vibelign/core/patch_suggester.py
git commit -m "feat(patch-suggester): defer to deterministic top-1 on high confidence under --ai (C6)"
```

---

## Task 3: Full-suite regression check

**Files:** none (read-only)

- [ ] **Step 3.1: Run the full pytest suite excluding the slow benchmark dir**

Run: `python -m pytest tests/ --ignore=tests/benchmark -q`
Expected: every pre-existing test still passes. If an unrelated test fails, **stop and investigate** — do not rewrite or skip tests without confirming root cause. The most likely regression surface is other `test_patch_*` files that may have been asserting AI-selection behavior.

- [ ] **Step 3.2: If any test fails, report the failure to the reviewer and pause**

Do not proceed to Task 4 until the full suite is green. The deference rule is intentionally narrow (only `high` confidence), so failures likely indicate either (a) a legitimate behavioral change that needs test update, or (b) an unintended side effect of the condition rewrite.

---

## Task 4: End-to-end sandbox validation with real `--ai`

**Files:** none (runtime validation only)

- [ ] **Step 4.1: Reinstall vib so the new code is picked up by the CLI**

Run from the repo root:

```bash
uv tool install --reinstall --force .
```

Expected: exit 0, final line `Installed 3 executables: vib, vibelign, vibelign-mcp`. Skipping this step will cause Step 4.2 to silently run against the pre-C6 binary.

- [ ] **Step 4.2: Rebuild the sandbox and run the 5 scenarios with `--ai`**

Run:

```bash
rm -rf /tmp/vibelign-ice-sandbox-postC6-ai
cp -R "/Users/user/Documents/coding/VibeLign/tests/benchmark/sample_project" /tmp/vibelign-ice-sandbox-postC6-ai
cd /tmp/vibelign-ice-sandbox-postC6-ai
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
  vib patch --ai --json "$request" | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d['data']['patch_plan']
print(f\"  file:       {p.get('target_file')}\")
print(f\"  anchor:     {p.get('target_anchor')}\")
print(f\"  confidence: {p.get('confidence')}\")
"
done
```

Expected output pattern (anchor names per sandbox drift may vary slightly, but key comparisons below):
- `change_error_msg`: `pages/login.py` + `LOGIN_HANDLE_LOGIN` (confidence `low`, AI invoked → unchanged)
- `add_email_domain_check`: `api/auth.py` or `core/validators.py` (still wrong, F2 — C6 does not target this; confidence `high`, AI **skipped** so result matches deterministic output of Step 4.3 below)
- `fix_login_lock_bug`: `api/auth.py` + `AUTH_LOGIN_USER` (confidence `low`, unchanged)
- `add_bio_length_limit`: **`pages/profile.py` + `PROFILE_HANDLE_PROFILE_UPDATE`** ← this is the regression fix. Pre-C6: `core/validators.py`. Post-C6: profile. Confidence `high`, AI skipped.
- `add_password_change`: `api/auth.py` + anchor from deterministic (still wrong on multi-file fanout, F4, out of scope)

- [ ] **Step 4.3: Cross-check deterministic equivalence for high-confidence cases**

Re-run the same 5 scenarios **without** `--ai`:

```bash
cd /tmp/vibelign-ice-sandbox-postC6-ai
for req in \
  "로그인 실패 시 에러 메시지를 한국어로 바꿔줘|change_error_msg" \
  "회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가|add_email_domain_check" \
  "로그인 잠금이 풀리지 않는 버그 수정 — 로그인 성공 시 login_attempts를 0으로 리셋해야 함|fix_login_lock_bug" \
  "프로필 수정 시 bio 길이를 200자로 제한해줘|add_bio_length_limit" \
  "비밀번호 변경 기능 추가 — 현재 비밀번호 확인 후 새 비밀번호로 변경|add_password_change"; do
  request="${req%|*}"
  id="${req#*|}"
  echo "=== $id (det) ==="
  vib patch --json "$request" | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d['data']['patch_plan']
print(f\"  file:   {p.get('target_file')}\")
print(f\"  anchor: {p.get('target_anchor')}\")
print(f\"  conf:   {p.get('confidence')}\")
"
done
```

Expected: for **every scenario that reports confidence `high`** in Step 4.3's deterministic run, Step 4.2's `--ai` run must report the **exact same** `target_file` and `target_anchor`. Any mismatch on a `high`-confidence row means the deference rule is not firing — stop and investigate.

- [ ] **Step 4.4: Tally the accuracy against `tests/benchmark/scenarios.json`**

Run:

```bash
python3 <<'PY'
import json

scenarios = {s["id"]: s for s in json.load(open("/Users/user/Documents/coding/VibeLign/tests/benchmark/scenarios.json"))}

# Paste the --ai results from Step 4.2 here (one tuple per scenario):
results = {
    "change_error_msg":       ("pages/login.py", "LOGIN_HANDLE_LOGIN"),
    "add_email_domain_check": ("<file-from-run>", "<anchor-from-run>"),
    "fix_login_lock_bug":     ("api/auth.py", "AUTH_LOGIN_USER"),
    "add_bio_length_limit":   ("pages/profile.py", "PROFILE_HANDLE_PROFILE_UPDATE"),
    "add_password_change":    ("<file-from-run>", "<anchor-from-run>"),
}

files_ok = 0
anchor_ok_num = 0
anchor_ok_den = 0
overall_ok = 0
for sid, sc in scenarios.items():
    got_file, got_anchor = results[sid]
    correct_files = set(sc["correct_files"])
    forbidden = set(sc.get("forbidden_files", []))
    f_ok = correct_files.issubset({got_file}) and got_file not in forbidden
    if sc.get("correct_anchor") is None:
        a_ok = "N/A"
    else:
        anchor_ok_den += 1
        a_ok = got_anchor == sc["correct_anchor"]
        if a_ok:
            anchor_ok_num += 1
    if f_ok:
        files_ok += 1
    if f_ok and a_ok in (True, "N/A"):
        overall_ok += 1
    print(f"{sid:28s} file={'✅' if f_ok else '❌'} anchor={a_ok}")

print(f"\nfiles: {files_ok}/5  anchor: {anchor_ok_num}/{anchor_ok_den}  overall: {overall_ok}/5")
PY
```

Replace the `<file-from-run>` / `<anchor-from-run>` placeholders with the actual outputs from Step 4.2 before running. **Record the final `files/anchor/overall` numbers — they go into Task 5.**

**Post-C6 target:** `--ai` mode reaches **at least** the C1 deterministic baseline — `files 3/5`, `anchor 3/4`, `overall 3/5`. Lower numbers mean the fix is incomplete; stop and investigate.

---

## Task 5: Record Post-C6 results in the spec and commit

**Files:**
- Modify: `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md` (append Post-C6 section under §3)

- [ ] **Step 5.1: Append the Post-C6 subsection**

In `docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md`, locate the end of the "`--ai` 모드 베이스라인 (2026-04-12)" subsection (it ends just before the `---` that separates §3 from §4 "Failure Taxonomy"). Immediately before that `---`, insert:

```markdown

### Post-C6 재측정 (`--ai` deference, YYYY-MM-DD)

C6 (AI deference rule) 적용 후 동일 샌드박스에서 `vib patch --ai --json` 재측정. 환경: `/tmp/vibelign-ice-sandbox-postC6-ai`, 공급자: Gemini.

| 시나리오 ID | AI 결과 파일 | AI 결과 앵커 | confidence | files_ok | anchor_ok | overall | 2026-04-12 `--ai` 대비 |
|---|---|---|---|---|---|---|---|
| change_error_msg       | `pages/login.py`      | `LOGIN_HANDLE_LOGIN`           | low    | ✅ | ✅ | ✅ | 유지 |
| add_email_domain_check | `<fill>`              | `<fill>`                       | high   | ❌ | ❌ | ❌ | 유지 (C2 대상) |
| fix_login_lock_bug     | `api/auth.py`         | `AUTH_LOGIN_USER`              | low    | ✅ | ✅ | ✅ | 유지 |
| add_bio_length_limit   | `pages/profile.py`    | `PROFILE_HANDLE_PROFILE_UPDATE`| high   | ✅ | ✅ | ✅ | **회귀 해소** |
| add_password_change    | `<fill>`              | `<fill>`                       | high   | ❌ | N/A | ❌ | 유지 (C4 대상) |

- files 정확도: **<fill> / 5** (<fill>%) ← 2026-04-12 `--ai` (2/5) 대비 +<fill>%p
- anchor 정확도: **<fill> / 4** (<fill>%) ← 2026-04-12 `--ai` (2/4) 대비 +<fill>%p
- overall 정확도: **<fill> / 5** (<fill>%) ← 2026-04-12 `--ai` (2/5) 대비 +<fill>%p

**결론:** `--ai` 모드가 C1 deterministic 과 동률 (또는 그 이상). "deterministic = prefilter / AI = low-confidence judge" 설계 철학과 코드가 일치. 남은 실패는 모두 C2 (F2 layer routing) / C4 (F4 multi-fanout) 스코프.
```

Replace every `<fill>` with the actual value from Task 4. Replace `YYYY-MM-DD` with today's date. If any result in the table differs from the expected pattern (e.g. `add_bio_length_limit` still wrong), **do not hand-edit it to pass** — record the actual result and stop to investigate.

- [ ] **Step 5.2: Commit the spec update**

```bash
git add docs/superpowers/specs/2026-04-11-patch-accuracy-ice-design.md
git commit -m "docs(spec): record post-C6 --ai deference benchmark results"
```

- [ ] **Step 5.3: Final verification**

Run: `python -m pytest tests/ --ignore=tests/benchmark -q`
Expected: all tests still pass.

---

## Out of scope (intentionally deferred)

- **C2 (F2 layer routing)** — `add_email_domain_check` is still misrouted to a utility file. Next ICE round candidate.
- **C4 (F4 multi-fanout)** — `add_password_change` still collapses to a single file. Next ICE round candidate.
- **Prompt/pool improvements for `_ai_select_file`** — the deference rule skips AI entirely on `high` confidence, so the prompt itself is not touched. A follow-up plan may improve the prompt for the `medium`/`low` paths (e.g. passing deterministic top-N with scores), but C6 is scoped to the single minimal fix that reverses the measured regression.
- **C5 (benchmark runner automation)** — still valuable as the guardrail that would have caught this regression automatically; remains a pending candidate.
