# AI CLI 도구 언인스톨 설계

- **날짜**: 2026-06-14
- **브랜치**: feat/vibelign-product-renew
- **상태**: 설계 승인됨 (구현 계획 대기)

## 배경 / 문제

클로드코드는 GUI에서 언인스톨(`uninstall_claude_code`)을 제공한다. 하지만 자동
설치 가능한 나머지 AI CLI 3종(**OpenCode / Codex / Antigravity**)은 설치만 있고
제거 수단이 없다. 사용자가 GUI 안에서 이 도구들을 되돌릴 방법이 필요하다.

설치 흐름은 다음과 같이 이미 존재한다:
- `vibelign-gui/src-tauri/src/commands/tool_install.rs` — `ToolInstaller` 레지스트리 +
  `install_tool` Tauri 커맨드(spawn_blocking + 출력 스트리밍 + 설치 후 재-probe).
- `vibelign-gui/src/lib/tools/installerRegistry.ts` — `installTool` / `toolInstallStatus` 래퍼.
- `vibelign-gui/src/components/tools/ToolInstallPanel.tsx` — 설치 UI(idle/installing/done/manual phase).
- `vibelign-gui/src/components/ToolSetupSelector.tsx` — 칩 옆 "자동 설치" 버튼이 패널을 연다.

## 스코프 결정 (확정)

1. **제거 범위 = CLI 바이너리만.** 클로드코드 언인스톨과 동일. VibeLign이
   `vib start --tools`로 등록한 MCP 설정(`.mcp.json` 등)·규칙 파일은 건드리지 않는다.
   도구 자체의 config/data·로그인 상태도 보존한다.
2. **제거 명령이 있는 도구/OS = 자동, 없으면 안내 폴백.** 설치의 `manual_url` 폴백과
   동일한 패턴. 거짓 성공을 만들지 않는다(제거 후 재-probe로 검증).

## 제거 명령 매트릭스 (도구 × OS)

| 도구 | macOS | Windows |
|---|---|---|
| **opencode** | `opencode uninstall --keep-config --keep-data --force` (내장 명령, 바이너리만) | `npm uninstall -g opencode-ai` |
| **codex** | `npm uninstall -g @openai/codex` | 안내 폴백 (powershell 설치 → 깔끔한 제거 명령 없음) |
| **agy** | **바이너리 직접 삭제** (resolve된 경로 1개 `remove_file`) | 안내 폴백 (설정 > 앱 > Installed Apps) |

`--keep-config --keep-data`로 opencode "바이너리만" 스코프를 지킨다.

### agy 바이너리 직접 삭제 — 안전 근거

agy는 공식 `agy uninstall` 명령이 없다. macOS는 단일 바이너리이므로 다음으로 안전하게 제거한다:

```rust
let path = find_executable("agy");   // PATH에서 실제 resolve. 추측 안 함.
std::fs::remove_file(path)?;          // 파일 1개만. 비재귀. 셸 미경유.
```

- **경로 추측 없음**: 하드코딩(`~/.local/bin/agy`)이 아니라 `find_executable`가 돌려준 실제 경로만 삭제.
- **파일 1개·비재귀**: `std::fs::remove_file`는 디렉터리/재귀/glob 불가. 셸을 안 거쳐 인젝션·확장 위험 없음.
- **"agy" 파일만**: `find_executable`이 돌려주는 건 정의상 `agy` 실행파일.
- **삭제 후 재-probe**: 안 사라졌으면(심링크·공유 위치 예외) 안내 폴백으로 전환. 거짓 성공 없음.
- config(`~/.gemini/antigravity-cli/`)는 손대지 않음 → "바이너리만" 스코프와 일치.
  (opencode 내장 uninstall보다 오히려 덜 공격적.)

Windows agy는 Installed Apps로 등록되는 구조라 파일 삭제로 깔끔하게 안 빠진다 → 안내 폴백.

## 컴포넌트 설계

### 1. Rust 백엔드 — `tool_install.rs`

**`ToolInstaller` 구조체 확장** (제거 정보 추가):

```rust
// 도구별 제거 방식
pub(crate) enum UninstallKind {
    /// OS별 제거 명령. None = 그 OS는 안내 폴백.
    Command {
        mac: Option<(&'static str, &'static [&'static str])>,
        win: Option<(&'static str, &'static [&'static str])>,
    },
    /// probe_binary 경로를 resolve 후 remove_file (agy mac). 그 외 OS는 안내.
    RemoveBinary,
    /// 전부 수동 안내.
    Manual,
}
```

`ToolInstaller`에 필드 추가:
- `uninstall: UninstallKind`
- `uninstall_hint: &'static str` — 안내 폴백 시 보여줄 수동 제거 단계
- `uninstall_url: &'static str` — 안내 폴백 시 열 공식 문서

**새 커맨드** `uninstall_tool` — `install_tool` 미러링:

```rust
#[derive(Serialize)]  // camelCase
pub(crate) struct ToolUninstallResult {
    pub removed: bool,
    pub exit_code: Option<i32>,
    pub manual_hint: String,   // removed=false 일 때 안내
    pub manual_url: String,
}

#[tauri::command]
pub(crate) async fn uninstall_tool(app: tauri::AppHandle, id: String)
    -> Result<ToolUninstallResult, String>
```

동작:
- `Command` + 해당 OS 명령 있음 → `spawn_blocking`으로 spawn, stdout/stderr를
  `tool-install-output` 이벤트로 스트리밍(설치와 동일 이벤트, `stream` 필드로 구분).
- `RemoveBinary` + mac → `find_executable(probe)` resolve 후 `std::fs::remove_file`.
- `Manual`이거나 해당 OS 명령 없음(`None`) → 실행 없이 `removed:false` + `uninstall_hint`/`uninstall_url` 반환.
- 종료 후 **재-probe**: `removed = find_executable(probe).is_none()`.

`lib.rs`의 `invoke_handler`에 `uninstall_tool` 등록.

### 2. 프론트 래퍼 — `installerRegistry.ts`

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

### 3. UI — `ToolInstallPanel.tsx`

현재 패널은 `installed === true`면 "✓ 설치됨"만 표시. 여기에 제거 흐름 추가:

- phase 상태머신을 `mode: "install" | "uninstall"`로 정리(파일 1개 유지, 책임만 분리).
- **설치됨 상태**일 때 `🗑 제거` 버튼(빨강 아웃라인) 노출.
- 클릭 → **인라인 확인**("정말 제거할까요? 설정·로그인은 유지됩니다") → `uninstallTool(id)`.
- `removing` phase: 스피너 + 로그 스트림(설치와 동일 이벤트 재사용).
- 성공(`removed:true`) → `removed` 상태, 패널은 다시 미설치 표시로 복귀(재-probe).
- 실패/Manual(`removed:false`) → 설치의 `manual` phase처럼 **수동 안내(manualHint) + 문서 열기 버튼(manualUrl) + "제거 후 다시 확인"**.

## 테스트

### Rust (`tool_install.rs` 테스트 모듈에 추가)
- 3개 도구 모두 `uninstall` 정보 존재.
- opencode: OS별 Command 둘 다 non-empty.
- codex: mac Command 있음, win 없음(→ 안내).
- agy: `RemoveBinary`, win은 안내.
- 안내 폴백 도구는 `uninstall_hint`/`uninstall_url` non-empty.

### 프론트 (`ToolInstallPanel` 테스트 옆)
- `installed=true`면 제거 버튼 노출.
- 제거 버튼 → 확인 → `uninstallTool` 호출.
- `removed:false` 반환 시 수동 안내 표시.

## 비목표 (YAGNI)
- MCP 설정/규칙 파일 정리(스코프 외 — 사용자 결정).
- 도구 config/data·로그인 삭제(스코프 외).
- Windows agy/codex 자동 제거(깔끔한 명령 없음 → 안내로 충분).
- 일괄 제거("전체 제거") 버튼(개별 제거로 충분).

## 영향 파일
- `vibelign-gui/src-tauri/src/commands/tool_install.rs` (구조체 확장 + uninstall_tool + 테스트)
- `vibelign-gui/src-tauri/src/lib.rs` (커맨드 등록)
- `vibelign-gui/src/lib/tools/installerRegistry.ts` (래퍼 + 타입)
- `vibelign-gui/src/components/tools/ToolInstallPanel.tsx` (제거 UI)
- 프론트/Rust 테스트 파일
