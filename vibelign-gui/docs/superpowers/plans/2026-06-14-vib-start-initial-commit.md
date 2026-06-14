# vib start 초기 커밋 + stale 오버라이드 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vib start`가 모든 프로젝트에 git 베이스라인(초기 커밋)을 만들어 가이드 변경감지(`changedFileCount`)가 정상 작동하게 하고, 변경이 없을 때 검증 단계(5/6) stale 오버라이드를 정리한다.

**Architecture:** A) `vib_start_cmd.py`에 gitignore 기본값(node_modules/.DS_Store) 추가 + `_ensure_initial_commit`(커밋0일 때만, identity fallback, --no-verify, 훅 설치 전 실행). B) `guide.ts` `resolveOverride`가 inferred<5면 5/6 오버라이드 폐기. 변경집합 코어·inferStep·훅 로직 무변경.

**Tech Stack:** Python(subprocess/git, pytest) + TypeScript(Vitest). 기존 헬퍼 재사용: `_find_git_exe`, `WINDOWS_SUBPROCESS_FLAGS`.

**Spec:** `docs/superpowers/specs/2026-06-14-vib-start-initial-commit-design.md`

---

## File Structure
- Modify `vibelign/commands/vib_start_cmd.py` — gitignore 상수 2개 + `_ensure_initial_commit` 함수 + 호출부.
- Modify `tests/test_vib_start.py` — `_ensure_initial_commit`·gitignore 테스트.
- Modify `vibelign-gui/src/lib/nav/guide.ts` — `resolveOverride` 1조건.
- Modify `vibelign-gui/src/lib/nav/guide.test.ts` — resolveOverride 케이스.

---

## Task 1: gitignore 기본값 확장 + `_ensure_initial_commit` (Python, TDD)

**Files:** Modify `vibelign/commands/vib_start_cmd.py`, `tests/test_vib_start.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_vib_start.py` 끝에. (상단에 `import subprocess` 가 이미 있으면 재사용; `from vibelign.commands.vib_start_cmd import _ensure_initial_commit, _ensure_gitignore_entry, _find_git_exe` 추가.)

```python
def _git(root, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)

def test_ensure_initial_commit_creates_baseline(tmp_path):
    from vibelign.commands.vib_start_cmd import _ensure_initial_commit
    _git(tmp_path, "init")
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    assert _ensure_initial_commit(tmp_path) is True
    count = _git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip()
    assert count == "1"

def test_ensure_initial_commit_skips_when_commits_exist(tmp_path):
    from vibelign.commands.vib_start_cmd import _ensure_initial_commit
    _git(tmp_path, "init")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "first")
    assert _ensure_initial_commit(tmp_path) is False
    assert _git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

def test_ensure_initial_commit_no_git(tmp_path, monkeypatch):
    import vibelign.commands.vib_start_cmd as m
    monkeypatch.setattr(m, "_find_git_exe", lambda: None)
    assert m._ensure_initial_commit(tmp_path) is False

def test_gitignore_includes_node_modules_and_dsstore(tmp_path):
    from vibelign.commands.vib_start_cmd import _ensure_gitignore_entry
    _ensure_gitignore_entry(tmp_path)
    body = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in body
    assert ".DS_Store" in body
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_vib_start.py -k "ensure_initial_commit or gitignore_includes" -q` → ImportError/AttributeError(미정의) 또는 assert 실패.

- [ ] **Step 3: 구현.** (a) 상수 추가 — `GITIGNORE_LOGS_LINE` 등 상수 묶음(라인 40~45) 다음에:
```python
GITIGNORE_NODE_MODULES_LINE = "node_modules/"
GITIGNORE_DS_STORE_LINE = ".DS_Store"
```
(b) `_ensure_gitignore_entry`의 `lines_to_add` 리스트(현재 `GITIGNORE_LINE`~`GITIGNORE_REPORTS_LINE`)에 두 상수를 추가:
```python
        for line in [
            GITIGNORE_LINE,
            GITIGNORE_RUST_CHECKPOINTS_LINE,
            GITIGNORE_RUST_OBJECTS_LINE,
            GITIGNORE_SCAN_CACHE_LINE,
            GITIGNORE_LOGS_LINE,
            GITIGNORE_REPORTS_LINE,
            GITIGNORE_NODE_MODULES_LINE,
            GITIGNORE_DS_STORE_LINE,
        ]
```
(c) `_init_git` 함수 바로 다음(`# === ANCHOR: VIB_START_CMD__HAS_GIT_END ===` 위)에 `_ensure_initial_commit` 추가:
```python
def _ensure_initial_commit(root: Path) -> bool:
    """커밋이 0개인 repo에만 초기 베이스라인 커밋을 만든다. 기존 커밋/실패/git없음 → False."""
    git = _find_git_exe()
    if not git:
        return False
    try:
        head = subprocess.run(
            [git, "rev-parse", "--verify", "HEAD"],
            cwd=root, capture_output=True, creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        if head.returncode == 0:
            return False  # 이미 커밋 있음 — 히스토리 불변
        subprocess.run(
            [git, "add", "-A"], cwd=root, check=True, capture_output=True,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        staged = subprocess.run(
            [git, "diff", "--cached", "--quiet"],
            cwd=root, capture_output=True, creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        if staged.returncode == 0:
            return False  # staged 비어있음(빈 디렉터리)
        subprocess.run(
            [git, "-c", "user.name=VibeLign", "-c", "user.email=vibelign@local",
             "commit", "--no-verify", "-m", "chore: 초기 베이스라인 (VibeLign)"],
            cwd=root, check=True, capture_output=True,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False
```

- [ ] **Step 4: 통과 확인** — `python -m pytest tests/test_vib_start.py -k "ensure_initial_commit or gitignore_includes" -q` → 4 passed.

- [ ] **Step 5: 커밋**
```bash
git add vibelign/commands/vib_start_cmd.py tests/test_vib_start.py
git commit -m "feat(vib-start): 초기 베이스라인 커밋 보장 + gitignore node_modules/.DS_Store (A)"
```

---

## Task 2: 호출부 배선 (Python)

**Files:** Modify `vibelign/commands/vib_start_cmd.py`

- [ ] **Step 1: 호출부 수정.** `git_active` 결정 블록(현재 `secret_hook_result = install_pre_commit_secret_hook(...)` 바로 위)에 gitignore 적용 + 초기 커밋을 **훅 설치 전**에 삽입. 다음 블록을:
```python
    secret_hook_result = install_pre_commit_secret_hook(root) if git_active else None
```
이렇게 앞에 추가:
```python
    if git_active:
        _ensure_gitignore_entry(root)
        if _ensure_initial_commit(root):
            clack_success("초기 베이스라인 커밋을 만들었어요 (변경 추적 시작)")
    secret_hook_result = install_pre_commit_secret_hook(root) if git_active else None
```

> 근거: 훅 설치 **이전**에 커밋해 pre-commit 비밀훅 간섭을 원천 차단(스펙 §4). `_ensure_gitignore_entry`는 멱등이라 다른 곳에서 또 불려도 무해. `_ensure_initial_commit`은 커밋0일 때만 동작하므로 기존 repo 영향 없음.

- [ ] **Step 2: 회귀 확인** — `python -m pytest tests/test_vib_start.py -q` → 기존 전부 통과(호출부 변경이 기존 테스트 깨지면 수정, 단 커버리지 약화 금지).

- [ ] **Step 3: 커밋**
```bash
git add vibelign/commands/vib_start_cmd.py
git commit -m "feat(vib-start): git_active 시 gitignore+초기커밋을 훅 설치 전 실행"
```

---

## Task 3: resolveOverride stale 정리 (TypeScript, TDD)

**Files:** Modify `vibelign-gui/src/lib/nav/guide.ts`, `vibelign-gui/src/lib/nav/guide.test.ts`

작업 디렉터리: `vibelign-gui`.

- [ ] **Step 1: 실패 테스트 추가** — `src/lib/nav/guide.test.ts`. import에 `resolveOverride` 추가(없으면)하고, 새 describe 추가:
```ts
describe("resolveOverride", () => {
  test("변경 없음(4)이면 5 오버라이드 폐기", () => {
    expect(resolveOverride({ step: 5, baseInferred: 4 }, 4)).toBe(4);
  });
  test("변경 없음(4)이면 6 오버라이드 폐기", () => {
    expect(resolveOverride({ step: 6, baseInferred: 5 }, 4)).toBe(4);
  });
  test("검증할 변경 있음(5)이면 5 오버라이드 유지", () => {
    expect(resolveOverride({ step: 5, baseInferred: 5 }, 5)).toBe(5);
  });
  test("전방 이동 오버라이드(2·3·4)는 baseInferred 일치 시 유지", () => {
    expect(resolveOverride({ step: 4, baseInferred: 3 }, 3)).toBe(4);
  });
  test("오버라이드 없으면 inferred", () => {
    expect(resolveOverride(null, 4)).toBe(4);
  });
});
```
(`resolveOverride`·`GuideOverride` 가 guide.ts에서 export 되는지 확인; `resolveOverride`는 export됨. import 라인에 추가.)

- [ ] **Step 2: 실패 확인** — `npx vitest run src/lib/nav/guide.test.ts` → "5 오버라이드 폐기" 케이스 FAIL(현재는 5 반환).

- [ ] **Step 3: 구현.** `resolveOverride`를 교체:
```ts
export function resolveOverride(
  override: GuideOverride | null,
  inferred: ActiveGuideStep,
): ActiveGuideStep {
  if (!override) return inferred;
  // 5️⃣/6️⃣(검증·저장)는 검증할 변경이 있을 때만 의미 — 변경 없음(4)으로 떨어지면 stale 오버라이드 폐기.
  if (override.step >= 5 && inferred < 5) return inferred;
  if (override.baseInferred === inferred) return override.step;
  return inferred;
}
```

- [ ] **Step 4: 통과 확인** — `npx vitest run src/lib/nav/guide.test.ts && npx tsc --noEmit` → 전부 통과, tsc 클린.

- [ ] **Step 5: 커밋**
```bash
git add vibelign-gui/src/lib/nav/guide.ts vibelign-gui/src/lib/nav/guide.test.ts
git commit -m "fix(guide): 변경 없음(4)일 때 검증/저장(5·6) stale 오버라이드 폐기 (B)"
```

---

## Task 4: 전체 검증

- [ ] **Step 1: Python** — repo 루트에서 `python -m pytest tests/test_vib_start.py -q` → 전부 통과.
- [ ] **Step 2: 프론트** — `cd vibelign-gui && npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests "` → tsc 클린, 전부 통과.
- [ ] **Step 3: 수동 통합** — 새 임시 폴더에 `vib start` → `git rev-list --count HEAD` == 1 확인 + `.gitignore`에 node_modules/ 포함 확인. (Windows는 코드 리뷰 대체.)
- [ ] **Step 4: 보고**(커밋 없음).

---

## Self-Review (작성자 점검 완료)
- **스펙 커버리지**: A-1 gitignore→Task1(상수+lines_to_add), A-2 `_ensure_initial_commit`→Task1, A-3 호출부(훅 전)→Task2, B resolveOverride→Task3, 테스트→각 Task TDD + Task4. 매핑 완료.
- **플레이스홀더 없음**: 코드/명령/기대 구체.
- **타입/시그니처 일관**: `_ensure_initial_commit(root: Path) -> bool`, `_ensure_gitignore_entry(root)`, `_find_git_exe()`, `resolveOverride(override, inferred)`/`GuideOverride{step,baseInferred}` — 정의·사용·테스트 일치. 상수명 `GITIGNORE_NODE_MODULES_LINE`/`GITIGNORE_DS_STORE_LINE` 정의=사용 일치.
- **위험**: 호출부에서 `_ensure_gitignore_entry` 중복 호출 가능(멱등이라 무해). pre-commit 훅은 커밋이 훅 설치 전이라 미발동 + `--no-verify` 이중 안전.
