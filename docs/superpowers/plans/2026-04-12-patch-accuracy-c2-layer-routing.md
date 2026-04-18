# Patch Accuracy C2 — Layer Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `add_email_domain_check` pinned-intent 시나리오를 해소해 `vib bench --patch` baseline 을 4/5→5/5 (files), 3/4→4/4 (anchor) 로 끌어올린다. 나머지 4 시나리오 회귀 없음.

**Architecture:** 2 파트 합친 구조. (1) `vib_start_cmd.py` 의 `ui_tokens` 에 `pages`/`routes` 추가해 `pages/*.py` 가 `project_map.ui_modules` 에 들어가게 하고, (2) `patch_suggester._score_all_files` 정렬 직후에 `_apply_layer_routing` 후처리 함수를 호출해 "top1 이 non-ui + verb 가 CREATE + ui caller 가 있고 positive score + gate 모두 충족" 일 때만 caller 의 최고 앵커를 BOOST(+18), top1 을 PENALTY(−3) 적용 후 재정렬.

**Tech Stack:** Python 3, unittest, vibelign 내부 모듈. C1 (verb cluster) 이미 구현됨 — `_classify_request_verb`, `_VERB_CLUSTER_CREATE` 등을 재사용. C5 bench runner 이미 baseline 회귀 가드 live.

**Spec:** `docs/superpowers/specs/2026-04-12-patch-accuracy-c2-layer-routing-design.md`

---

## File Structure

**Modified files:**
- `vibelign/commands/vib_start_cmd.py` — `_build_project_map` 의 `ui_tokens` 2단어 추가 (§3.1)
- `vibelign/core/patch_suggester.py` — `_apply_layer_routing` 신규 함수 + `_score_all_files` 내 호출 (§3.2)
- `tests/benchmark/patch_accuracy_baseline.json` — Task 6 에서 `vib bench --patch --update-baseline` 로 갱신

**New test files:**
- `tests/test_layer_routing.py` — `_apply_layer_routing` 단위 테스트 6개 (mock `ProjectMapSnapshot`)

**Extended test files:**
- `tests/test_patch_accuracy_scenarios.py::PatchAccuracyScenarioTest` — `test_add_email_domain_check_selects_signup_handle_signup` 추가
- `tests/test_vib_start.py` (or similar) — `pages/`, `routes/` 가 `ui_modules` 로 분류되는지 회귀 가드

**Intentionally NOT modified:**
- `vibelign/core/project_map.py` — `classify_path` 는 이미 `ui_modules` 를 우선 검사하므로 그대로
- C1 verb cluster 상수/함수 — 재사용
- `_ai_select_file` — C6 deference 가 high confidence 일 때 det 결과를 그대로 통과시키므로 파트 2 가 det 에 붙으면 ai 도 자동 반영

---

## Verb Cluster Reuse Note

C1 이 이미 `vibelign/core/patch_suggester.py:735-863` 에 verb cluster 전체를 구현해 놓았다. Plan 이 사용하는 상수/함수:

- `_VERB_CLUSTER_CREATE = "CREATE"` (line 737)
- `_classify_request_verb(request_tokens)` (line 829) — 마지막 매치 클러스터 반환
- 요청 "회원가입 시 … 검사 **추가**" → `CREATE` (stem "추가" 가 CREATE 매핑, line 762)
- 요청 "로그인 … 버그 **수정**" → `MUTATE` (stems "버그"/"수정" 모두 MUTATE, line 750/753)

C2 gate 2 는 `verb_cluster == _VERB_CLUSTER_CREATE` 로 구현. spec §3.2 가 언급한 ADD/CREATE/INTEGRATE 는 실제로 C1 의 CREATE 하나로 충분 — "추가/생성/만들/신규/add/create/new/register" 전부 CREATE 로 맵핑돼 있음.

---

## Task 1: Part 1 — `pages/`/`routes/` 를 ui_tokens 에 추가

**Files:**
- Modify: `vibelign/commands/vib_start_cmd.py:368`
- Test: `tests/test_vib_start.py` (append)

- [ ] **Step 1: 먼저 test_vib_start.py 의 기존 구조 확인**

Run: `head -60 tests/test_vib_start.py`
Expected: `_build_project_map` 직접 호출하거나 `subprocess.run(["vib", "start"])` 로 검증하는 패턴 확인.

- [ ] **Step 2: 실패하는 회귀 가드 테스트 작성**

`tests/test_vib_start.py` 맨 아래에 추가:

```python
class TestPagesRoutesUiClassification(unittest.TestCase):
    """C2 Part 1: pages/ and routes/ must classify as ui_modules.

    Without this, C2's layer-routing rule can't identify ui-layer callers
    in project_map.files[rel].imported_by.
    """

    def test_pages_directory_is_classified_as_ui(self):
        from vibelign.commands.vib_start_cmd import _build_project_map
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pages").mkdir()
            (root / "pages" / "signup.py").write_text("def handle(): pass\n")
            pm = _build_project_map(root, force_scan=True)
            self.assertIn("pages/signup.py", pm["ui_modules"])

    def test_routes_directory_is_classified_as_ui(self):
        from vibelign.commands.vib_start_cmd import _build_project_map
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "routes").mkdir()
            (root / "routes" / "users.py").write_text("def get(): pass\n")
            pm = _build_project_map(root, force_scan=True)
            self.assertIn("routes/users.py", pm["ui_modules"])
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `python -m pytest tests/test_vib_start.py::TestPagesRoutesUiClassification -v`
Expected: 두 테스트 모두 **FAIL** (AssertionError: 'pages/signup.py' not in [])

- [ ] **Step 4: `ui_tokens` 에 2 단어 추가**

`vibelign/commands/vib_start_cmd.py:368` 수정. 기존:

```python
    ui_tokens = ["ui", "view", "views", "window", "dialog", "widget", "screen"]
```

→ 변경:

```python
    ui_tokens = [
        "ui",
        "view",
        "views",
        "window",
        "dialog",
        "widget",
        "screen",
        "pages",
        "routes",
    ]
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_vib_start.py::TestPagesRoutesUiClassification -v`
Expected: 두 테스트 모두 **PASS**

- [ ] **Step 6: 기존 `test_vib_start*` 회귀 확인**

Run: `python -m pytest tests/test_vib_start.py tests/test_vib_start_hooks.py -v`
Expected: 전부 PASS (신규 2 개 포함).

- [ ] **Step 7: 커밋**

```bash
git add vibelign/commands/vib_start_cmd.py tests/test_vib_start.py
git commit -m "$(cat <<'EOF'
feat(project-map): classify pages/ and routes/ as ui modules

C2 part 1: add "pages" and "routes" to ui_tokens so web-framework
convention directories get the ui classification. Alone this has zero
effect on patch scoring (C1 layer bonus is gated on _is_ui_request
vocabulary), but it's a prerequisite for C2 part 2's caller-routing
rule to identify ui-layer importers.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 파트 1 smoke test — bench 재측정 (회귀 없음 확인)

**Files:**
- Run-only, 파트 1 만 적용한 상태에서 bench 재측정. spec §2.4 에서 empirical 하게 "효과 0" 임을 검증한 것과 일관되는지 확인.

- [ ] **Step 1: uv tool 재설치 (로컬 수정 반영)**

Run: `uv tool install --reinstall --force .`
Expected: 설치 성공 메시지. 에러 시 Task 1 롤백 후 조사.

- [ ] **Step 2: `vib bench --patch` 실행**

Run: `vib bench --patch`
Expected: exit code **1** (regressions 없음이지만 baseline 미달인 상태에서도 exit 0 이어야 정상 — `--update-baseline` 미사용 시 baseline 대비 diff 0 이면 exit 0). 정확한 동작:
- det/ai totals 가 **4/5, 3/4, 4/5** 로 baseline 과 동일
- `regressions == []`
- exit code **0**

만약 totals 가 baseline 과 달라지면 Task 1 에 의도치 않은 부작용이 있는 것 — 커밋 롤백 후 조사.

- [ ] **Step 3: 결과 스냅샷 기록**

Run: `vib bench --patch --json | tail -60` → 현재 터미널에 기록만 (파일로 저장 X, Task 6 에서 갱신되므로)

---

## Task 3: Part 2 단위 테스트 선행 작성 (`tests/test_layer_routing.py`)

**Files:**
- Create: `tests/test_layer_routing.py`

- [ ] **Step 1: 파일 생성 + 공통 mock 헬퍼**

Create `tests/test_layer_routing.py`:

```python
"""Unit tests for _apply_layer_routing (C2 part 2).

Covers the four gates and the boost/penalty arithmetic that flips
ranking when all gates pass. Uses a hand-built ProjectMapSnapshot
fixture — no sandbox, no subprocess.
"""
import unittest
from pathlib import Path

from vibelign.core.project_map import ProjectMapSnapshot


def _make_map(
    ui_modules=frozenset(),
    service_modules=frozenset(),
    core_modules=frozenset(),
    files=None,
):
    return ProjectMapSnapshot(
        schema_version=2,
        project_name="test",
        entry_files=frozenset(),
        ui_modules=ui_modules,
        core_modules=core_modules,
        service_modules=service_modules,
        large_files=frozenset(),
        file_count=0,
        generated_at=None,
        anchor_index={},
        tree=[],
        files=files or {},
    )


class LayerRoutingGateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path("/fake/root")
        self.auth = self.root / "api" / "auth.py"
        self.signup = self.root / "pages" / "signup.py"
        self.validators = self.root / "core" / "validators.py"
```

- [ ] **Step 2: Gate 1 테스트 — top1 이 이미 ui 면 발화 안 함**

Append to `tests/test_layer_routing.py`:

```python
    def test_gate1_ui_top1_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py", "pages/login.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.signup, 10), (self.auth, 5)]
        result = _apply_layer_routing(
            candidates, ["추가", "검사"], pm, self.root
        )
        self.assertEqual(result, candidates)
```

- [ ] **Step 3: Gate 2 테스트 — MUTATE verb 는 발화 안 함**

Append:

```python
    def test_gate2_mutate_verb_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["버그", "수정"], pm, self.root
        )
        self.assertEqual(result, candidates)
```

- [ ] **Step 4: Gate 2 양성 — CREATE verb 는 발화**

Append:

```python
    def test_gate2_create_verb_fires(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["검사", "추가"], pm, self.root
        )
        self.assertNotEqual(result, candidates)
        self.assertEqual(result[0][0], self.signup)
```

- [ ] **Step 5: Gate 3 테스트 — ui importer 없으면 발화 안 함**

Append:

```python
    def test_gate3_no_ui_importer_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset(),
            service_modules=frozenset({"api/auth.py", "api/users.py"}),
            files={
                "api/auth.py": {"imported_by": ["api/users.py"]},
                "api/users.py": {"imported_by": []},
            },
        )
        users = self.root / "api" / "users.py"
        candidates = [(self.auth, 19), (users, 3)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        self.assertEqual(result, candidates)
```

- [ ] **Step 6: Gate 4 테스트 — ui caller 가 0점이면 발화 안 함**

Append:

```python
    def test_gate4_zero_score_caller_does_not_fire(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 0)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        self.assertEqual(result, candidates)
```

- [ ] **Step 7: BOOST/PENALTY 산수 테스트**

Append:

```python
    def test_scoring_flips_ranking_with_expected_arithmetic(self):
        from vibelign.core.patch_suggester import _apply_layer_routing

        pm = _make_map(
            ui_modules=frozenset({"pages/signup.py"}),
            service_modules=frozenset({"api/auth.py"}),
            files={
                "pages/signup.py": {"imported_by": []},
                "api/auth.py": {"imported_by": ["pages/signup.py"]},
            },
        )
        candidates = [(self.auth, 19), (self.signup, 2)]
        result = _apply_layer_routing(
            candidates, ["추가"], pm, self.root
        )
        result_map = {path: score for path, score in result}
        self.assertEqual(result_map[self.signup], 2 + 18)  # BOOST
        self.assertEqual(result_map[self.auth], 19 - 3)    # PENALTY
        self.assertEqual(result[0][0], self.signup)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 8: 6 개 테스트 전부 실패 확인**

Run: `python -m pytest tests/test_layer_routing.py -v`
Expected: 6 개 테스트 모두 **FAIL**: `ImportError: cannot import name '_apply_layer_routing' from 'vibelign.core.patch_suggester'`.

- [ ] **Step 9: 실패 상태 커밋 (TDD red)**

```bash
git add tests/test_layer_routing.py
git commit -m "$(cat <<'EOF'
test(c2): layer routing unit tests (failing — red stage)

6 tests covering the 4 gates and boost/penalty arithmetic for
_apply_layer_routing. Implementation in next commit.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `_apply_layer_routing` 구현 (TDD green)

**Files:**
- Modify: `vibelign/core/patch_suggester.py` — 새 함수 추가 + 호출 삽입

- [ ] **Step 1: `_apply_layer_routing` 함수를 `_score_all_files` **바로 앞** 에 추가**

`vibelign/core/patch_suggester.py` 의 `_score_all_files` 정의(line 1140) 바로 위에 다음을 삽입:

```python
# --- C2 layer routing post-processing ---
#
# After C1 verb-aware scoring ranks files, promote a ui-layer caller over
# a non-ui top1 when the request is a CREATE-style request and the caller
# imports the top1. The four gates protect existing correct routings from
# regressing. See docs/superpowers/specs/2026-04-12-patch-accuracy-c2-
# layer-routing-design.md for the full rationale; tune values only with
# measurement data.
_LAYER_ROUTING_BOOST = 18
_LAYER_ROUTING_PENALTY = 3


def _apply_layer_routing(
    candidates: list[tuple[Path, int]],
    request_tokens: list[str],
    project_map: Optional[ProjectMapSnapshot],
    root: Path,
) -> list[tuple[Path, int]]:
    """Promote a ui-layer caller when the top1 is a non-ui file that the
    caller imports, the request is a CREATE verb, and the caller already
    has a positive base score. See spec §3 for gate definitions.

    Returns the rewritten candidate list sorted descending by score.
    Returns the input unchanged when any gate fails or when project_map
    is None.
    """
    if not candidates or project_map is None:
        return candidates

    top_path, _top_score = candidates[0]
    top_rel = relpath_str(root, top_path)

    # Gate 1: top1 must NOT already be a ui file.
    if project_map.classify_path(top_rel) == "ui":
        return candidates

    # Gate 2: request verb cluster must be CREATE.
    verb_cluster = _classify_request_verb(request_tokens)
    if verb_cluster != _VERB_CLUSTER_CREATE:
        return candidates

    # Gate 3: top1 must have at least one ui-layer importer.
    file_entry = project_map.files.get(top_rel, {})
    raw_importers = file_entry.get("imported_by", [])
    if not isinstance(raw_importers, list):
        return candidates
    ui_importers = [
        rel for rel in raw_importers
        if isinstance(rel, str) and project_map.classify_path(rel) == "ui"
    ]
    if not ui_importers:
        return candidates

    # Gate 4: at least one ui importer must have score > 0 in candidates.
    candidate_by_rel: dict[str, tuple[Path, int]] = {
        relpath_str(root, p): (p, s) for p, s in candidates
    }
    positive_callers = [
        (rel, *candidate_by_rel[rel])
        for rel in ui_importers
        if rel in candidate_by_rel and candidate_by_rel[rel][1] > 0
    ]
    if not positive_callers:
        return candidates

    # Pick the highest-scoring positive ui caller.
    positive_callers.sort(key=lambda item: item[2], reverse=True)
    _, best_path, _ = positive_callers[0]

    new_candidates: list[tuple[Path, int]] = []
    for path, score in candidates:
        if path == best_path:
            new_candidates.append((path, score + _LAYER_ROUTING_BOOST))
        elif path == top_path:
            new_candidates.append((path, score - _LAYER_ROUTING_PENALTY))
        else:
            new_candidates.append((path, score))
    new_candidates.sort(key=lambda item: (-item[1], str(item[0])))
    return new_candidates
```

- [ ] **Step 2: 단위 테스트 6 개 통과 확인**

Run: `python -m pytest tests/test_layer_routing.py -v`
Expected: **6/6 PASS**.

- [ ] **Step 3: 커밋 (green — 함수만, 아직 파이프라인 연결 X)**

```bash
git add vibelign/core/patch_suggester.py
git commit -m "$(cat <<'EOF'
feat(patch): _apply_layer_routing helper for C2

Implements the four gates and boost/penalty arithmetic documented in
the C2 spec. Not yet wired into _score_all_files — the next commit
adds the call site so suggest_patch / score_candidates actually use it.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `_score_all_files` 에 `_apply_layer_routing` 호출 삽입

**Files:**
- Modify: `vibelign/core/patch_suggester.py:1182` (정렬 직후)

- [ ] **Step 1: `_score_all_files` 맨 끝의 return 직전에 후처리 호출 추가**

기존(`_score_all_files` line 1181-1183):

```python
        scored.append((score, path, rationale))
    scored.sort(key=lambda x: (-x[0], str(x[1])))
    return scored, metadata, anchor_meta, project_map, ui_label_idx
```

→ 변경:

```python
        scored.append((score, path, rationale))
    scored.sort(key=lambda x: (-x[0], str(x[1])))

    # C2 layer routing post-processing. See _apply_layer_routing docstring.
    candidates = [(path, score) for score, path, _ in scored]
    rewritten = _apply_layer_routing(candidates, request_tokens, project_map, root)
    if rewritten != candidates:
        rationale_by_path = {path: rationale for _, path, rationale in scored}
        scored = [
            (score, path, rationale_by_path[path] + ["C2 레이어 라우팅 재배치"])
            for path, score in rewritten
        ]
    return scored, metadata, anchor_meta, project_map, ui_label_idx
```

Rationale annotation 은 best-effort — 재배치된 엔트리의 rationale 리스트에 한 줄만 덧붙인다.

- [ ] **Step 2: 단위 테스트 여전히 통과 + 기존 score_candidates 테스트 통과**

Run: `python -m pytest tests/test_layer_routing.py tests/test_patch_suggester_score_candidates.py -v`
Expected: 전부 PASS.

- [ ] **Step 3: 기존 patch 관련 전체 회귀 확인**

Run: `python -m pytest tests/test_patch_suggested_anchor.py tests/test_patch_anchor_priority.py tests/test_patch_project_map_fallback.py tests/test_patch_validation_strict.py tests/test_patch_cmd_wrapper.py tests/test_patch_import_expansion.py tests/test_patch_targeting_regressions.py tests/test_patch_verb_cluster.py -v`
Expected: 전부 PASS. 만약 회귀 있으면 `_apply_layer_routing` 의 gate 로직이 너무 공격적인 것 — spec §3.2 의 gate 조건을 재검토해 해당 케이스가 왜 발화하는지 추적.

- [ ] **Step 4: 커밋**

```bash
git add vibelign/core/patch_suggester.py
git commit -m "$(cat <<'EOF'
feat(patch): wire _apply_layer_routing into _score_all_files

C2 part 2 now active. After the file ranking is sorted, layer routing
rewrites it when the four gates pass (top1 non-ui + CREATE verb + ui
importer with positive score). suggest_patch and score_candidates both
consume the rewritten order automatically.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `add_email_domain_check` 시나리오 회귀 가드 추가

**Files:**
- Modify: `tests/test_patch_accuracy_scenarios.py` — `PatchAccuracyScenarioTest` 에 새 테스트 추가

- [ ] **Step 1: 테스트 추가**

`tests/test_patch_accuracy_scenarios.py` 의 `PatchAccuracyScenarioTest` 클래스 안, `test_add_bio_length_limit_selects_profile_update` 아래에 추가:

```python
    def test_add_email_domain_check_selects_signup_handle_signup(self):
        """C2 regression guard: layer routing must flip auth→signup.

        Without C2, score_candidates ranks api/auth.py top1 via
        AUTH_REGISTER_USER anchor match. C2's layer-routing post-processor
        promotes pages/signup.py (a ui-layer caller of auth) because:
          - top1 (api/auth.py) is classified as "service" (not "ui")
          - request verb is CREATE ("검사 추가")
          - pages/signup.py is in api/auth.py's imported_by and ui-classified
          - pages/signup.py has positive base score from path-token match
        """
        result = self._run("add_email_domain_check")
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")

    def test_add_email_domain_check_ai_mode_also_routes_to_signup(self):
        """C6 deference passes det result through when confidence is high."""
        result = self._run("add_email_domain_check", use_ai=True)
        self.assertEqual(result.target_file, "pages/signup.py")
        self.assertEqual(result.target_anchor, "SIGNUP_HANDLE_SIGNUP")
```

- [ ] **Step 2: 신규 테스트 통과 + 기존 patch_accuracy 시나리오 통과**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: 기존 3 test + 신규 2 test + `TestAIDeference` 2 test = **7/7 PASS**.

만약 `test_add_email_domain_check_*` 가 fail 하면: `_score_all_files` 의 호출 지점이 잘못됐거나, `pages/signup.py` 의 base score 가 sandbox 에서 `0` 인 것. 후자라면 샌드박스를 `prepare_patch_sandbox` 로 만들고 `score_candidates` 를 직접 호출해 pages/signup.py 점수를 확인(spec §2.2 는 점수 2 로 기록).

- [ ] **Step 3: 커밋**

```bash
git add tests/test_patch_accuracy_scenarios.py
git commit -m "$(cat <<'EOF'
test(c2): regression guard for add_email_domain_check flip

Locks in the C2 layer-routing fix: add_email_domain_check must
route to pages/signup.py::SIGNUP_HANDLE_SIGNUP in both det and ai
modes (C6 deference passes det through on high confidence).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `vib bench --patch` baseline 갱신

**Files:**
- Modify: `tests/benchmark/patch_accuracy_baseline.json` (자동 — CLI 로 갱신)

- [ ] **Step 1: uv tool 재설치**

Run: `uv tool install --reinstall --force .`
Expected: 성공 메시지. 재설치 후 `vib` 바이너리가 이번 PR 의 변경을 반영.

- [ ] **Step 2: baseline 갱신 전에 현재 상태 확인**

Run: `vib bench --patch`
Expected: `regressions` 목록에 `change_error_msg`, `fix_login_lock_bug`, `add_bio_length_limit`, `add_password_change` 는 없고, `add_email_domain_check` 는 **improvement** 로 표시. exit code **1** (baseline 과 달라졌으므로 diff 감지).

- [ ] **Step 3: baseline 갱신**

Run: `vib bench --patch --update-baseline`
Expected: exit code **0**. `tests/benchmark/patch_accuracy_baseline.json` 이 수정됨.

- [ ] **Step 4: 갱신된 baseline 검증**

Run: `vib bench --patch`
Expected:
- exit code **0**
- `regressions == []`, `improvements == []`
- totals: det `files_ok: "5/5"`, `anchor_ok: "4/4"`, `recall_at_3: "5/5"`
- totals: ai 도 동일 (C6 deference 효과)

만약 ai totals 가 det 와 다르면: C6 deference 가 low/medium confidence 에서 AI 를 여전히 호출하는 경우인지 확인. spec 상으론 C2 의 det 개선이 high confidence 시 ai 로 전파돼야 함.

- [ ] **Step 5: baseline 커밋**

```bash
git add tests/benchmark/patch_accuracy_baseline.json
git commit -m "$(cat <<'EOF'
chore(bench): update patch accuracy baseline for C2

Post-C2 baseline: det and ai both at 5/5 files, 4/4 anchor, 5/5
recall@3. add_password_change remains the only files_ok=true /
anchor_ok=null entry (multi-file fanout, C4 territory).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 전체 테스트 수트 + 수락 기준 체크

**Files:**
- Run-only. 모든 수락 기준 통과 여부 최종 확인.

- [ ] **Step 1: 전체 테스트 수트 실행**

Run: `python -m pytest tests/ -v 2>&1 | tail -40`
Expected: 전부 PASS. 만약 C2 와 무관한 테스트가 깨지면 Task 1–7 중 어느 단계에서 부작용이 발생한 것 — 커밋 체인을 되짚어 원인 추적.

- [ ] **Step 2: `vib bench --patch --json` 으로 수락 기준 §6 검증**

Run: `vib bench --patch --json`
수락 기준 (spec §6):
- `summary.totals.det.files_ok == "5/5"` ✓
- `summary.totals.det.anchor_ok == "4/4"` ✓
- `summary.totals.ai.files_ok == "5/5"` ✓
- `summary.totals.ai.anchor_ok == "4/4"` ✓
- `diff.regressions == []` ✓
- `summary.scenarios.add_email_domain_check.det.files_ok == true` ✓
- exit code 0 ✓

- [ ] **Step 3: `add_email_domain_check` 의 타겟 파일/앵커 직접 재확인**

Run:

```bash
python3 -c "
import tempfile
from pathlib import Path
from vibelign.commands.bench_fixtures import prepare_patch_sandbox
from vibelign.core.patch_suggester import suggest_patch
with tempfile.TemporaryDirectory() as tmp:
    root = prepare_patch_sandbox(Path(tmp))
    req = '회원가입 시 허용된 이메일 도메인만 통과하도록 검사 추가'
    for use_ai in (False, True):
        p = suggest_patch(root, req, use_ai=use_ai)
        print(f'use_ai={use_ai}: {p.target_file} :: {p.target_anchor} ({p.confidence})')
"
```

Expected 출력:
```
use_ai=False: pages/signup.py :: SIGNUP_HANDLE_SIGNUP (high)
use_ai=True: pages/signup.py :: SIGNUP_HANDLE_SIGNUP (high)
```

- [ ] **Step 4: 커밋 체인 리뷰**

Run: `git log --oneline -10`
Expected: Task 1–7 의 커밋 7개 (+ 기존 spec 커밋) 이 순서대로 보임:

1. `docs(spec): patch accuracy C2 layer routing design` (이미 존재)
2. `feat(project-map): classify pages/ and routes/ as ui modules` (Task 1)
3. `test(c2): layer routing unit tests (failing — red stage)` (Task 3)
4. `feat(patch): _apply_layer_routing helper for C2` (Task 4)
5. `feat(patch): wire _apply_layer_routing into _score_all_files` (Task 5)
6. `test(c2): regression guard for add_email_domain_check flip` (Task 6)
7. `chore(bench): update patch accuracy baseline for C2` (Task 7)

- [ ] **Step 5: 메모리 업데이트**

`~/.claude/projects/-Users-topsphinx-YesonENT-Dropbox-top-sphinx-Mac-Documents-coding-VibeLign/memory/project_patch_accuracy_c1_done.md` 을 갱신하거나 새 메모리 파일 작성:
- C2 완료 표시, baseline 5/5·4/4·5/5
- 남은 실패: add_password_change (C4)
- 다음 후보: C4 (multi-fanout)

구체적 편집은 메모리 시스템의 "types of memory" 가이드를 따라 기존 파일 업데이트 우선.

---

## Rollback Plan

어떤 Task 에서라도 회귀가 발견되면:

1. **Task 1 회귀 (다른 `test_vib_start*` 깨짐)**: `git reset --hard HEAD^` 로 Task 1 커밋 되돌림. "pages"/"routes" 가 무언가의 prefix 로 잡히는 예상 못한 파일을 조사.
2. **Task 4/5 회귀 (기존 patch 테스트 깨짐)**: `_apply_layer_routing` 의 gate 가 너무 관대한 것. `_classify_request_verb` 가 해당 테스트의 요청에 대해 CREATE 를 반환하는지, `imported_by` 가 의도와 다르게 ui importer 를 포함하는지 확인.
3. **Task 7 baseline 에서 불예상 regression**: `_apply_layer_routing` 이 `fix_login_lock_bug` 같은 MUTATE 요청에 발화하는 것. `_classify_request_verb` 가 해당 요청의 last cluster 를 잘못 반환하는지 확인.

롤백 수단: 모든 커밋은 독립이라 `git reset --hard <prev>` 로 개별 되돌릴 수 있다. **예외**: Task 5 (wire-in) 는 Task 4 (helper) 를 전제하므로 함께 되돌릴 것.

---

## Self-Review

- **Spec coverage**: spec §3.1 → Task 1, §3.2 → Task 3-5, §4.3 단위 테스트 → Task 3, §4.2 회귀 보호 → Task 6, §6 수락 기준 → Task 8. ✓
- **Placeholder scan**: "TBD"/"TODO"/"add error handling" 없음. 모든 코드 블록 완결. ✓
- **Type consistency**: `_apply_layer_routing(candidates, request_tokens, project_map, root)` signature 가 Task 3 테스트, Task 4 구현, Task 5 호출 site 에서 전부 동일. `_VERB_CLUSTER_CREATE` 상수, `_classify_request_verb` 함수명 C1 기존 정의와 일치. ✓
- **Task granularity**: 각 step 이 2–5 분 범위. 가장 긴 step 은 Task 4 Step 1 (`_apply_layer_routing` 함수 body 작성) — 약 5 분.
