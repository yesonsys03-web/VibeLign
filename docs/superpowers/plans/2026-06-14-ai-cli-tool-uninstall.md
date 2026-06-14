# AI CLI 도구 언인스톨 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GUI에서 OpenCode / Codex / Antigravity CLI를 제거(언인스톨)할 수 있게 한다 — 클로드코드 언인스톨과 동일하게 바이너리만 제거.

**Architecture:** 기존 설치 흐름(`tool_install.rs` 레지스트리 + `install_tool` 커맨드 + `ToolInstallPanel`)을 미러링한다. `ToolInstaller` 구조체에 OS별 제거 명령/안내 필드를 추가하고, `uninstall_tool` Tauri 커맨드를 만든다. agy mac은 명령이 없어 resolve된 단일 바이너리를 `remove_file`로 안전 삭제한다. 명령·삭제가 불가한 도구/OS(codex-win, agy-win)는 안내 폴백.

**Tech Stack:** Rust (Tauri 커맨드), TypeScript/React (Vitest), 기존 `find_executable` PATH resolver 재사용.

---

## File Structure

- `vibelign-gui/src-tauri/src/commands/tool_install.rs` — `ToolInstaller` 확장, `uninstall_command` 헬퍼, `uninstall_tool` 커맨드, Rust 테스트 (modify)
- `vibelign-gui/src-tauri/src/lib.rs:190-191` — `uninstall_tool` 핸들러 등록 (modify)
- `vibelign-gui/src/lib/tools/installerRegistry.ts` — `uninstallTool` 래퍼 + `ToolUninstallResult` 타입 (modify)
- `vibelign-gui/src/components/tools/ToolInstallPanel.tsx` — 제거 UI(설치됨 상태일 때 버튼+확인+안내 폴백) (modify)
- `vibelign-gui/src/components/tools/__tests__/ToolInstallPanel.test.tsx` — 프론트 테스트 (create)

---

## Task 1: Rust — `ToolInstaller` 제거 필드 + `uninstall_command` 헬퍼

**Files:**
- Modify: `vibelign-gui/src-tauri/src/commands/tool_install.rs`
- Test: 동일 파일 `#[cfg(test)] mod tests`

- [ ] **Step 1: 제거 명령 헬퍼의 실패 테스트 작성**

`tool_install.rs`의 `mod tests` 안에 추가:

```rust
    #[test]
    fn uninstall_command_per_os() {
        // opencode: mac=opencode 내장, win=npm
        let oc = tool_installer("opencode").unwrap();
        let mac = uninstall_command(oc, "macos").expect("opencode mac uninstall");
        assert_eq!(mac.0, "opencode");
        assert!(mac.1.iter().any(|a| a == "uninstall"));
        let win = uninstall_command(oc, "windows").expect("opencode win uninstall");
        assert_eq!(win.0, "npm");
    }

    #[test]
    fn codex_win_and_agy_have_no_command_fallback_to_manual() {
        // codex: mac=npm 명령 있음, win=명령 없음(안내)
        let cx = tool_installer("codex").unwrap();
        assert!(uninstall_command(cx, "macos").is_some());
        assert!(uninstall_command(cx, "windows").is_none());
        // agy: 어느 OS도 명령 없음(mac은 remove_binary, win은 안내)
        let agy = tool_installer("agy").unwrap();
        assert!(uninstall_command(agy, "macos").is_none());
        assert!(uninstall_command(agy, "windows").is_none());
    }

    #[test]
    fn agy_uses_remove_binary_others_do_not() {
        assert!(tool_installer("agy").unwrap().uninstall_remove_binary);
        assert!(!tool_installer("opencode").unwrap().uninstall_remove_binary);
        assert!(!tool_installer("codex").unwrap().uninstall_remove_binary);
    }

    #[test]
    fn manual_fallback_tools_have_hint_and_url() {
        for id in ["codex", "agy"] {
            let t = tool_installer(id).unwrap();
            assert!(!t.uninstall_hint.is_empty(), "{id} hint");
            assert!(!t.uninstall_url.is_empty(), "{id} url");
        }
    }
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd vibelign-gui/src-tauri && cargo test --lib tool_install 2>&1 | tail -20`
Expected: 컴파일 실패 — `uninstall_command` 함수 없음, `uninstall_remove_binary`/`uninstall_hint`/`uninstall_url` 필드 없음.

- [ ] **Step 3: 구조체에 제거 필드 추가**

`ToolInstaller` 구조체(`tool_install.rs:11-26`)의 `recommended_for_beginner` 필드 다음에 추가:

```rust
    pub recommended_for_beginner: bool,
    /// OS별 제거 명령. None = 그 OS는 안내 폴백.
    pub mac_uninstall: Option<(&'static str, &'static [&'static str])>,
    pub win_uninstall: Option<(&'static str, &'static [&'static str])>,
    /// true 면 mac 에서 probe_binary 경로를 resolve 후 remove_file (agy).
    pub uninstall_remove_binary: bool,
    /// 안내 폴백 시 보여줄 수동 제거 단계.
    pub uninstall_hint: &'static str,
    /// 안내 폴백 시 열 공식 문서 URL.
    pub uninstall_url: &'static str,
```

- [ ] **Step 4: 레지스트리 3개 도구에 값 채우기**

`OPENCODE` 상수(`tool_install.rs:28-35`)의 `recommended_for_beginner: true,` 다음에 추가:

```rust
    recommended_for_beginner: true,
    mac_uninstall: Some(("opencode", &["uninstall", "--keep-config", "--keep-data", "--force"])),
    win_uninstall: Some(("npm", &["uninstall", "-g", "opencode-ai"])),
    uninstall_remove_binary: false,
    uninstall_hint: "제거가 안 되면 `npm uninstall -g opencode-ai` 또는 설치 시 사용한 방법으로 지워주세요.",
    uninstall_url: "https://opencode.ai/download",
```

`CODEX` 상수(`tool_install.rs:36-43`)의 `recommended_for_beginner: false,` 다음에 추가:

```rust
    recommended_for_beginner: false,
    mac_uninstall: Some(("npm", &["uninstall", "-g", "@openai/codex"])),
    win_uninstall: None,
    uninstall_remove_binary: false,
    uninstall_hint: "Windows: `npm uninstall -g @openai/codex` 를 실행하거나, npm 으로 설치하지 않았다면 설치 페이지의 제거 안내를 따라주세요.",
    uninstall_url: "https://www.npmjs.com/package/@openai/codex",
```

`AGY` 상수(`tool_install.rs:44-51`)의 `recommended_for_beginner: false,` 다음에 추가:

```rust
    recommended_for_beginner: false,
    mac_uninstall: None,
    win_uninstall: None,
    uninstall_remove_binary: true,
    uninstall_hint: "Windows: 설정 > 앱 > 설치된 앱에서 'Antigravity CLI' 를 제거하세요. ANTIGRAVITY_API_KEY 환경변수가 있으면 함께 지워주세요.",
    uninstall_url: "https://antigravity.google/docs/cli-install",
```

- [ ] **Step 5: `uninstall_command` 헬퍼 추가**

`install_command` 함수(`tool_install.rs:63-69`) 바로 다음에 추가:

```rust
/// os: "macos" | "windows". 그 OS에 제거 명령이 없으면 None(→ 안내 폴백 또는 remove_binary).
pub(crate) fn uninstall_command(t: &ToolInstaller, os: &str) -> Option<(String, Vec<String>)> {
    let entry = match os {
        "macos" => t.mac_uninstall,
        "windows" => t.win_uninstall,
        _ => None,
    }?;
    Some((entry.0.to_string(), entry.1.iter().map(|s| s.to_string()).collect()))
}
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd vibelign-gui/src-tauri && cargo test --lib tool_install 2>&1 | tail -20`
Expected: PASS (신규 4개 포함 기존 테스트 전부 통과).

- [ ] **Step 7: 커밋**

```bash
git add vibelign-gui/src-tauri/src/commands/tool_install.rs
git commit -m "feat(tool-uninstall): ToolInstaller 제거 필드 + uninstall_command 헬퍼"
```

---

## Task 2: Rust — `uninstall_tool` 커맨드 + 핸들러 등록

**Files:**
- Modify: `vibelign-gui/src-tauri/src/commands/tool_install.rs`
- Modify: `vibelign-gui/src-tauri/src/lib.rs:190-191`

- [ ] **Step 1: `ToolUninstallResult` 결과 타입 추가**

`tool_install.rs`의 `ToolInstallOutput` 구조체(`:93-99`) 다음에 추가:

```rust
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolUninstallResult {
    pub removed: bool,
    pub exit_code: Option<i32>,
    /// removed=false 일 때 보여줄 수동 제거 안내.
    pub manual_hint: String,
    pub manual_url: String,
}
```

- [ ] **Step 2: `uninstall_tool` 커맨드 추가**

`install_tool` 커맨드 끝(`tool_install.rs:177`, `// ANCHOR: TOOL_INSTALL_END` 직전) 다음 줄, 앵커 밖에 추가:

```rust

#[tauri::command]
pub(crate) async fn uninstall_tool(
    app: tauri::AppHandle,
    id: String,
) -> Result<ToolUninstallResult, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    let manual_hint = t.uninstall_hint.to_string();
    let manual_url = t.uninstall_url.to_string();

    // 1) agy mac: 명령이 없어 resolve된 단일 바이너리만 삭제(파일 1개, 비재귀, 셸 미경유).
    if t.uninstall_remove_binary && current_os() == "macos" {
        let probe = t.probe_binary;
        let removed = match find_executable(probe) {
            Some(path) => {
                std::fs::remove_file(&path).map_err(|e| format!("제거 실패: {e}"))?;
                find_executable(probe).is_none()
            }
            None => true, // 이미 없음
        };
        return Ok(ToolUninstallResult { removed, exit_code: None, manual_hint, manual_url });
    }

    // 2) 제거 명령이 있으면 실행. 없으면 안내 폴백.
    let Some((program, args)) = uninstall_command(t, current_os()) else {
        return Ok(ToolUninstallResult { removed: false, exit_code: None, manual_hint, manual_url });
    };

    let probe_binary = t.probe_binary;
    tauri::async_runtime::spawn_blocking(move || {
        use tauri::Emitter;
        let mut cmd = std::process::Command::new(&program);
        cmd.args(&args);
        cmd.env("PATH", augmented_vib_path());
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        hide_console(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| format!("제거 실행 실패: {e}"))?;

        let stderr_handle = child.stderr.take().map(|err| {
            let app2 = app.clone();
            let id2 = id.clone();
            std::thread::spawn(move || {
                for line in BufReader::new(err).lines().map_while(Result::ok) {
                    let _ = app2.emit(
                        "tool-install-output",
                        ToolInstallOutput { id: id2.clone(), stream: "stderr".into(), line },
                    );
                }
            })
        });
        if let Some(out) = child.stdout.take() {
            for line in BufReader::new(out).lines().map_while(Result::ok) {
                let _ = app.emit(
                    "tool-install-output",
                    ToolInstallOutput { id: id.clone(), stream: "stdout".into(), line },
                );
            }
        }
        if let Some(h) = stderr_handle {
            let _ = h.join();
        }
        let status = child.wait().map_err(|e| format!("제거 대기 실패: {e}"))?;
        // 제거 후 재-probe — 정말 사라졌는지 검증(거짓 성공 방지).
        let removed = find_executable(probe_binary).is_none();
        Ok(ToolUninstallResult {
            removed,
            exit_code: status.code(),
            manual_hint,
            manual_url,
        })
    })
    .await
    .map_err(|_| SPAWN_FAIL.to_string())?
}
```

- [ ] **Step 3: 핸들러 등록**

`lib.rs:191`의 `commands::tool_install::tool_install_status,` 다음 줄에 추가:

```rust
            commands::tool_install::tool_install_status,
            commands::tool_install::uninstall_tool,
```

- [ ] **Step 4: 컴파일 + 테스트 확인**

Run: `cd vibelign-gui/src-tauri && cargo test --lib tool_install 2>&1 | tail -15`
Expected: 컴파일 성공, PASS.

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src-tauri/src/commands/tool_install.rs vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(tool-uninstall): uninstall_tool 커맨드 + 핸들러 등록"
```

---

## Task 3: 프론트 래퍼 — `installerRegistry.ts`

**Files:**
- Modify: `vibelign-gui/src/lib/tools/installerRegistry.ts`

- [ ] **Step 1: 타입 + 래퍼 추가**

`installerRegistry.ts` 끝(`toolInstallStatus` 함수 다음)에 추가:

```ts
export interface ToolUninstallResult {
  removed: boolean;
  exitCode: number | null;
  manualHint: string;
  manualUrl: string;
}

export function uninstallTool(id: string): Promise<ToolUninstallResult> {
  return invoke<ToolUninstallResult>("uninstall_tool", { id });
}

/** 제거가 실패했거나 명령이 없으면(removed=false) 수동 안내로. */
export function shouldGuideManualUninstall(r: { removed: boolean }): boolean {
  return !r.removed;
}
```

- [ ] **Step 2: 타입체크 확인**

Run: `cd vibelign-gui && rtk tsc --noEmit 2>&1 | tail -10`
Expected: 에러 없음(0 출력).

- [ ] **Step 3: 커밋**

```bash
git add vibelign-gui/src/lib/tools/installerRegistry.ts
git commit -m "feat(tool-uninstall): installerRegistry uninstallTool 래퍼 + 타입"
```

---

## Task 4: UI — `ToolInstallPanel` 제거 흐름 + 테스트

**Files:**
- Modify: `vibelign-gui/src/components/tools/ToolInstallPanel.tsx`
- Test: `vibelign-gui/src/components/tools/__tests__/ToolInstallPanel.test.tsx` (create)

- [ ] **Step 1: 실패 테스트 작성**

`vibelign-gui/src/components/tools/__tests__/ToolInstallPanel.test.tsx` 생성:

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ToolInstallPanel } from "../ToolInstallPanel";

const mocks = vi.hoisted(() => ({
  toolInstallStatus: vi.fn(),
  uninstallTool: vi.fn(),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn().mockResolvedValue(() => undefined),
}));
vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("../../../lib/tools/installerRegistry", async () => {
  const actual = await vi.importActual<typeof import("../../../lib/tools/installerRegistry")>(
    "../../../lib/tools/installerRegistry",
  );
  return {
    ...actual,
    toolInstallStatus: mocks.toolInstallStatus,
    uninstallTool: mocks.uninstallTool,
    installTool: vi.fn(),
  };
});

describe("ToolInstallPanel uninstall", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    mocks.toolInstallStatus.mockReset();
    mocks.uninstallTool.mockReset();
  });

  test("shows_uninstall_button_when_installed", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    render(<ToolInstallPanel id="opencode" />);
    expect(await screen.findByText(/제거/)).toBeInTheDocument();
  });

  test("confirm_then_calls_uninstallTool", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    mocks.uninstallTool.mockResolvedValue({ removed: true, exitCode: 0, manualHint: "", manualUrl: "" });
    render(<ToolInstallPanel id="opencode" />);
    fireEvent.click(await screen.findByText(/제거/));
    // 인라인 확인 버튼
    fireEvent.click(await screen.findByText(/정말 제거/));
    await waitFor(() => expect(mocks.uninstallTool).toHaveBeenCalledWith("opencode"));
  });

  test("removed_false_shows_manual_guide", async () => {
    mocks.toolInstallStatus.mockResolvedValue(true);
    mocks.uninstallTool.mockResolvedValue({
      removed: false,
      exitCode: null,
      manualHint: "설정 > 앱에서 제거하세요.",
      manualUrl: "https://antigravity.google/docs/cli-install",
    });
    render(<ToolInstallPanel id="agy" />);
    fireEvent.click(await screen.findByText(/제거/));
    fireEvent.click(await screen.findByText(/정말 제거/));
    expect(await screen.findByText(/설정 > 앱에서 제거하세요\./)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd vibelign-gui && rtk vitest run src/components/tools/__tests__/ToolInstallPanel.test.tsx 2>&1 | tail -20`
Expected: FAIL — 제거 버튼 없음("제거" 텍스트 못 찾음).

- [ ] **Step 3: 패널에 제거 흐름 구현**

`ToolInstallPanel.tsx`를 수정한다. import에 `uninstallTool`, `shouldGuideManualUninstall`, `ToolUninstallResult` 추가(`:4-10` import 블록):

```tsx
import {
  installTool,
  uninstallTool,
  toolInstallStatus,
  getInstaller,
  shouldGuideManual,
  shouldGuideManualUninstall,
  type ToolInstallResult,
  type ToolUninstallResult,
} from "../../lib/tools/installerRegistry";
```

phase 타입(`:19`)에 제거 단계 추가:

```tsx
  const [phase, setPhase] = useState<
    "idle" | "installing" | "done" | "manual" | "confirm-uninstall" | "uninstalling" | "removed" | "manual-uninstall"
  >("idle");
```

제거 결과 상태를 `result` 아래에 추가(`:21` 근처):

```tsx
  const [uninstallResult, setUninstallResult] = useState<ToolUninstallResult | null>(null);
```

`start` 함수(`:47-63`) 다음에 제거 핸들러 추가:

```tsx
  async function startUninstall() {
    setPhase("uninstalling");
    setLines([]);
    try {
      const r = await uninstallTool(id);
      setUninstallResult(r);
      if (shouldGuideManualUninstall(r)) {
        setPhase("manual-uninstall");
      } else {
        setInstalled(false);
        setPhase("removed");
      }
    } catch {
      setPhase("manual-uninstall");
    }
  }
```

설치됨 표시 줄(`:75-78`)을 수정해 제거 버튼을 노출한다:

```tsx
      <div style={{ fontWeight: 900, fontSize: 14, display: "flex", alignItems: "center", gap: 8 }}>
        <span>
          {meta.displayName} {installed ? "✓ 설치됨" : ""}
          {meta.recommendedForBeginner && !installed ? " — 무료·키 불필요 (추천)" : ""}
        </span>
        {installed && (phase === "idle" || phase === "done" || phase === "removed") && (
          <button
            className="btn btn-sm"
            onClick={() => setPhase("confirm-uninstall")}
            style={{ border: "2px solid #B91C1C", background: "transparent", color: "#B91C1C", fontWeight: 800, marginLeft: "auto" }}
          >
            🗑 제거
          </button>
        )}
      </div>
```

`phase === "installing"` 블록(`:96-101`) 다음에 제거 UI 블록들을 추가한다:

```tsx
      {phase === "confirm-uninstall" && (
        <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
          <div style={{ fontWeight: 800 }}>정말 제거할까요? (설정·로그인은 유지됩니다)</div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn btn-sm"
              onClick={() => void startUninstall()}
              style={{ background: "#B91C1C", color: "#fff", border: "2px solid #B91C1C", fontWeight: 800 }}
            >
              제거
            </button>
            <button className="btn btn-sm" onClick={() => setPhase("idle")}>취소</button>
          </div>
        </div>
      )}

      {phase === "uninstalling" && (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="spinner" />
          <span style={{ fontWeight: 800, fontSize: 13 }}>제거 중…</span>
        </div>
      )}

      {phase === "removed" && (
        <div style={{ fontSize: 12, color: "#166534", fontWeight: 700 }}>✓ 제거 완료!</div>
      )}

      {phase === "manual-uninstall" && (
        <div style={{ fontSize: 12, color: "#92400E", display: "grid", gap: 6 }}>
          <div style={{ fontWeight: 800 }}>자동 제거가 안 됐어요 — 직접 제거해 주세요.</div>
          {uninstallResult?.manualHint && <div>{uninstallResult.manualHint}</div>}
          {uninstallResult?.manualUrl && (
            <button
              className="btn btn-sm"
              onClick={() => {
                if (uninstallResult.manualUrl) void openUrl(uninstallResult.manualUrl).catch(() => {});
              }}
              style={{ justifySelf: "start" }}
            >
              제거 안내 페이지 열기 →
            </button>
          )}
          <button
            className="btn btn-sm"
            onClick={() =>
              void toolInstallStatus(id).then((ok) => {
                setInstalled(ok);
                if (!ok) setPhase("removed");
              })
            }
            style={{ justifySelf: "start" }}
          >
            제거 후 다시 확인
          </button>
        </div>
      )}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd vibelign-gui && rtk vitest run src/components/tools/__tests__/ToolInstallPanel.test.tsx 2>&1 | tail -20`
Expected: PASS (3 테스트).

- [ ] **Step 5: 타입체크 + 린트**

Run: `cd vibelign-gui && rtk tsc --noEmit 2>&1 | tail -5 && rtk eslint src/components/tools/ToolInstallPanel.tsx 2>&1 | tail -5`
Expected: 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add vibelign-gui/src/components/tools/ToolInstallPanel.tsx vibelign-gui/src/components/tools/__tests__/ToolInstallPanel.test.tsx
git commit -m "feat(tool-uninstall): ToolInstallPanel 제거 버튼·확인·안내 폴백"
```

---

## Self-Review 결과

- **Spec coverage**: 제거 매트릭스(Task 1 레지스트리) / agy remove_binary(Task 2) / 안내 폴백(Task 1·2·4) / UI 제거 버튼·확인·안내(Task 4) / Rust·프론트 테스트(Task 1·4) — 전부 매핑됨.
- **Placeholder scan**: 모든 코드 스텝에 실제 코드 포함. TBD/TODO 없음.
- **Type consistency**: `ToolUninstallResult`(removed/exitCode/manualHint/manualUrl) — Rust(camelCase serde) ↔ TS 일치. `uninstallTool(id)` 시그니처 Task 2·3·4 동일. phase 문자열 일관.
- **비고**: opencode/codex는 mac/win 자동(또는 codex-win 안내), agy는 mac remove_binary·win 안내 — 스코프 "바이너리만"과 일치(config 보존).
