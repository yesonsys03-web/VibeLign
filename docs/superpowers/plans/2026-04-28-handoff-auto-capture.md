# Handoff Auto-Capture Implementation Plan (v2 — revised after internal review)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vib transfer --handoff` 단독 실행만으로도 Claude 가 직접 작성한 수준의 풍부한 Session Handoff 가 PROJECT_CONTEXT.md 에 자동 합성되도록, work_memory.json 의 `decisions / verification / relevant_files / recent_events(kind="commit")` 를 *사용자 행동 변경 없이* 누적 채우는 인프라를 추가한다. **`decisions[-1]` 이 자동으로 active_intent 가 되는 기존 의미를 보존하기 위해, decisions[] 는 오직 명시적 의도 표현 (AI 의 `transfer_set_decision` 호출) 으로만 채운다.**

**Architecture:**
work_memory.py 의 기존 API (`add_decision / add_verification / record_event`) 위에 얇은 입력 어댑터를 추가:
- ① **git post-commit 훅** → `record_commit(...)` 가 `recent_events.kind="commit"` 으로 기록 (decisions 아님). commit 메시지는 *fact* 로만 흐르고 active_intent 를 오염시키지 않음.
- ② **mcp_dispatch 후처리 훅** — `guard_check → add_verification`, `checkpoint_create → record_checkpoint(...)` 가 `recent_events.kind="checkpoint"` 으로 기록, `patch_apply` 는 `strict_patch` 파싱해 *relevant_files 1건만* (decisions 아님, top-level/strict_patch dry_run 은 모두 skip).
- ③ **AI 자율 호출용 신규 MCP 도구 3개** — `transfer_set_decision / verification / relevant`. `decisions[]` 는 이 경로로만 채워짐.

기존 `build_transfer_summary` (work_memory.py:410+) 와 `vib_transfer_cmd.py` 와이어링은 그대로 사용. PROJECT_CONTEXT.md 합성 로직 변경 0.

**Tech Stack:** Python 3.10+, pytest, vibelign 기존 모듈 (work_memory, git_hooks, mcp_dispatch, mcp_transfer_handlers, mcp_handler_registry, mcp_tool_specs, vib_start_cmd, cli_command_groups), shell (post-commit hook).

---

## 검증된 사실 (이 plan 의 기반)

- `work_memory.py:506` `summary["active_intent"] = state["decisions"][-1]` — decisions[] 오염 시 핸드오프 핵심 목표가 잘못 잡힘 ⇒ 자동 캡처는 decisions[] 절대 안 건드림
- `mcp_tool_specs.py:141, 159` patch_apply required = `["strict_patch"]` ⇒ 자동 캡처는 strict_patch 객체 파싱
- `git_hooks.py:18` `HookInstallResult(status, path)` (frozen dataclass), `:47 get_hooks_dir(root)` ⇒ worktree/submodule 안전 처리
- `git_hooks.py:100` 기존 pre-commit 의 fallback 메시지가 `vib` 와 `vibelign` 둘 다 검색함 ⇒ post-commit 도 동일 fallback 패턴 사용
- `work_memory.py:22-37` `WORK_MEMORY_EXCLUDED_DIRS = {".omc", ".vibelign"}` + `_is_excluded_memory_path` ⇒ relevant_files 입력 시 이미 안전 필터됨
- `tests/test_mcp_tool_snapshot.py:74` tool 이름 *순서까지* assert ⇒ 새 도구 추가 시 갱신 필수

---

## File Structure

**Created:**
- `vibelign/commands/internal_record_commit_cmd.py` — `_internal_record_commit` 실행 로직 (stdin commit message → `record_commit`)
- `tests/test_handoff_auto_capture.py` — end-to-end (commit → recent_events, MCP → decisions/verification, vib transfer → PROJECT_CONTEXT)
- `tests/test_work_memory_relevant_api.py` — `add_relevant_file` 단위
- `tests/test_work_memory_record_commit.py` — `record_commit` / `record_checkpoint` 단위
- `tests/test_git_hooks_post_commit.py` — install/uninstall + worktree + 기존 hook exit 케이스
- `tests/test_mcp_dispatch_capture.py` — dispatch 자동 캡처 + 명시 MCP 도구 + dry_run skip + tool 결과 부수효과 0

**Modified:**
- `vibelign/core/work_memory.py` — `add_relevant_file(path, file_path, why)`, `record_commit(path, sha, message)`, `record_checkpoint(path, message)` 신규
- `vibelign/mcp/mcp_transfer_handlers.py` — `handle_transfer_set_decision/verification/relevant` 3개
- `vibelign/mcp/mcp_handler_registry.py` — 위 3개 dispatch 등록
- `vibelign/mcp/mcp_tool_specs.py` — 위 3개 spec 추가
- `vibelign/mcp/mcp_dispatch.py` — call_tool_dispatch 후처리 훅 (3개 도구만 매핑)
- `vibelign/core/git_hooks.py` — `install_post_commit_record_hook / uninstall_*`
- `vibelign/cli/cli_command_groups.py` — internal subcommand `_internal_record_commit` 등록만 담당
- `vibelign/commands/vib_start_cmd.py` — `_setup_project` 에서 새 훅 자동 설치
- `tests/test_mcp_tool_snapshot.py` — 새 도구 3개 이름/순서/required 갱신
- `AGENTS.md` / `CLAUDE.md` / `OPENCODE.md` — narrative discipline 규칙 (decisions 는 *명시* 호출 강조)

**Total**: 6 new files (~530 lines), 11 modified files (~270 lines), 0 schema changes.

---

## Task 1: Public `add_relevant_file` API

**Files:**
- Modify: `vibelign/core/work_memory.py` (private `_append_relevant_file` 직후 line ~305 에 public 함수 추가)
- Test: `tests/test_work_memory_relevant_api.py` (신규)

- [ ] **Step 1: Write failing test**

`tests/test_work_memory_relevant_api.py`:

```python
import tempfile
import unittest
from pathlib import Path
from vibelign.core.work_memory import add_relevant_file, load_work_memory


class AddRelevantFileTest(unittest.TestCase):
    def test_appends_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "vibelign/core/work_memory.py", "core narrative store")
            state = load_work_memory(wm)
            self.assertEqual(
                state["relevant_files"][-1],
                {"path": "vibelign/core/work_memory.py", "why": "core narrative store"},
            )

    def test_dedups_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "a.py", "first")
            add_relevant_file(wm, "a.py", "updated")
            state = load_work_memory(wm)
            self.assertEqual(len(state["relevant_files"]), 1)
            self.assertEqual(state["relevant_files"][0]["why"], "updated")

    def test_skips_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "/absolute/path", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])

    def test_skips_excluded_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, ".omc/state/x.json", "skip")
            add_relevant_file(wm, ".vibelign/work_memory.json", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])

    def test_skips_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            add_relevant_file(wm, "../escape", "skip")
            self.assertEqual(load_work_memory(wm)["relevant_files"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_work_memory_relevant_api.py -v`
Expected: ImportError on `add_relevant_file`

- [ ] **Step 3: Implement public function**

Insert just before `# === ANCHOR: WORK_MEMORY_RECORD_EVENT_START ===`:

```python
# === ANCHOR: WORK_MEMORY_ADD_RELEVANT_FILE_START ===
def add_relevant_file(path: Path, file_path: str, why: str) -> None:
    """Public 진입점 — relevant_files 에 entry 추가 (dedup, 절대/제외경로 차단).

    Why: 기존 _append_relevant_file 은 record_event 내부 헬퍼였음.
         MCP 도구·hook 등 외부 호출자가 직접 부를 public API.
    """
    state = load_work_memory(path)
    state["relevant_files"] = _append_relevant_file(
        state["relevant_files"], file_path, why
    )
    state["updated_at"] = _utc_now()
    save_work_memory(path, state)
# === ANCHOR: WORK_MEMORY_ADD_RELEVANT_FILE_END ===
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_work_memory_relevant_api.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/work_memory.py tests/test_work_memory_relevant_api.py
git commit -m "$(cat <<'EOF'
feat(work_memory): public add_relevant_file API

기존 _append_relevant_file 은 record_event 내부 헬퍼였음. MCP 도구/hook 이
직접 relevant_files 에 entry 를 추가할 수 있도록 public 진입점 추가. 절대경로/
.omc/.vibelign/parent traversal 은 _safe_relative_path 가 그대로 차단.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Public `record_commit` API + record_event 어댑터

**Files:**
- Modify: `vibelign/core/work_memory.py` (record_event 직후에 record_commit 추가)
- Test: `tests/test_work_memory_record_commit.py` (신규)

**왜:** 기존 `record_event(rel_path, ...)` 는 *파일 경로* 를 검증하는데, commit 은 file 단위 이벤트가 아님. `record_commit(sha, message)` 가 `recent_events` 에 `kind="commit"` 으로 안전하게 기록.

- [ ] **Step 1: Write failing test**

`tests/test_work_memory_record_commit.py`:

```python
import tempfile
import unittest
from pathlib import Path
from vibelign.core.work_memory import record_commit, load_work_memory


class RecordCommitTest(unittest.TestCase):
    def test_appends_commit_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234deadbeef", "feat(mcp): new tool")
            state = load_work_memory(wm)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "commit")
            self.assertEqual(event["message"], "feat(mcp): new tool")
            self.assertIn("abc1234", event["path"])

    def test_does_not_touch_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "chore: bump 2.0.35")
            state = load_work_memory(wm)
            self.assertEqual(state["decisions"], [])

    def test_handles_multiline_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            msg = "feat: x\n\nbody line\nbody line 2\n\n한글 ✨"
            record_commit(wm, "abc1234", msg)
            event = load_work_memory(wm)["recent_events"][-1]
            # truncate 후에도 첫 줄과 한글 보존
            self.assertIn("feat: x", event["message"])

    def test_skips_blank_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            record_commit(wm, "abc1234", "")
            self.assertEqual(load_work_memory(wm)["recent_events"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_work_memory_record_commit.py -v`
Expected: ImportError on `record_commit`

- [ ] **Step 3: Implement record_commit**

Insert after `record_warning` end anchor (around line 372):

```python
# === ANCHOR: WORK_MEMORY_RECORD_COMMIT_START ===
def record_commit(path: Path, sha: str, message: str) -> None:
    """recent_events 에 kind="commit" entry 추가. decisions[] 는 건드리지 않음.

    Why: commit 메시지는 사실(fact) 이지 의사결정(decision) 이 아님.
         decisions[-1] → active_intent 매핑이 release commit 으로 오염되지 않도록
         별도 bucket (recent_events) 으로 격리한다. multi-line / 한글 / 이모지 안전.
    """
    text = _truncate_text(message)
    if not text:
        return
    short = (sha or "")[:12] or "unknown"
    try:
        state = load_work_memory(path)
        event: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": "commit",
            "path": f"git/{short}",
            "message": text,
            "action": "",
        }
        state["recent_events"].append(event)
        state["updated_at"] = event["time"]
        save_work_memory(path, state)
    except Exception:
        return
# === ANCHOR: WORK_MEMORY_RECORD_COMMIT_END ===
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_work_memory_record_commit.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/work_memory.py tests/test_work_memory_record_commit.py
git commit -m "$(cat <<'EOF'
feat(work_memory): record_commit API — commit 을 사실로만 기록 (decisions 미오염)

post-commit 훅이 사용할 진입점. recent_events 에 kind="commit" 으로 누적해
build_transfer_summary 의 change_details / 변경 파일 섹션에 자연스럽게 합류.
decisions[-1] → active_intent 의미를 보존하기 위해 decisions[] 는 절대 건드리지
않는다.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2.5: Public `record_checkpoint` API (synthetic checkpoint event)

**Files:**
- Modify: `vibelign/core/work_memory.py` (`record_commit` 직후에 `record_checkpoint` 추가)
- Test: `tests/test_work_memory_record_commit.py` (같은 파일에 checkpoint event 케이스 추가)

**왜:** `record_event()` 는 파일 경로 기반 이벤트 API라 `_safe_relative_path()` 와 `relevant_files` 갱신 흐름을 탄다. `checkpoint_create` 는 실제 파일 변경이 아니라 state save fact 이므로, commit 과 같은 synthetic event 전용 API 로 분리해야 relevant_files 를 오염시키지 않는다.

- [ ] **Step 1: Add failing tests**

`tests/test_work_memory_record_commit.py` 에 추가:

```python
class RecordCheckpointTest(unittest.TestCase):
    def test_appends_checkpoint_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            from vibelign.core.work_memory import record_checkpoint
            record_checkpoint(wm, "v2.0.35 작업 전 안전 저장")

            state = load_work_memory(wm)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "checkpoint")
            self.assertEqual(event["path"], "checkpoint")
            self.assertIn("v2.0.35", event["message"])
            self.assertEqual(state["decisions"], [])
            self.assertEqual(state["relevant_files"], [])

    def test_skips_blank_checkpoint_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm = Path(tmp) / "work_memory.json"
            from vibelign.core.work_memory import record_checkpoint
            record_checkpoint(wm, "")
            self.assertEqual(load_work_memory(wm)["recent_events"], [])
```

- [ ] **Step 2: Implement record_checkpoint**

Insert after `record_commit`:

```python
# === ANCHOR: WORK_MEMORY_RECORD_CHECKPOINT_START ===
def record_checkpoint(path: Path, message: str) -> None:
    """recent_events 에 kind="checkpoint" entry 추가. decisions/relevant_files 는 건드리지 않음.

    Why: checkpoint_create 는 파일 변경이 아니라 state-save fact 이므로 record_event 의
         파일 경로/relevant_files 경로와 분리한다.
    """
    text = _truncate_text(message)
    if not text:
        return
    try:
        state = load_work_memory(path)
        event: WorkMemoryEvent = {
            "time": _utc_now(),
            "kind": "checkpoint",
            "path": "checkpoint",
            "message": text,
            "action": "",
        }
        state["recent_events"].append(event)
        state["updated_at"] = event["time"]
        save_work_memory(path, state)
    except Exception:
        return
# === ANCHOR: WORK_MEMORY_RECORD_CHECKPOINT_END ===
```

- [ ] **Step 3: Run tests**

Run: `uv run --with pytest pytest tests/test_work_memory_record_commit.py -v`
Expected: commit + checkpoint unit tests passed

- [ ] **Step 4: Commit**

```bash
git add vibelign/core/work_memory.py tests/test_work_memory_record_commit.py
git commit -m "$(cat <<'EOF'
feat(work_memory): record_checkpoint synthetic event API

checkpoint_create 는 파일 변경이 아니라 state-save fact 이므로 record_event
의 _safe_relative_path / relevant_files 자동 갱신 흐름과 분리한다. 동일 파일에
record_commit 과 record_checkpoint 두 synthetic event API 가 함께 산다.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 3 MCP 도구 + tool snapshot 갱신

**Files:**
- Modify: `vibelign/mcp/mcp_transfer_handlers.py` (3 handlers)
- Modify: `vibelign/mcp/mcp_handler_registry.py` (DISPATCH_TABLE 등록 + 3 wrappers)
- Modify: `vibelign/mcp/mcp_tool_specs.py` (3 specs)
- Modify: `tests/test_mcp_tool_snapshot.py` (새 도구 이름·순서·required 갱신)
- Test: `tests/test_mcp_dispatch_capture.py` (신규, 명시 MCP 호출)

- [ ] **Step 1: Write failing test (명시 MCP 호출)**

`tests/test_mcp_dispatch_capture.py`:

```python
import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import load_work_memory
from vibelign.mcp.mcp_dispatch import call_tool_dispatch


def _tc(**kw: Any) -> Any:
    return {"type": kw.get("type"), "text": kw.get("text")}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TransferMCPToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _wm(self):
        return load_work_memory(MetaPaths(self.root).work_memory_path)

    def test_set_decision_appends_to_decisions(self):
        _run(call_tool_dispatch("transfer_set_decision",
            {"text": "1-B 옵션 채택"}, root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["decisions"][-1], "1-B 옵션 채택")

    def test_set_verification_appends_to_verification(self):
        _run(call_tool_dispatch("transfer_set_verification",
            {"text": "pytest -> 12 passed"}, root=self.root, text_content=_tc))
        self.assertIn("12 passed", self._wm()["verification"][-1])

    def test_set_relevant_appends_to_relevant_files(self):
        _run(call_tool_dispatch("transfer_set_relevant",
            {"path": "vibelign/core/work_memory.py", "why": "core"},
            root=self.root, text_content=_tc))
        self.assertEqual(
            self._wm()["relevant_files"][-1],
            {"path": "vibelign/core/work_memory.py", "why": "core"})

    def test_set_decision_requires_text(self):
        result = _run(call_tool_dispatch("transfer_set_decision",
            {}, root=self.root, text_content=_tc))
        self.assertIn("text 인자가 필요", result[0]["text"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_mcp_dispatch_capture.py -v`
Expected: 4 fails — "알 수 없는 도구"

- [ ] **Step 3: Add 3 handler functions**

In `vibelign/mcp/mcp_transfer_handlers.py` append:

```python
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_DECISION_START ===
def handle_transfer_set_decision(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.work_memory import add_decision
    text = arguments.get("text")
    if not isinstance(text, str) or not text.strip():
        return _text(text_content, "transfer_set_decision: text 인자가 필요해요.")
    add_decision(MetaPaths(root).work_memory_path, text)
    return _text(text_content, f"decisions[] 에 추가됨: {text[:60]}")
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_DECISION_END ===


# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_VERIFICATION_START ===
def handle_transfer_set_verification(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.work_memory import add_verification
    text = arguments.get("text")
    if not isinstance(text, str) or not text.strip():
        return _text(text_content, "transfer_set_verification: text 인자가 필요해요.")
    add_verification(MetaPaths(root).work_memory_path, text)
    return _text(text_content, f"verification[] 에 추가됨: {text[:60]}")
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_VERIFICATION_END ===


# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_RELEVANT_START ===
def handle_transfer_set_relevant(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.work_memory import add_relevant_file
    file_path = arguments.get("path")
    why = arguments.get("why", "Relevant to recent work.")
    if not isinstance(file_path, str) or not file_path.strip():
        return _text(text_content, "transfer_set_relevant: path 인자가 필요해요.")
    if not isinstance(why, str):
        why = "Relevant to recent work."
    add_relevant_file(MetaPaths(root).work_memory_path, file_path, why)
    return _text(text_content, f"relevant_files[] 에 추가됨: {file_path}")
# === ANCHOR: MCP_TRANSFER_HANDLERS_HANDLE_TRANSFER_SET_RELEVANT_END ===
```

- [ ] **Step 4: Wire DISPATCH_TABLE in mcp_handler_registry.py**

(`grep -n DISPATCH_TABLE vibelign/mcp/mcp_handler_registry.py` 위치 확인 후) dict 안에 추가:

```python
    "transfer_set_decision": _handle_transfer_set_decision,
    "transfer_set_verification": _handle_transfer_set_verification,
    "transfer_set_relevant": _handle_transfer_set_relevant,
```

위 3 wrappers (기존 `_handle_anchor_set_intent` 패턴 모방, 약 line 269 이후):

```python
def _handle_transfer_set_decision(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
) -> list[object]:
    from vibelign.mcp.mcp_transfer_handlers import handle_transfer_set_decision
    return handle_transfer_set_decision(root, arguments, text_content)


def _handle_transfer_set_verification(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
) -> list[object]:
    from vibelign.mcp.mcp_transfer_handlers import handle_transfer_set_verification
    return handle_transfer_set_verification(root, arguments, text_content)


def _handle_transfer_set_relevant(
    root: Path, arguments: dict[str, object], text_content: TextContentFactory
) -> list[object]:
    from vibelign.mcp.mcp_transfer_handlers import handle_transfer_set_relevant
    return handle_transfer_set_relevant(root, arguments, text_content)
```

- [ ] **Step 5: Add 3 tool specs**

`mcp_tool_specs.py` 의 anchor_set_intent 직후에 (line ~242 부근):

```python
    {
        "name": "transfer_set_decision",
        "description": "현재 세션의 의사결정을 work_memory.decisions 에 누적합니다. PROJECT_CONTEXT.md 의 active_intent / Decision context 에 자동 반영됩니다. 두 옵션 사이에서 선택할 때, 의도가 바뀔 때 호출하세요. WHY 포함 권장.",
        "inputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "description": "결정 내용 한 줄."}},
        },
    },
    {
        "name": "transfer_set_verification",
        "description": "테스트/검증 결과를 work_memory.verification 에 누적합니다. PROJECT_CONTEXT.md 의 Verification snapshot 에 자동 반영됩니다.",
        "inputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {"text": {"type": "string", "description": "검증 명령 + 결과."}},
        },
    },
    {
        "name": "transfer_set_relevant",
        "description": "이번 세션의 핵심 파일을 work_memory.relevant_files 에 등록합니다. PROJECT_CONTEXT.md 의 Relevant files 에 자동 반영됩니다.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "프로젝트 루트 기준 상대 경로"},
                "why": {"type": "string", "description": "왜 이 파일이 핵심인가."}
            },
        },
    },
```

- [ ] **Step 6: Update tool snapshot test**

`tests/test_mcp_tool_snapshot.py:74-105` 영역 — anchor_set_intent 항목 직후에 새 도구 3개 추가 (현재 spec 순서대로):

```python
# 기존 list 어딘가:
"anchor_set_intent",
"transfer_set_decision",      # NEW
"transfer_set_verification",  # NEW
"transfer_set_relevant",      # NEW
```

`by_name` 검증부에도 3개 도구의 required 필드 assert 추가:

```python
self.assertEqual(by_name["transfer_set_decision"].inputSchema["required"], ["text"])
self.assertEqual(by_name["transfer_set_verification"].inputSchema["required"], ["text"])
self.assertEqual(by_name["transfer_set_relevant"].inputSchema["required"], ["path"])
```

- [ ] **Step 7: Run all related tests**

Run: `uv run --with pytest pytest tests/test_mcp_dispatch_capture.py tests/test_mcp_tool_snapshot.py -v`
Expected: 4 + (snapshot test count) passed

- [ ] **Step 8: Commit**

```bash
git add vibelign/mcp/mcp_transfer_handlers.py vibelign/mcp/mcp_handler_registry.py vibelign/mcp/mcp_tool_specs.py tests/test_mcp_dispatch_capture.py tests/test_mcp_tool_snapshot.py
git commit -m "$(cat <<'EOF'
feat(mcp): transfer_set_decision/verification/relevant MCP 도구 추가

AI 가 작업 중 work_memory 의 decisions / verification / relevant_files 를
직접 누적할 수 있는 3개 MCP 도구. build_transfer_summary 가 이미 그 필드를
PROJECT_CONTEXT.md 의 active_intent / verification / relevant 칸에 매핑하므로
이게 추가되면 vib transfer --handoff 결과가 즉시 풍부해진다.

decisions[-1] → active_intent 의미를 보존하려고 decisions[] 는 *명시적* 호출만
받는다 (자동 캡처 경로에서는 절대 안 건드림 — Task 4 참조).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: mcp_dispatch 후처리 훅 (보수적 자동 캡처)

**Files:**
- Modify: `vibelign/mcp/mcp_dispatch.py`
- Test: `tests/test_mcp_dispatch_capture.py` (Task 3 파일에 클래스 추가)

**자동 캡처 정책 (의도적으로 좁게):**
| 도구 | 자동 캡처 동작 | 절대 안 하는 동작 |
|---|---|---|
| `guard_check` | 결과 텍스트 → `add_verification` | decisions[] 안 건드림 |
| `checkpoint_create` | message → `record_checkpoint` (recent_events) | decisions[] / relevant_files[] 안 건드림 |
| `patch_apply` (실 적용) | strict_patch → target file → `add_relevant_file` 1건 | decisions[] 안 건드림 |
| `patch_apply` (dry_run) | top-level `dry_run=True` 또는 `strict_patch.dry_run=True` 모두 아무 것도 안 함 | — |
| 기타 도구 | 아무 것도 안 함 | — |

- [ ] **Step 1: Write failing tests for auto-capture policy**

`tests/test_mcp_dispatch_capture.py` 에 클래스 추가:

```python
from unittest.mock import patch as mock_patch
from vibelign.mcp import mcp_dispatch


class DispatchAutoCaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()

    def tearDown(self):
        self.tmp.cleanup()

    def _wm(self):
        return load_work_memory(MetaPaths(self.root).work_memory_path)

    def test_guard_check_logs_verification(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"guard_check": lambda r, a, t: [{"type": "text", "text": "guard: ok"}]}):
            _run(call_tool_dispatch("guard_check", {}, root=self.root, text_content=_tc))
        self.assertTrue(any("guard" in v for v in self._wm()["verification"]))

    def test_checkpoint_create_logs_recent_event_not_decision(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"checkpoint_create": lambda r, a, t: [{"type": "text", "text": "saved"}]}):
            _run(call_tool_dispatch("checkpoint_create",
                {"message": "v2.0.35 작업 전 안전 저장"},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])  # 핵심: decisions 안 건드림
        self.assertTrue(
            any(e.get("kind") == "checkpoint" for e in wm["recent_events"]),
            f"checkpoint event missing: {wm['recent_events']}",
        )
        self.assertEqual(wm["relevant_files"], [])

    def test_patch_apply_with_strict_patch_logs_relevant_file_only(self):
        strict = {
            "target": {
                "file": "vibelign/core/work_memory.py",
                "anchor": "WORK_MEMORY_ADD_DECISION",
            },
            "operation": "replace",
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "applied"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])
        self.assertTrue(
            any(rf["path"] == "vibelign/core/work_memory.py"
                for rf in wm["relevant_files"]),
            f"relevant_files missing: {wm['relevant_files']}",
        )

    def test_patch_apply_dry_run_skipped(self):
        strict = {
            "target": {"file": "vibelign/core/work_memory.py"},
            "dry_run": True,
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "would apply"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict},
                root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["relevant_files"], [])

    def test_patch_apply_top_level_dry_run_skipped(self):
        strict = {
            "target": {"file": "vibelign/core/work_memory.py"},
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "would apply"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict, "dry_run": True},
                root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["relevant_files"], [])

    def test_other_tools_have_no_side_effect(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"random_tool": lambda r, a, t: [{"type": "text", "text": "x"}]}):
            _run(call_tool_dispatch("random_tool", {},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])
        self.assertEqual(wm["verification"], [])
        self.assertEqual(wm["recent_events"], [])
        self.assertEqual(wm["relevant_files"], [])

    def test_capture_failure_does_not_break_tool_result(self):
        """work_memory write 실패해도 도구 결과는 정상 반환."""
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"guard_check": lambda r, a, t: [{"type": "text", "text": "g"}]}):
            with mock_patch("vibelign.mcp.mcp_dispatch.add_verification",
                side_effect=Exception("disk full")):
                result = _run(call_tool_dispatch("guard_check", {},
                    root=self.root, text_content=_tc))
        self.assertEqual(result[0]["text"], "g")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run --with pytest pytest tests/test_mcp_dispatch_capture.py::DispatchAutoCaptureTest -v`
Expected: 7 fails (all auto-capture missing)

- [ ] **Step 3: Implement post-dispatch hook**

Replace `mcp_dispatch.py` body:

```python
# === ANCHOR: MCP_DISPATCH_START ===
from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from vibelign.mcp.mcp_handler_registry import DISPATCH_TABLE
from vibelign.mcp.mcp_handler_registry import TextContentFactory
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import (
    add_relevant_file,
    add_verification,
    record_checkpoint,
)


# === ANCHOR: MCP_DISPATCH_DISPATCHCALLABLE_START ===
class DispatchCallable(Protocol):
    # === ANCHOR: MCP_DISPATCH___CALL___START ===
    def __call__(
        self, root: Path, arguments: dict[str, object], text_content: TextContentFactory
# === ANCHOR: MCP_DISPATCH_DISPATCHCALLABLE_END ===
    # === ANCHOR: MCP_DISPATCH___CALL___END ===
    ) -> list[object]: ...


def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]


# === ANCHOR: MCP_DISPATCH_CALL_TOOL_DISPATCH_START ===
async def call_tool_dispatch(
    name: str,
    arguments: dict[str, object],
    *,
    root: Path,
    text_content: TextContentFactory,
# === ANCHOR: MCP_DISPATCH_CALL_TOOL_DISPATCH_END ===
) -> list[object]:
    handler = cast(DispatchCallable | None, DISPATCH_TABLE.get(name))
    if handler is None:
        return _text(text_content, f"알 수 없는 도구: {name}")
    result = handler(root, arguments, text_content)
    try:
        _auto_capture_narrative(name, arguments, result, root)
    except Exception:
        pass  # narrative 캡처 실패는 도구 결과를 망치지 않는다.
    return result


def _auto_capture_narrative(
    name: str,
    arguments: dict[str, object],
    result: list[object],
    root: Path,
) -> None:
    """주요 도구 호출 후 work_memory 자동 누적 (decisions[] 는 절대 안 건드림)."""
    wm = MetaPaths(root).work_memory_path

    if name == "guard_check":
        text = _flatten_result_text(result)
        if text:
            add_verification(wm, f"guard_check -> {text[:200]}")

    elif name == "checkpoint_create":
        msg = arguments.get("message")
        if isinstance(msg, str) and msg.strip():
            # checkpoint 는 사실(state save) 이므로 recent_events 에만.
            record_checkpoint(wm, msg)

    elif name == "patch_apply":
        strict = arguments.get("strict_patch")
        if not isinstance(strict, dict):
            return
        if arguments.get("dry_run") is True or strict.get("dry_run") is True:
            return
        target = strict.get("target")
        if isinstance(target, dict):
            file_path = target.get("file")
            if isinstance(file_path, str) and file_path:
                anchor = target.get("anchor", "")
                why = (
                    f"patch_apply target (anchor: {anchor})"
                    if isinstance(anchor, str) and anchor
                    else "patch_apply target"
                )
                add_relevant_file(wm, file_path, why)


def _flatten_result_text(result: list[object]) -> str:
    parts: list[str] = []
    for item in result:
        if isinstance(item, dict):
            text = item.get("text")
        else:
            text = getattr(item, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return " | ".join(parts)
# === ANCHOR: MCP_DISPATCH_END ===
```

- [ ] **Step 4: Run tests**

Run: `uv run --with pytest pytest tests/test_mcp_dispatch_capture.py -v`
Expected: 4 (Task 3) + 7 (Task 4) = 11 passed

- [ ] **Step 5: Commit**

```bash
git add vibelign/mcp/mcp_dispatch.py tests/test_mcp_dispatch_capture.py
git commit -m "$(cat <<'EOF'
feat(mcp): dispatch 후처리 훅 — guard/checkpoint/patch_apply 자동 캡처 (decisions 안전)

guard_check 결과 → verification[], checkpoint_create message → record_checkpoint
(kind=checkpoint), patch_apply 의 strict_patch.target.file → relevant_files.
decisions[] 는 자동 경로에서 절대 안 건드림 (active_intent 의미 보존).
patch_apply(dry_run) 은 top-level/strict_patch 내부 모두 skip. capture 실패는 도구 결과를 망치지 않음.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `vib _internal_record_commit` CLI subcommand (stdin 입력)

**Files:**
- Create: `vibelign/commands/internal_record_commit_cmd.py`
- Modify: `vibelign/cli/cli_command_groups.py`
- Test: `tests/test_handoff_auto_capture.py` (신규, 같은 프로세스에서 모듈 호출로 검증)

**왜:** post-commit 훅이 commit 메시지를 multi-line / 한글 / 따옴표 안전하게 전달하도록 stdin 기반. argv 인자 회피.

- [ ] **Step 1: Write failing test**

`tests/test_handoff_auto_capture.py`:

```python
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import load_work_memory


class InternalRecordCommitCLITest(unittest.TestCase):
    def _run_cli(self, args, stdin_text):
        """argparse 진입점 직접 호출 (subprocess 없이)."""
        from vibelign.cli.vib_cli import main as vib_main
        original_cwd = Path.cwd()
        try:
            with patch("sys.stdin", io.StringIO(stdin_text)):
                rc = vib_main(args)
        finally:
            pass
        return rc

    def test_records_commit_from_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            MetaPaths(root).ensure_vibelign_dirs()
            with patch("os.getcwd", return_value=str(root)):
                # subcommand 만 인자, message 는 stdin 으로
                from vibelign.commands.internal_record_commit_cmd import (
                    run_internal_record_commit,
                )
                from argparse import Namespace
                with patch("sys.stdin", io.StringIO("feat: hello\n\nbody\n한글 ✨")):
                    run_internal_record_commit(Namespace(sha="abc1234"), root=root)

            state = load_work_memory(MetaPaths(root).work_memory_path)
            event = state["recent_events"][-1]
            self.assertEqual(event["kind"], "commit")
            self.assertIn("feat: hello", event["message"])
            self.assertEqual(state["decisions"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_handoff_auto_capture.py::InternalRecordCommitCLITest -v`
Expected: ImportError

- [ ] **Step 3: Add internal command runner**

Create `vibelign/commands/internal_record_commit_cmd.py`:

```python
from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import record_commit


def run_internal_record_commit(args: Namespace, root: Path | None = None) -> None:
    """post-commit hook internal entrypoint. Reads commit message from stdin."""
    project_root = root if root is not None else Path.cwd()
    message = sys.stdin.read()
    record_commit(MetaPaths(project_root).work_memory_path, str(args.sha), message)
```

- [ ] **Step 4: Add CLI subcommand wiring**

`vibelign/cli/cli_command_groups.py` (export_cmd 등록부 근처):

```python
import argparse  # already imported, verify

internal_commit_parser = subparsers.add_parser(
    "_internal_record_commit",
    help=argparse.SUPPRESS,  # 사용자에게 숨김
    description="post-commit 훅이 호출. stdin 으로 commit 메시지 받음."
)
internal_commit_parser.add_argument("sha", help="git commit SHA")
internal_commit_parser.set_defaults(
    func=lazy_command(
        "vibelign.commands.internal_record_commit_cmd",
        "run_internal_record_commit",
    )
)
```

테스트는 `vibelign.commands.internal_record_commit_cmd.run_internal_record_commit` 를 직접 호출한다. `cli_command_groups.py` 는 argparse 등록만 담당해 대형 CLI 파일에 로직을 추가하지 않는다.

- [ ] **Step 5: Run test**

Run: `uv run --with pytest pytest tests/test_handoff_auto_capture.py::InternalRecordCommitCLITest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add vibelign/commands/internal_record_commit_cmd.py vibelign/cli/cli_command_groups.py tests/test_handoff_auto_capture.py
git commit -m "$(cat <<'EOF'
feat(cli): _internal_record_commit subcommand (stdin 입력, multiline 안전)

post-commit 훅이 호출할 internal 진입점. argparse.SUPPRESS 로 사용자에게 숨김.
commit message 는 stdin 으로 받아 multi-line / 한글 / 이모지 / 따옴표 안전.
record_commit 으로 recent_events 에만 누적 (decisions 안 건드림).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `install_post_commit_record_hook` (PREPEND, get_hooks_dir, fallback chain)

**Files:**
- Modify: `vibelign/core/git_hooks.py`
- Test: `tests/test_git_hooks_post_commit.py` (신규)

**원본 review 반영:**
- `get_hooks_dir(root)` 사용 (worktree/submodule 안전)
- `HookInstallResult(status=str, path=Path|None)` 일관
- Vibelign 블록을 *PREPEND* 해서 기존 훅 의 `exit` 와 무관하게 항상 실행
- 명령 fallback: `vib` → `vibelign` → 현재 설치된 Python module fallback (`python3 -m vibelign.cli.vib_cli`) (기존 pre-commit 패턴 모방)

- [ ] **Step 1: Write failing tests**

`tests/test_git_hooks_post_commit.py`:

```python
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from vibelign.core.git_hooks import (
    install_post_commit_record_hook,
    uninstall_post_commit_record_hook,
)


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)


class PostCommitHookTest(unittest.TestCase):
    def test_installs_hook_with_marker_and_exec_bit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            result = install_post_commit_record_hook(root)
            self.assertEqual(result.status, "installed")
            hook = root / ".git" / "hooks" / "post-commit"
            self.assertTrue(hook.exists())
            self.assertTrue(os.access(hook, os.X_OK))
            content = hook.read_text()
            self.assertIn("# vibelign: post-commit-record v1", content)
            self.assertIn("# vibelign: post-commit-record-end", content)

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            r1 = install_post_commit_record_hook(root)
            r2 = install_post_commit_record_hook(root)
            self.assertEqual(r1.status, "installed")
            self.assertEqual(r2.status, "already-installed")

    def test_returns_not_git_when_no_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = install_post_commit_record_hook(Path(tmp))
            self.assertEqual(r.status, "not-git")

    def test_prepends_to_existing_hook_so_runs_before_existing_exit(self):
        """기존 hook 끝에 exit 가 있어도 vibelign 블록이 먼저 실행되어야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook_path = root / ".git" / "hooks" / "post-commit"
            hook_path.write_text("#!/bin/sh\necho 'user hook'\nexit 0\n")
            hook_path.chmod(0o755)

            install_post_commit_record_hook(root)
            content = hook_path.read_text()
            # 셔뱅은 위 1줄, 그 직후 vibelign 블록, 그 다음 기존 사용자 hook
            lines = content.splitlines()
            shebang_idx = next(i for i, l in enumerate(lines) if l.startswith("#!"))
            vib_start_idx = next(i for i, l in enumerate(lines) if "post-commit-record v1" in l)
            user_idx = next(i for i, l in enumerate(lines) if "user hook" in l)
            self.assertLess(shebang_idx, vib_start_idx)
            self.assertLess(vib_start_idx, user_idx)

    def test_uninstall_preserves_existing_user_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            hook = root / ".git" / "hooks" / "post-commit"
            hook.write_text("#!/bin/sh\necho 'user hook'\nexit 0\n")
            hook.chmod(0o755)

            install_post_commit_record_hook(root)
            uninstall_post_commit_record_hook(root)
            content = hook.read_text()
            self.assertIn("user hook", content)
            self.assertNotIn("post-commit-record v1", content)

    def test_uninstall_removes_file_when_only_vibelign_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            install_post_commit_record_hook(root)
            uninstall_post_commit_record_hook(root)
            self.assertFalse((root / ".git" / "hooks" / "post-commit").exists())

    def test_hook_contains_python_module_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git_init(root)
            install_post_commit_record_hook(root)
            content = (root / ".git" / "hooks" / "post-commit").read_text()
            self.assertIn("python3 -m vibelign.cli.vib_cli _internal_record_commit", content)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run --with pytest pytest tests/test_git_hooks_post_commit.py -v`
Expected: ImportError

- [ ] **Step 3: Implement install/uninstall**

`vibelign/core/git_hooks.py` 끝에 추가:

```python
# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_START ===
_POST_COMMIT_MARKER = "# vibelign: post-commit-record v1"
_POST_COMMIT_END = "# vibelign: post-commit-record-end"

# vib → vibelign → python -m fallback. stdin 으로 commit 메시지 전달.
_POST_COMMIT_BLOCK_TEMPLATE = """\
{marker}
sha=$(git rev-parse HEAD 2>/dev/null)
msg=$(git log -1 --pretty=%B 2>/dev/null)
if [ -n "$sha" ] && [ -n "$msg" ]; then
    if command -v vib >/dev/null 2>&1; then
        printf "%s" "$msg" | vib _internal_record_commit "$sha" >/dev/null 2>&1 || true
    elif command -v vibelign >/dev/null 2>&1; then
        printf "%s" "$msg" | vibelign _internal_record_commit "$sha" >/dev/null 2>&1 || true
    elif command -v python3 >/dev/null 2>&1; then
        printf "%s" "$msg" | python3 -m vibelign.cli.vib_cli _internal_record_commit "$sha" >/dev/null 2>&1 || true
    fi
fi
{end}
"""


def _build_post_commit_block() -> str:
    return _POST_COMMIT_BLOCK_TEMPLATE.format(
        marker=_POST_COMMIT_MARKER, end=_POST_COMMIT_END
    )


def install_post_commit_record_hook(root: Path) -> HookInstallResult:
    """Vibelign 블록을 PREPEND 해서 기존 hook 의 exit 와 무관하게 실행되게 한다."""
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    block = _build_post_commit_block()

    if hook_path.exists():
        existing = hook_path.read_text(encoding="utf-8")
        if _POST_COMMIT_MARKER in existing:
            return HookInstallResult(status="already-installed", path=hook_path)
        # shebang 보존 + 그 다음에 vibelign 블록 + 그 다음에 기존 본문
        if existing.startswith("#!"):
            shebang, _, rest = existing.partition("\n")
            new_content = f"{shebang}\n\n{block}\n{rest}"
        else:
            new_content = f"#!/bin/sh\n\n{block}\n{existing}"
    else:
        new_content = f"#!/bin/sh\n\n{block}\n"

    hook_path.write_text(new_content, encoding="utf-8")
    hook_path.chmod(0o755)
    return HookInstallResult(status="installed", path=hook_path)


def uninstall_post_commit_record_hook(root: Path) -> HookInstallResult:
    hooks_dir = get_hooks_dir(root)
    if hooks_dir is None:
        return HookInstallResult(status="not-git", path=None)
    hook_path = hooks_dir / "post-commit"
    if not hook_path.exists():
        return HookInstallResult(status="missing", path=hook_path)

    content = hook_path.read_text(encoding="utf-8")
    if _POST_COMMIT_MARKER not in content:
        return HookInstallResult(status="foreign-hook", path=hook_path)

    start = content.index(_POST_COMMIT_MARKER)
    end_idx = content.index(_POST_COMMIT_END, start) + len(_POST_COMMIT_END)
    # 양 옆 빈 줄 정리
    while start > 0 and content[start - 1] == "\n":
        start -= 1
    while end_idx < len(content) and content[end_idx] == "\n":
        end_idx += 1
    new_content = content[:start] + content[end_idx:]
    new_content = new_content.rstrip()

    if new_content.strip() in ("", "#!/bin/sh"):
        hook_path.unlink()
        return HookInstallResult(status="removed", path=hook_path)

    hook_path.write_text(new_content + "\n", encoding="utf-8")
    return HookInstallResult(status="removed", path=hook_path)
# === ANCHOR: GIT_HOOKS_POST_COMMIT_RECORD_END ===
```

- [ ] **Step 4: Run tests**

Run: `uv run --with pytest pytest tests/test_git_hooks_post_commit.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/git_hooks.py tests/test_git_hooks_post_commit.py
git commit -m "$(cat <<'EOF'
feat(git_hooks): post-commit 훅 — commit 사실을 work_memory.recent_events 로 운반

vibelign 블록을 PREPEND 해서 기존 hook 의 exit 와 무관하게 실행. get_hooks_dir
사용해 worktree/submodule 안전. 명령 fallback chain (vib → vibelign → python module).
stdin 으로 commit msg 전달해 multi-line / 한글 / 이모지 / 따옴표 안전.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `vib start` 가 새 훅 자동 설치

**Files:**
- Modify: `vibelign/commands/vib_start_cmd.py`
- Test: `tests/test_vib_start_hooks.py` (기존 파일에 케이스 추가)

- [ ] **Step 1: Write failing test**

`tests/test_vib_start_hooks.py` 에 추가:

```python
def test_vib_start_installs_post_commit_record_hook(self):
    import os
    import subprocess
    from argparse import Namespace
    from unittest.mock import patch
    from vibelign.commands.vib_start_cmd import run_vib_start

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        previous = Path.cwd()
        try:
            os.chdir(root)
            with patch("vibelign.commands.vib_start_cmd._selected_start_tools", return_value=[]):
                run_vib_start(Namespace(all_tools=False, tools=None, force=False, quickstart=False))
        finally:
            os.chdir(previous)

        hook = root / ".git" / "hooks" / "post-commit"
        self.assertTrue(hook.exists())
        self.assertIn("post-commit-record v1", hook.read_text())
```

(`run_vib_start` 는 현재 작업 디렉터리 기준으로 root 를 해석하므로 테스트는 `os.chdir(root)` 패턴을 따른다.)

- [ ] **Step 2: Run test to verify failure**

Run: `uv run --with pytest pytest tests/test_vib_start_hooks.py::test_vib_start_installs_post_commit_record_hook -v`
Expected: FAIL (hook 미생성)

- [ ] **Step 3: Wire into vib_start_cmd.py**

import 추가:
```python
from vibelign.core.git_hooks import (
    install_pre_commit_secret_hook,
    install_post_commit_record_hook,
)
```

기존 `secret_hook_result = install_pre_commit_secret_hook(root) if git_active else None` 직후에:
```python
record_hook_result = (
    install_post_commit_record_hook(root) if git_active else None
)
if record_hook_result and record_hook_result.status == "installed":
    clack_success("git post-commit 훅 설치됨 (commit 메시지가 핸드오프로 자동 누적)")
```

- [ ] **Step 4: Run test**

Run: `uv run --with pytest pytest tests/test_vib_start_hooks.py -v`
Expected: 모든 케이스 PASS

- [ ] **Step 5: Commit**

```bash
git add vibelign/commands/vib_start_cmd.py tests/test_vib_start_hooks.py
git commit -m "$(cat <<'EOF'
feat(start): vib start 가 post-commit-record 훅 자동 설치

기존 pre-commit secret 훅과 동일 패턴. git 저장소면 두 훅 모두 자동 설치.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: AGENTS.md / CLAUDE.md / OPENCODE.md 업데이트

**Files:**
- Modify: `AGENTS.md` (root)
- Modify: `CLAUDE.md` (root)
- Modify: `OPENCODE.md` (root)

핵심 강조점: **decisions[] 에 들어가는 건 *명시적* `transfer_set_decision` 호출뿐**. AI 가 결정을 의식적으로 적어야 active_intent 가 의미 있어짐. 자동 캡처는 보강.

- [ ] **Step 1: 추가할 텍스트 (3 파일 동일)**

```markdown
## Handoff Narrative Discipline

work_memory.json 의 의미 칸은 *3 가지 경로* 로 채워집니다:

| 필드 | 자동 캡처 (보강) | 명시 호출 (핵심) |
|---|---|---|
| `decisions[]` | (없음 — 자동 캡처 안 함) | `transfer_set_decision(text)` |
| `verification[]` | guard_check 결과 | `transfer_set_verification(text)` |
| `relevant_files[]` | patch_apply target | `transfer_set_relevant(path, why)` |
| `recent_events[]` (kind=commit/checkpoint) | git post-commit / checkpoint_create | (호출 없음) |

`decisions[-1]` 이 PROJECT_CONTEXT.md 의 **active_intent** 가 됩니다. 그러므로
`transfer_set_decision` 은 **세션의 진짜 의사결정** 일 때만 호출하세요:

- 두 옵션 사이에서 하나를 선택했을 때 (이유 포함, 1줄)
- 의도가 바뀌었을 때 ("이제는 X 가 아니라 Y 를 추구")
- 작업의 핵심 목표가 정해졌을 때

**호출하지 말 것**:
- 단순 진행 보고 ("이제 Task 3 시작")
- commit 정렬 / 버전 bump 같은 메커니컬 작업
- 검증 결과 (그건 `transfer_set_verification`)
```

- [ ] **Step 2: 3 파일에 위 텍스트 추가, commit**

```bash
git add AGENTS.md CLAUDE.md OPENCODE.md
git commit -m "$(cat <<'EOF'
docs(handoff): narrative discipline — decisions 는 명시 호출만

decisions[-1] → active_intent 매핑이 의미 있도록 *진짜 의사결정* 만 transfer_
set_decision 호출하라는 규칙. commit / checkpoint / verification 은 별도 경로.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: End-to-end 통합 테스트 (commit + MCP + transfer)

**Files:**
- Modify: `tests/test_handoff_auto_capture.py` (Task 5 파일에 클래스 추가)

핵심 시나리오:
1. git commit (merge / amend 포함) → recent_events 만 채워짐, decisions 그대로
2. transfer_set_decision MCP 호출 → decisions[-1] = 그 값
3. build_transfer_summary → active_intent = 위 값 (commit 메시지 아님!)

- [ ] **Step 1: Write tests**

`tests/test_handoff_auto_capture.py` 에 추가:

```python
class EndToEndTest(unittest.TestCase):
    def _git_repo(self, root: Path) -> None:
        import subprocess
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@v.local"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)

    def test_commit_does_not_pollute_active_intent(self):
        import subprocess
        from vibelign.core.git_hooks import install_post_commit_record_hook
        from vibelign.core.work_memory import build_transfer_summary

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git_repo(root)
            MetaPaths(root).ensure_vibelign_dirs()
            install_post_commit_record_hook(root)

            (root / "README.md").write_text("hi\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore(gui): Tauri 앱 번들을 2.0.35로 정렬"],
                cwd=root, check=True, capture_output=True,
            )

            wm = MetaPaths(root).work_memory_path
            state = load_work_memory(wm)
            self.assertEqual(state["decisions"], [],
                "commit 은 decisions 에 들어가면 안 된다 — active_intent 오염")
            self.assertTrue(
                any(e.get("kind") == "commit" for e in state["recent_events"]),
                "commit 은 recent_events 에 있어야 한다",
            )

            # Explicit decision 기록
            from vibelign.core.work_memory import add_decision
            add_decision(wm, "1-B 옵션 채택: 통일성 우선")

            summary = build_transfer_summary(wm)
            self.assertEqual(summary["active_intent"], "1-B 옵션 채택: 통일성 우선",
                "active_intent 는 명시 decision 이어야 함, commit msg 가 아님")

    def test_multiline_korean_commit_message(self):
        import subprocess
        from vibelign.core.git_hooks import install_post_commit_record_hook

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._git_repo(root)
            MetaPaths(root).ensure_vibelign_dirs()
            install_post_commit_record_hook(root)

            (root / "f.txt").write_text("x")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            msg = "feat: 한글 ✨\n\n본문 line 1\n본문 line 2"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=root, check=True, capture_output=True,
            )

            state = load_work_memory(MetaPaths(root).work_memory_path)
            commit_event = next(
                e for e in state["recent_events"] if e.get("kind") == "commit"
            )
            self.assertIn("한글 ✨", commit_event["message"])
```

(merge/revert/amend 케이스는 너무 무거워 별도 PR 로 분리. 위 두 케이스가 핵심 의미 보존 검증.)

- [ ] **Step 2: Run tests**

Run: `uv run --with pytest pytest tests/test_handoff_auto_capture.py::EndToEndTest -v`
Expected: 2 passed (이전 Task 모두 끝났다면)

- [ ] **Step 3: Commit**

```bash
git add tests/test_handoff_auto_capture.py
git commit -m "$(cat <<'EOF'
test(handoff): E2E — commit 은 active_intent 오염 안 함, multiline 한글 안전

git commit → recent_events 만 채워지고 decisions 은 비어 있음 검증.
build_transfer_summary 의 active_intent 는 명시 add_decision 이 우선.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: v2.0.35 버전 정렬 (4 commits + tag + push)

**Files:**
- `pyproject.toml`, `vibelign-gui/package.json`, `vibelign-gui/package-lock.json` (×2),
  `vibelign-gui/src-tauri/{tauri.conf.json, Cargo.toml, Cargo.lock}`

(v2.0.34 와 동일 패턴. 본 plan 의 마지막 단계.)

- [ ] **Step 1: 4 파일 group 별 bump** (`2.0.34 → 2.0.35`)
- [ ] **Step 2: 3 chore commits** (vibelign python / GUI npm / GUI Tauri)
- [ ] **Step 3: tag + push**

```bash
git tag v2.0.35
git push origin feat/vibelign-2.0-gui
git push origin v2.0.35
```

- [ ] **Step 4: CI 확인** — `gh run list --limit 5` 로 publish.yml + gui.yml + python.yml 시동 확인

---

## Self-Review Checklist (실행 전)

**1. Spec coverage**:
- ✅ active_intent 오염 방지 (commit → recent_events, NOT decisions) — Task 2, 6, 9
- ✅ patch_apply 인자 mismatch 수정 (strict_patch 파싱 + top-level dry_run 처리) — Task 4
- ✅ git_hooks 패턴 일치 (HookInstallResult.status, get_hooks_dir, fallback chain) — Task 6
- ✅ post-commit PREPEND (exit 영향 안 받음) — Task 6
- ✅ E2E 테스트가 vib 바이너리 의존 안 함 (모듈 직접 호출 / cli.vib_cli main) — Task 5, 9
- ✅ snapshot test 갱신 — Task 3 Step 6
- ✅ patch_apply(dry_run) skip — top-level `dry_run` 과 `strict_patch.dry_run` 둘 다 Task 4
- ✅ checkpoint_create 는 `record_checkpoint` 로 recent_events 에만 기록, decisions/relevant_files 오염 없음 — Task 2.5, 4
- ✅ multi-line / 한글 / 이모지 commit msg 안전 (stdin 전달) — Task 5, 6, 9
- ✅ transfer_set_relevant edge case (절대경로/.omc/parent traversal) — Task 1 단위 테스트
- ✅ work_memory write 실패 시 도구 결과 안 망침 — Task 4 test_capture_failure...

**2. Placeholder scan**: 통과. 모든 Step 에 실제 코드/명령/예상 결과 포함.

**3. Type consistency**:
- `add_decision/add_verification/add_relevant_file/record_commit/record_checkpoint` — 첫 인자 모두 `path: Path` (work_memory.json 경로)
- `HookInstallResult(status: str, path: Path | None)` — 기존 dataclass 그대로 사용
- MCP handler 시그니처 `(root, arguments, text_content)` — 기존 패턴
- `record_event(path, *, kind, rel_path, message, action="", relevant_reason="")` — 기존 keyword-only 시그니처 유지; synthetic commit/checkpoint 는 전용 API 사용

---

## Out of Scope (다음 릴리스 후보)

- merge/revert/amend commit 의 special handling (단순 commit 으로만 처리, 이번 릴리스)
- AI conversation transcript 직접 스크래핑
- vib transfer 가 Anthropic API 로 자동 narrative 합성
- decisions[] 길이 제한 시 LLM 요약
- 사용자 직접 호출 CLI (`vib intent / decision`) — 사용자 명시 거부

## Backward Compat 노트

- 기존 사용자 `vib start` 한 번 더 → post-commit-record 훅 자동 설치
- 기존 pre-commit secret 훅 / cursor / claude 등록 등 그대로
- work_memory.json 스키마 변경 0
- `vib transfer --handoff` 결과는 데이터 누적된 만큼 풍부해짐 (점진 향상)
- 기존에 사용자 본인이 `.git/hooks/post-commit` 에 다른 훅을 넣어둔 경우, vibelign 블록은 PREPEND 되어 기존 훅 *전에* 실행됨 → 기존 훅 동작은 그대로 유지
