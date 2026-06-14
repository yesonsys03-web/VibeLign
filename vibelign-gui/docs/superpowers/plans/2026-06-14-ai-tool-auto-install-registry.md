# AI 도구 자동설치 레지스트리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** opencode·codex·antigravity(agy)를 앱 안에서 원클릭 자동설치하고(Win/mac), opencode+무료모델을 무키 기본값으로, 자동설치 불가/실패 시 가이드 수동설치로 폴백한다.

**Architecture:** 도구별 설치 메타를 데이터 레지스트리로 정의(rust+ts 미러). 백엔드 `install_tool` 커맨드가 플랫폼별 설치명령을 spawn→로그 스트림(run_preview 패턴)→셸 프로브(`find_executable`)한다. 프론트는 OnboardingClaudeSetup 패턴의 일반 설치 패널을 재사용. Claude 기존 설치 플로·모델 실행부는 무변경.

**Tech Stack:** Tauri(Rust, serde, std::process) + React/TS, Vitest, `cargo test`. 기존 헬퍼 재사용: `find_executable`·`augmented_vib_path`·`hide_console`(platform.rs)·run_preview의 `spawn_output_thread` 스트리밍 패턴.

**Spec:** `docs/superpowers/specs/2026-06-14-ai-tool-auto-install-registry-design.md`

---

## File Structure
- Create `src-tauri/src/commands/tool_install.rs` — 레지스트리(데이터) + 순수 헬퍼(플랫폼 명령 선택·폴백 판정) + `install_tool`/`tool_install_status` 커맨드 + 인라인 테스트.
- Modify `src-tauri/src/lib.rs` — `mod` 선언 + 커맨드 2개 등록.
- Create `src/lib/tools/installerRegistry.ts` — TS 미러 메타 + 폴백 판정 순수 함수 + invoke 래퍼.
- Create `src/lib/tools/__tests__/installerRegistry.test.ts`.
- Create `src/components/tools/ToolInstallPanel.tsx` — 일반 설치 패널(설치 중→로그→프로브→완료/인증안내/수동폴백).
- Modify `src/components/ToolSetupSelector.tsx` — 자동설치 메타 정합 + 패널 연결 훅.
- Modify `src/pages/WorkRoom.tsx` — no-provider 상태에 "opencode 무료 원클릭 설치".
- 무변경: `onboarding/`(Claude), `planning_persona.rs` 실행부.

---

## Phase 1 — 백엔드 레지스트리 + 설치 런타임

### Task 1: 설치 레지스트리 + 순수 헬퍼 (Rust, TDD)

**Files:** Create `src-tauri/src/commands/tool_install.rs`

- [ ] **Step 1: 실패 테스트 작성** — `tool_install.rs` 끝에:

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_has_three_tools_with_probe() {
        for id in ["opencode", "codex", "agy"] {
            let t = tool_installer(id).expect("registered");
            assert!(!t.probe_binary.is_empty());
            assert!(!t.manual_url.is_empty());
        }
        assert!(tool_installer("unknown").is_none());
    }
    #[test]
    fn opencode_is_beginner_default_and_no_auth() {
        let t = tool_installer("opencode").unwrap();
        assert!(t.recommended_for_beginner);
        assert_eq!(t.auth, AuthKind::None);
    }
    #[test]
    fn codex_and_agy_need_login() {
        assert_eq!(tool_installer("codex").unwrap().auth, AuthKind::Login);
        assert_eq!(tool_installer("agy").unwrap().auth, AuthKind::Login);
    }
    #[test]
    fn install_command_selected_per_os() {
        // macos/windows 둘 다 비어있지 않은 program+args 를 돌려줘야 한다.
        let t = tool_installer("agy").unwrap();
        let mac = install_command(t, "macos").expect("mac cmd");
        let win = install_command(t, "windows").expect("win cmd");
        assert!(!mac.0.is_empty() && !mac.1.is_empty());
        assert!(!win.0.is_empty() && !win.1.is_empty());
    }
    #[test]
    fn unsupported_os_yields_no_command_for_manual_fallback() {
        let t = tool_installer("agy").unwrap();
        assert!(install_command(t, "linux-unknown").is_none());
    }
}
```

- [ ] **Step 2: 실패 확인** — `cd src-tauri && cargo test tool_install 2>&1 | tail -15` (모듈/심볼 미정의).

- [ ] **Step 3: 구현 작성** — `tool_install.rs` 상단:

```rust
// ANCHOR: TOOL_INSTALL_START
use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum AuthKind {
    None,
    Login,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct ToolInstaller {
    pub id: &'static str,
    pub display_name: &'static str,
    pub probe_binary: &'static str,
    /// (program, args) — macOS
    pub mac_program: &'static str,
    pub mac_args: &'static [&'static str],
    /// (program, args) — Windows
    pub win_program: &'static str,
    pub win_args: &'static [&'static str],
    pub auth: AuthKind,
    pub auth_hint: &'static str,
    pub manual_url: &'static str,
    pub recommended_for_beginner: bool,
}

const OPENCODE: ToolInstaller = ToolInstaller {
    id: "opencode", display_name: "OpenCode", probe_binary: "opencode",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://opencode.ai/install | bash"],
    win_program: "npm", win_args: &["install", "-g", "opencode-ai"],
    auth: AuthKind::None,
    auth_hint: "무료 모델이라 추가 로그인이 필요 없어요 — 바로 쓸 수 있어요.",
    manual_url: "https://opencode.ai/download", recommended_for_beginner: true,
};
const CODEX: ToolInstaller = ToolInstaller {
    id: "codex", display_name: "Codex", probe_binary: "codex",
    mac_program: "npm", mac_args: &["install", "-g", "@openai/codex"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://chatgpt.com/codex/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 OpenAI 로그인이 필요해요 — 터미널에서 `codex` 를 한 번 실행해 로그인하세요.",
    manual_url: "https://www.npmjs.com/package/@openai/codex", recommended_for_beginner: false,
};
const AGY: ToolInstaller = ToolInstaller {
    id: "agy", display_name: "Antigravity", probe_binary: "agy",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://antigravity.google/cli/install.sh | bash"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://antigravity.google/cli/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 Google 로그인이 필요해요 — `agy` 를 처음 실행하면 브라우저 로그인이 열려요.",
    manual_url: "https://antigravity.google/docs/cli-install", recommended_for_beginner: false,
};

pub(crate) fn tool_installer(id: &str) -> Option<&'static ToolInstaller> {
    match id {
        "opencode" => Some(&OPENCODE),
        "codex" => Some(&CODEX),
        "agy" => Some(&AGY),
        _ => None,
    }
}

/// os: "macos" | "windows" (그 외는 None → 가이드 수동 폴백). 반환 (program, args).
pub(crate) fn install_command(t: &ToolInstaller, os: &str) -> Option<(String, Vec<String>)> {
    match os {
        "macos" => Some((t.mac_program.to_string(), t.mac_args.iter().map(|s| s.to_string()).collect())),
        "windows" => Some((t.win_program.to_string(), t.win_args.iter().map(|s| s.to_string()).collect())),
        _ => None,
    }
}

#[cfg(target_os = "macos")]
fn current_os() -> &'static str { "macos" }
#[cfg(target_os = "windows")]
fn current_os() -> &'static str { "windows" }
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn current_os() -> &'static str { "other" }
// ANCHOR: TOOL_INSTALL_END
```

- [ ] **Step 4: 통과 확인** — `cd src-tauri && cargo test tool_install 2>&1 | tail -15` (5 passed).

- [ ] **Step 5: 커밋**
```bash
git add src-tauri/src/commands/tool_install.rs
git commit -m "feat(tool-install): 설치 레지스트리 + 플랫폼 명령 선택 (opencode/codex/agy)"
```

### Task 2: `install_tool`·`tool_install_status` 커맨드 (Rust)

**Files:** Modify `src-tauri/src/commands/tool_install.rs`, `src-tauri/src/lib.rs`

- [ ] **Step 1: 구현 추가** (`ANCHOR: TOOL_INSTALL_END` 직전). run_preview 의 스트리밍 패턴을 따른다.

```rust
use std::io::{BufRead, BufReader};
use super::platform::{augmented_vib_path, hide_console};
use super::planning_persona::find_executable;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolInstallResult {
    pub installed: bool,
    pub exit_code: Option<i32>,
    /// none/login — 설치됐을 때 다음에 필요한 인증
    pub auth: AuthKind,
    pub auth_hint: String,
    /// 자동설치 불가/실패 시 수동 폴백용
    pub manual_url: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolInstallOutput {
    pub id: String,
    pub stream: String,
    pub line: String,
}

#[tauri::command]
pub(crate) fn tool_install_status(id: String) -> Result<bool, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    Ok(find_executable(t.probe_binary).is_some())
}

#[tauri::command]
pub(crate) fn install_tool(app: tauri::AppHandle, id: String) -> Result<ToolInstallResult, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    let Some((program, args)) = install_command(t, current_os()) else {
        // 지원 안 되는 OS → 가이드 수동 폴백
        return Ok(ToolInstallResult {
            installed: false, exit_code: None, auth: t.auth,
            auth_hint: t.auth_hint.to_string(), manual_url: t.manual_url.to_string(),
        });
    };
    let mut cmd = std::process::Command::new(&program);
    cmd.args(&args);
    cmd.env("PATH", augmented_vib_path());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());
    hide_console(&mut cmd);
    let mut child = cmd.spawn().map_err(|e| format!("설치 실행 실패: {e}"))?;

    let emit = |app: &tauri::AppHandle, stream: &str, line: String| {
        use tauri::Emitter;
        let _ = app.emit("tool-install-output", ToolInstallOutput { id: id.clone(), stream: stream.into(), line });
    };
    if let Some(out) = child.stdout.take() {
        let (app2, stream) = (app.clone(), "stdout");
        for line in BufReader::new(out).lines().map_while(Result::ok) {
            emit(&app2, stream, line);
        }
    }
    if let Some(err) = child.stderr.take() {
        for line in BufReader::new(err).lines().map_while(Result::ok) {
            emit(&app, "stderr", line);
        }
    }
    let status = child.wait().map_err(|e| format!("설치 대기 실패: {e}"))?;
    // 종료 후 새로 PATH 해석해 프로브(설치 직후 PATH 반영 확인).
    let installed = find_executable(t.probe_binary).is_some();
    Ok(ToolInstallResult {
        installed,
        exit_code: status.code(),
        auth: t.auth,
        auth_hint: t.auth_hint.to_string(),
        manual_url: t.manual_url.to_string(),
    })
}
```

> 참고: stdout 를 동기로 끝까지 읽은 뒤 stderr 를 읽는다(설치 도구는 보통 stdout 위주, 단순화). 더 정밀한 동시 스트리밍이 필요하면 run_preview 의 `spawn_output_thread` 를 추출해 재사용해도 된다 — 단순 버전으로 시작.

- [ ] **Step 2: lib.rs 등록** — `mod` 영역에 `pub mod tool_install;`(commands/mod.rs 에 맞춰; 기존 패턴 확인 후 추가) 후 `generate_handler!` 에:
```rust
            commands::tool_install::install_tool,
            commands::tool_install::tool_install_status,
```
(commands 모듈 선언 위치는 `src-tauri/src/commands/mod.rs` 또는 lib.rs 의 기존 `pub mod` 나열을 따라 `pub mod tool_install;` 추가.)

- [ ] **Step 3: 빌드 + 테스트** — `cd src-tauri && cargo test tool_install 2>&1 | tail -8 && cargo build 2>&1 | tail -3` (5 passed, 빌드 OK).

- [ ] **Step 4: 커밋**
```bash
git add src-tauri/src/commands/tool_install.rs src-tauri/src/lib.rs src-tauri/src/commands/mod.rs
git commit -m "feat(tool-install): install_tool/tool_install_status 커맨드 — spawn·로그스트림·프로브"
```

---

## Phase 2 — 프론트 레지스트리 + 설치 패널

### Task 3: TS 레지스트리 + 폴백 판정 + invoke 래퍼 (TDD)

**Files:** Create `src/lib/tools/installerRegistry.ts`, `src/lib/tools/__tests__/installerRegistry.test.ts`

- [ ] **Step 1: 실패 테스트** — `installerRegistry.test.ts`:

```ts
import { describe, expect, test } from "vitest";
import { TOOL_INSTALLERS, getInstaller, shouldGuideManual } from "../installerRegistry";

describe("installerRegistry", () => {
  test("opencode 는 무키 추천 기본", () => {
    const t = getInstaller("opencode")!;
    expect(t.auth).toBe("none");
    expect(t.recommendedForBeginner).toBe(true);
  });
  test("codex·agy 는 login 필요", () => {
    expect(getInstaller("codex")!.auth).toBe("login");
    expect(getInstaller("agy")!.auth).toBe("login");
  });
  test("미등록 도구는 undefined", () => {
    expect(getInstaller("nope")).toBeUndefined();
  });
  test("설치 실패/미설치면 수동 가이드", () => {
    expect(shouldGuideManual({ installed: false, exitCode: 1 })).toBe(true);
    expect(shouldGuideManual({ installed: false, exitCode: null })).toBe(true); // 미지원 OS
    expect(shouldGuideManual({ installed: true, exitCode: 0 })).toBe(false);
  });
});
```

- [ ] **Step 2: 실패 확인** — `npx vitest run src/lib/tools/__tests__/installerRegistry.test.ts`.

- [ ] **Step 3: 구현** — `src/lib/tools/installerRegistry.ts`:

```ts
import { invoke } from "@tauri-apps/api/core";

export type AuthKind = "none" | "login";

export interface ToolInstallerMeta {
  readonly id: "opencode" | "codex" | "agy";
  readonly displayName: string;
  readonly auth: AuthKind;
  readonly recommendedForBeginner: boolean;
}

export const TOOL_INSTALLERS: readonly ToolInstallerMeta[] = [
  { id: "opencode", displayName: "OpenCode (무료)", auth: "none", recommendedForBeginner: true },
  { id: "codex", displayName: "Codex", auth: "login", recommendedForBeginner: false },
  { id: "agy", displayName: "Antigravity", auth: "login", recommendedForBeginner: false },
];

export function getInstaller(id: string): ToolInstallerMeta | undefined {
  return TOOL_INSTALLERS.find((t) => t.id === id);
}

export interface ToolInstallResult {
  installed: boolean;
  exitCode: number | null;
  auth?: AuthKind;
  authHint?: string;
  manualUrl?: string;
}

/** 자동설치가 실패했거나(installed=false) 미지원(exitCode=null)이면 수동 가이드로. */
export function shouldGuideManual(r: { installed: boolean; exitCode: number | null }): boolean {
  return !r.installed;
}

export function installTool(id: string): Promise<ToolInstallResult> {
  return invoke<ToolInstallResult>("install_tool", { id });
}
export function toolInstallStatus(id: string): Promise<boolean> {
  return invoke<boolean>("tool_install_status", { id });
}
```

- [ ] **Step 4: 통과 + tsc** — `npx vitest run src/lib/tools/__tests__/installerRegistry.test.ts && npx tsc --noEmit` (4 passed, 에러 없음).

- [ ] **Step 5: 커밋**
```bash
git add src/lib/tools/installerRegistry.ts src/lib/tools/__tests__/installerRegistry.test.ts
git commit -m "feat(tool-install): 프론트 설치 레지스트리 + 폴백 판정 + invoke 래퍼"
```

### Task 4: 일반 설치 패널 + 도구 선택 연결

**Files:** Create `src/components/tools/ToolInstallPanel.tsx`; Modify `src/components/ToolSetupSelector.tsx`

- [ ] **Step 1: ToolInstallPanel 작성** — `src/components/tools/ToolInstallPanel.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { installTool, toolInstallStatus, getInstaller, shouldGuideManual, type ToolInstallResult } from "../../lib/tools/installerRegistry";

interface Props { readonly id: string; readonly onDone?: () => void; }

export function ToolInstallPanel({ id, onDone }: Props) {
  const meta = getInstaller(id);
  const [phase, setPhase] = useState<"idle" | "installing" | "done" | "manual">("idle");
  const [lines, setLines] = useState<string[]>([]);
  const [result, setResult] = useState<ToolInstallResult | null>(null);
  const [installed, setInstalled] = useState(false);
  const outRef = useRef<HTMLDivElement>(null);

  useEffect(() => { toolInstallStatus(id).then(setInstalled).catch(() => setInstalled(false)); }, [id]);
  useEffect(() => {
    const un = listen<{ id: string; stream: string; line: string }>("tool-install-output", (e) => {
      if (e.payload.id === id) setLines((p) => [...p, e.payload.line]);
    });
    return () => { void un.then((f) => f()); };
  }, [id]);
  useEffect(() => { outRef.current?.scrollTo(0, outRef.current.scrollHeight); }, [lines]);

  if (!meta) return null;

  async function start() {
    setPhase("installing"); setLines([]);
    try {
      const r = await installTool(id);
      setResult(r);
      if (shouldGuideManual(r)) setPhase("manual");
      else { setInstalled(true); setPhase("done"); onDone?.(); }
    } catch {
      setPhase("manual");
    }
  }

  return (
    <div style={{ border: "2px solid #1A1A1A", padding: 12, display: "grid", gap: 8, background: "#F5F1E3" }}>
      <div style={{ fontWeight: 900, fontSize: 14 }}>
        {meta.displayName} {installed ? "✓ 설치됨" : ""}
        {meta.recommendedForBeginner && !installed ? " — 무료·키 불필요 (추천)" : ""}
      </div>
      {phase === "idle" && !installed && (
        <button className="btn" onClick={() => void start()}
          style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900, justifySelf: "start" }}>
          ⬇ 자동 설치
        </button>
      )}
      {phase === "installing" && (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="spinner" /><span style={{ fontWeight: 800, fontSize: 13 }}>설치 중… (수십 초~몇 분)</span>
        </div>
      )}
      {(phase === "installing" || lines.length > 0) && (
        <div ref={outRef} style={{ maxHeight: 160, overflowY: "auto", background: "#fff", border: "1px solid #D6D2C4", padding: 8, fontFamily: "IBM Plex Mono, monospace", fontSize: 11, whiteSpace: "pre-wrap" }}>
          {lines.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
      {phase === "done" && result && (
        <div style={{ fontSize: 12, color: "#166534", fontWeight: 700 }}>
          ✓ 설치 완료!{result.auth === "login" ? ` ${result.authHint}` : ` ${result.authHint ?? ""}`}
        </div>
      )}
      {phase === "manual" && (
        <div style={{ fontSize: 12, color: "#92400E", display: "grid", gap: 6 }}>
          <div style={{ fontWeight: 800 }}>자동 설치가 안 됐어요 — 직접 설치해 주세요.</div>
          {result?.manualUrl && (
            <button className="btn btn-sm" onClick={() => { if (result.manualUrl) void import("@tauri-apps/plugin-opener").then((m) => m.openUrl(result.manualUrl!)); }} style={{ justifySelf: "start" }}>
              설치 페이지 열기 →
            </button>
          )}
          <button className="btn btn-sm" onClick={() => void toolInstallStatus(id).then((ok) => { setInstalled(ok); if (ok) setPhase("done"); })} style={{ justifySelf: "start" }}>
            설치 후 다시 확인
          </button>
        </div>
      )}
    </div>
  );
}
```

> 주의: `@tauri-apps/plugin-opener` 가 프로젝트에 있는지 확인(run_preview/openPreview 가 외부 열기를 어떻게 하는지 참고). 없으면 기존 외부-열기 방식(invoke 커맨드)으로 교체.

- [ ] **Step 2: ToolSetupSelector 연결** — 각 `autoInstall: true` 후보(claude 제외: 기존 플로 유지) 도구에 대해, 선택/클릭 시 `ToolInstallPanel` 을 펼쳐 보여주도록 한다. 최소: 도구 항목 아래 "자동 설치" 토글로 `<ToolInstallPanel id={...} />` 렌더(opencode/codex/agy 만). claude·claude_desktop·cursor 는 기존 동작 유지.

- [ ] **Step 3: tsc + 테스트 + 빌드** — `npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests " | tail -2 && npm run build 2>&1 | grep -E "built in|error" | head -2`.

- [ ] **Step 4: 커밋**
```bash
git add src/components/tools/ToolInstallPanel.tsx src/components/ToolSetupSelector.tsx
git commit -m "feat(tool-install): 일반 설치 패널(로그·인증안내·수동폴백) + 도구 선택 연결"
```

---

## Phase 3 — 작업방 데드엔드 제거

### Task 5: WorkRoom no-provider → opencode 무키 원클릭

**Files:** Modify `src/pages/WorkRoom.tsx`

- [ ] **Step 1: no-provider 블록에 설치 패널.** `!anyDetected` 블록(H3 에서 다듬은 영역, "AI 도구가 없네요…" 부근)에 opencode 무키 원클릭을 우선 노출:

```tsx
{providers !== null && !anyDetected && (
  <div style={{ display: "grid", gap: 8 }}>
    <div style={{ fontSize: 13, fontWeight: 800 }}>아직 실행할 AI 도구가 없어요 — 무료로 바로 설치할 수 있어요.</div>
    <ToolInstallPanel id="opencode" onDone={() => void refreshProviders()} />
    <button className="btn btn-ghost btn-sm" onClick={onOpenSettings} style={{ fontSize: 12, justifySelf: "start" }}>
      다른 도구(codex·antigravity) 설치/등록 →
    </button>
  </div>
)}
```
- `ToolInstallPanel` import 추가. `refreshProviders` 는 기존 provider 감지 재실행 함수(없으면 providers 재조회 로직을 호출 — WorkRoom 의 provider 감지 effect 를 재실행하는 방식 사용; 정확한 함수명은 파일에서 확인).

- [ ] **Step 2: tsc + 테스트 + 빌드** — `npx tsc --noEmit && npm test 2>&1 | grep -E "Tests " | tail -1 && npm run build 2>&1 | grep -E "built in|error" | head -2`. 기존 WorkRoom 테스트가 깨지면 mock/기대 갱신(커버리지 약화 금지).

- [ ] **Step 3: 커밋**
```bash
git add src/pages/WorkRoom.tsx
git commit -m "feat(workroom): 도구 없음 상태에 opencode 무키 원클릭 설치 — 데드엔드 제거"
```

---

## Phase 4 — 검증

### Task 6: 전체 검증 + 수동 통합

- [ ] **Step 1: Rust 전체** — `cd src-tauri && cargo test 2>&1 | tail -5` (회귀 없음).
- [ ] **Step 2: 프론트 전체 + 빌드** — `npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests " && npm run build 2>&1 | grep -E "built in|error"`.
- [ ] **Step 3: 수동 통합(실기기, Win·mac 각각)** — 작업방 도구 없음 → opencode 원클릭 → 로그 스트림 → 설치 완료 → 즉시 실행 / codex·agy 설치 → 인증 안내 표시 / 일부러 실패(네트워크 차단) → 수동 폴백(페이지 열기·다시 확인) 노출.
- [ ] **Step 4: 검증 보고** (커밋 없음).

---

## Self-Review (작성자 점검 완료)
- **스펙 커버리지**: §3-1 레지스트리→Task1, §3-2 런타임(spawn·스트림·프로브)→Task2, §3-3 인증안내→ToolInstallResult.auth/authHint(Task2)+패널 표시(Task4), §3-4 수동폴백→shouldGuideManual(Task3)+패널 manual(Task4), §3-5 UI/기본값·작업방→Task4·5, Win/mac→install_command os 분기(Task1), Node 게이트→(런타임이 npm 실패 시 installed=false→manual 폴백으로 흡수; 별도 사전 게이트는 폴백이 커버). 매핑됨.
- **플레이스홀더**: 코드/명령/기대 구체. 단 lib.rs 모듈 선언 위치·`refreshProviders`/외부열기 API 는 "파일에서 확인" 지시(기존 패턴 의존) — 실행자가 해당 파일 관례를 따른다.
- **타입 일관성**: rust `AuthKind`(none/login serde lowercase) ↔ ts `AuthKind`("none"|"login"); `ToolInstallResult`(installed·exitCode·auth·authHint·manualUrl camelCase) rust serde ↔ ts; `install_tool`/`tool_install_status` 커맨드명 ↔ invoke 래퍼 일치; `tool_installer`/`install_command`/`shouldGuideManual`/`getInstaller` 정의↔사용 일치.
- **위험**: `@tauri-apps/plugin-opener` 존재 여부, WorkRoom provider 재조회 함수명 — Task 내 "확인" 명시. 동시 스트리밍 단순화(stdout→stderr 순차)는 설치 로그엔 충분, 필요 시 run_preview 패턴으로 승급.
