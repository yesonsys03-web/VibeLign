// === ANCHOR: RUN_PREVIEW_START ===
//! 실행해보기 (Run & Preview) — 마일스톤 1: 감지 + 러너
//! (plans/2026-06-12-실행해보기-run-preview-design.md §3·§4·§5).
//!
//! "빌드해서 배포"가 아니라 "실행해서 확인" — package.json 만으로 dev 실행 레시피를
//! 감지(detect_run_recipe, 순수)하고, watch.rs/work_room.rs 의 장기 프로세스 수명주기
//! (프로세스 그룹·트리 kill·앱종료 정리)를 복제해 자동 install → dev 실행을 돌린다.
//!
//! 설계 불변식 (기획안 §4·§5·§9 P0):
//! - 실행 명령은 **감지된 고정 셋**만 — 러너가 임의 명령 문자열을 받지 않는다(주입 표면 0).
//! - 자동 install 은 1회성 — node_modules 존재 시 건너뛴다(매번 install 금지).
//! - 취소·중지·앱종료는 반드시 **프로세스 트리 전체** kill — dev 서버는 npm → node 손자를
//!   만들어 plain kill 은 손자가 포트를 쥔 채 생존한다(재실행 충돌).
//! - 동시 1개 — 포트 충돌·자원 경쟁 방지. run_id 가 occupancy 토큰이다.
//!
//! M2 seam: 출력 라인에서 localhost:PORT 감지 → "run-preview-ready" 이벤트 → webview.
//! M3 seam: 작업방과의 동시 1개(§5) — 두 표면이 만나는 곳에서 상호배제 추가.

use std::io::{BufRead, BufReader};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use serde::Serialize;
use tauri::Emitter;

use super::planning_persona::find_executable;
use super::platform::{augmented_vib_path, hide_console};
use super::watch::kill_watch_child as kill_child_tree;
use super::work_room;

// ─── 타입 감지 (순수 코어, 테스트 우선) ─────────────────────────────────────────

/// 프로젝트 타입 — 미리보기 방식의 분기 축.
#[derive(Clone, Copy, PartialEq, Eq, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) enum ProjectKind {
    /// electron — 자체 OS 창(프로세스 본체가 화면).
    Electron,
    /// web — dev 서버가 포트를 열고, 앱 내 webview 로 미리보기(M2).
    Web,
    /// unknown — scripts.start 만 있어 타입을 못 좁힘. 로그만, 포트 감지되면 webview.
    Unknown,
    /// staticWeb — package.json 없이 index.html 만 있는 정적 HTML. 임베드 tiny_http
    /// 서버가 cwd 를 서빙하고 앱 내 webview 로 미리보기(외부 프로세스/네트워크 불필요).
    StaticWeb,
}

/// 실행 프로그램 — npm 서브커맨드 또는 npx(electron 폴백). 임의 문자열이 아니라
/// 감지가 만든 고정 셋만 들어온다(§4).
#[derive(Clone, PartialEq, Eq, Debug, Serialize)]
#[serde(rename_all = "camelCase", tag = "program", content = "args")]
pub(crate) enum RunProgram {
    /// npm 서브커맨드. ["start"] → `npm start`, ["run","dev"] → `npm run dev`.
    Npm(Vec<String>),
    /// npx 직접 실행. ["electron","."] → `npx electron .` (start 스크립트 없는 electron 폴백).
    Npx(Vec<String>),
    /// 정적 HTML — 외부 프로그램이 아니라 임베드 tiny_http 서버가 직접 서빙한다.
    /// run_start 가 spawn_orchestrator 경유 없이 특수 처리하므로 executable/args 는 미사용.
    Static,
}

impl RunProgram {
    fn npm_script(script: &str) -> Self {
        if script == "start" {
            RunProgram::Npm(vec!["start".into()])
        } else {
            RunProgram::Npm(vec!["run".into(), script.into()])
        }
    }

    /// 실행 바이너리 이름 — find_executable 로 .cmd/.exe 까지 해석된다.
    fn executable(&self) -> &'static str {
        match self {
            RunProgram::Npm(_) => "npm",
            RunProgram::Npx(_) => "npx",
            RunProgram::Static => "static",
        }
    }

    fn args(&self) -> &[String] {
        match self {
            RunProgram::Npm(a) | RunProgram::Npx(a) => a,
            RunProgram::Static => &[],
        }
    }

    /// 사용자 표시용 라벨 — "npm run dev", "npm start", "npx electron .".
    fn label(&self) -> String {
        format!("{} {}", self.executable(), self.args().join(" "))
    }
}

/// 미리보기 방식.
#[derive(Clone, PartialEq, Eq, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) enum PreviewKind {
    /// electron — 외부 OS 창(프로세스 자체).
    ExternalWindow,
    /// web — 출력에서 포트 감지 → webview. default_port 는 감지 전 추정(next/CRA=3000).
    Webview { default_port: Option<u16> },
    /// unknown — 로그만. 단 포트가 감지되면 webview 로 승격(런타임 판단).
    LogOnly,
}

/// 감지 결과 — UI 표시(label/kind)와 spawn 의도(program)를 함께 싣는다.
#[derive(Clone, PartialEq, Eq, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RunRecipe {
    kind: ProjectKind,
    program: RunProgram,
    command_label: String,
    preview: PreviewKind,
}

impl RunRecipe {
    fn new(kind: ProjectKind, program: RunProgram, preview: PreviewKind) -> Self {
        let command_label = program.label();
        Self { kind, program, command_label, preview }
    }
}

/// dependencies + devDependencies 어디든 키가 있으면 true.
/// vite 는 거의 devDependencies 에 산다 — 한쪽만 보면 vite 프로젝트를 놓친다.
fn dep_present(pkg: &serde_json::Value, name: &str) -> bool {
    ["dependencies", "devDependencies"].iter().any(|section| {
        pkg.get(section).and_then(|d| d.get(name)).is_some()
    })
}

fn script_present(pkg: &serde_json::Value, name: &str) -> bool {
    pkg.get("scripts").and_then(|s| s.get(name)).is_some()
}

/// package.json 본문 → 실행 레시피. **표는 우선순위 순**(§4) — 위에서부터 처음 맞는 행.
/// electron 이 있으면 scripts.dev 가 있어도 electron 으로 판정한다.
/// 순수 함수 — 파일 I/O 없음(테스트 용이).
pub(crate) fn detect_run_recipe(package_json: &str) -> Option<RunRecipe> {
    let pkg: serde_json::Value = serde_json::from_str(package_json).ok()?;

    // 1) electron — start 스크립트 있으면 npm start, 없으면 npx electron . 폴백.
    if dep_present(&pkg, "electron") {
        let program = if script_present(&pkg, "start") {
            RunProgram::npm_script("start")
        } else {
            RunProgram::Npx(vec!["electron".into(), ".".into()])
        };
        return Some(RunRecipe::new(ProjectKind::Electron, program, PreviewKind::ExternalWindow));
    }

    // 2) vite — npm run dev, 포트 감지(고정 기본 포트 없음, vite 는 5173 가 흔하나 가변).
    if dep_present(&pkg, "vite") {
        return Some(RunRecipe::new(
            ProjectKind::Web,
            RunProgram::npm_script("dev"),
            PreviewKind::Webview { default_port: None },
        ));
    }

    // 3) next — npm run dev, 기본 :3000.
    if dep_present(&pkg, "next") {
        return Some(RunRecipe::new(
            ProjectKind::Web,
            RunProgram::npm_script("dev"),
            PreviewKind::Webview { default_port: Some(3000) },
        ));
    }

    // 4) react-scripts(CRA) — npm start, 기본 :3000.
    if dep_present(&pkg, "react-scripts") {
        return Some(RunRecipe::new(
            ProjectKind::Web,
            RunProgram::npm_script("start"),
            PreviewKind::Webview { default_port: Some(3000) },
        ));
    }

    // 5) scripts.dev 존재 — web 기본, npm run dev.
    if script_present(&pkg, "dev") {
        return Some(RunRecipe::new(
            ProjectKind::Web,
            RunProgram::npm_script("dev"),
            PreviewKind::Webview { default_port: None },
        ));
    }

    // 6) scripts.start 만 — unknown, npm start, 로그만(포트 감지되면 webview).
    if script_present(&pkg, "start") {
        return Some(RunRecipe::new(
            ProjectKind::Unknown,
            RunProgram::npm_script("start"),
            PreviewKind::LogOnly,
        ));
    }

    // 7) 감지 실패.
    None
}

// ─── 포트 감지 (순수 코어, 테스트 우선) ─────────────────────────────────────────

/// 미리보기로 띄울 수 있는 로컬 호스트 — 0.0.0.0/127.0.0.1 은 webview 로딩을 위해
/// localhost 로 정규화한다.
const LOCAL_HOSTS: [&str; 3] = ["localhost", "127.0.0.1", "0.0.0.0"];

/// dev 서버 출력 한 줄에서 로컬 미리보기 URL 을 추출 → `http://localhost:PORT`.
/// vite(`➜ Local: http://localhost:5173/`)·next·CRA·일반 서버 출력의 다중 형식을
/// 커버한다(§9 P1). 네트워크 주소(192.168.x.x)는 건너뛰고 로컬만 — NO_COLOR 로
/// ANSI 가 이미 제거돼 있다고 가정한다. 순수 함수(테스트 용이).
pub(crate) fn detect_preview_url(line: &str) -> Option<String> {
    // http 를 https 보다 먼저 — dev 서버는 http 가 기본이고, 한 줄에 둘이 섞여도
    // 로컬 http 를 우선한다.
    for scheme in ["http://", "https://"] {
        let mut from = 0usize;
        while let Some(rel) = line[from..].find(scheme) {
            let host_start = from + rel + scheme.len();
            let rest = &line[host_start..];
            // 호스트 = ':' / '/' / 공백 전까지.
            let host_end = rest
                .find(|c: char| c == ':' || c == '/' || c.is_whitespace())
                .unwrap_or(rest.len());
            let host = &rest[..host_end];
            if LOCAL_HOSTS.contains(&host) && rest[host_end..].starts_with(':') {
                let port: String =
                    rest[host_end + 1..].chars().take_while(|c| c.is_ascii_digit()).collect();
                if let Ok(port) = port.parse::<u16>() {
                    if port > 0 {
                        return Some(format!("{scheme}localhost:{port}"));
                    }
                }
            }
            from = host_start;
        }
    }
    None
}

/// 미리보기 webview 창의 고정 라벨 — 한 실행당 하나(재사용·정리 대상).
const PREVIEW_LABEL: &str = "run-preview";

/// 미리보기로 허용되는 주소인지 — 로컬 http(s) 만. detect_preview_url 가 만든 주소를
/// 프런트가 그대로 돌려보내지만, 임의 외부 URL 로딩을 막는 방어선이다.
fn validate_local_url(url: &str) -> Result<tauri::Url, String> {
    let parsed = tauri::Url::parse(url).map_err(|_| "잘못된 미리보기 주소예요.".to_string())?;
    let scheme_ok = matches!(parsed.scheme(), "http" | "https");
    let host_ok =
        matches!(parsed.host_str(), Some("localhost") | Some("127.0.0.1") | Some("0.0.0.0"));
    if scheme_ok && host_ok {
        Ok(parsed)
    } else {
        Err("로컬 미리보기 주소만 열 수 있어요.".into())
    }
}

// ─── 러너 (watch/work_room 수명주기 복제) ───────────────────────────────────────

struct RunRuntime {
    child: Option<std::process::Child>,
    /// 단조 증가 실행 id — 점유(occupancy) 토큰. 오케스트레이터는 run_id 가 바뀌면 즉시 물러난다.
    run_id: u64,
    /// 실행 생명주기가 슬롯을 점유 중인지 — install→run 핸드오프의 child=None 틈에도 유지된다
    /// (child.is_some() 만으로는 그 틈에 두 번째 실행이 끼어든다, advisor 지적).
    active: bool,
    /// 취소 요청 — 오케스트레이터가 stopped 로 보고하게 한다.
    cancelled: bool,
    /// 감지된 미리보기 URL — run-preview-ready 는 fire-once 라, 탭 이탈 후 복귀(run_status)
    /// 에서 [미리보기 열기]를 복원하려면 여기 들고 있어야 한다(advisor 지적).
    preview_url: Option<String>,
    /// 마지막 run-status 라벨("installing"/"running") — active 만으로는 install 갭과 실행을
    /// 구분 못 해, 탭 복귀 시 install 중인데 "실행 중"으로 오표시된다(M3a 리뷰 P2). run_status
    /// 가 이 값을 돌려줘 복원이 진짜 단계를 보여준다.
    status_label: Option<&'static str>,
    /// 정적 HTML 실행 시 임베드 tiny_http 서버 핸들. child 와 상호 배타적 —
    /// 정적 실행엔 child 가 없고, npm 실행엔 static_server 가 없다. 중지/앱종료 때
    /// `.unblock()` 으로 서빙 스레드를 끝낸다(child 트리 kill 과 동형).
    static_server: Option<Arc<tiny_http::Server>>,
}

impl RunRuntime {
    fn new() -> Self {
        Self {
            child: None,
            run_id: 0,
            active: false,
            cancelled: false,
            preview_url: None,
            status_label: None,
            static_server: None,
        }
    }
}

pub(crate) struct RunState(Arc<Mutex<RunRuntime>>);

pub(crate) struct RunShutdownHandle(Arc<Mutex<RunRuntime>>);

pub(crate) fn new_state_pair() -> (RunState, RunShutdownHandle) {
    let inner = Arc::new(Mutex::new(RunRuntime::new()));
    (RunState(Arc::clone(&inner)), RunShutdownHandle(inner))
}

/// 앱 종료 공통 정리 — 확인 다이얼로그가 못 뜨는 종료에서도 고아 dev 서버가 남지 않게
/// 무조건 트리 kill 만은 보장한다(작업방 §10 P1 동형).
pub(crate) fn stop_for_exit(handle: &RunShutdownHandle) {
    if let Ok(mut guard) = handle.0.lock() {
        if let Some(mut child) = guard.child.take() {
            kill_child_tree(&mut child);
        }
        if let Some(server) = guard.static_server.take() {
            server.unblock();
        }
    }
}

impl Drop for RunState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.child.take() {
                kill_child_tree(&mut child);
            }
            if let Some(server) = guard.static_server.take() {
                server.unblock();
            }
        }
    }
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RunOutputEvent {
    run_id: u64,
    /// "install" | "run" — UI 가 "준비 중…"/"실행 중" 단계를 구분한다.
    phase: &'static str,
    stream: &'static str,
    line: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RunStatusEvent {
    run_id: u64,
    /// "installing" | "running" | "done" | "failed" | "stopped".
    status: &'static str,
    exit_code: Option<i32>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RunPreviewReadyEvent {
    run_id: u64,
    /// `http://localhost:PORT` — 프런트가 [미리보기 열기] 버튼으로 open_preview 에 돌려준다.
    url: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RunStatusInfo {
    running: bool,
    run_id: u64,
    /// 탭 복귀 시 [미리보기 열기] 복원용 — 감지됐으면 Some.
    preview_url: Option<String>,
    /// 현재 단계("installing"/"running") — 복원이 진짜 단계를 보이게(install 갭 오표시 방지).
    status: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RunStartInfo {
    run_id: u64,
    command_label: String,
    kind: ProjectKind,
    needs_install: bool,
}

/// 공통 Command 빌더 — install·run 양쪽이 같은 환경/플래그로 spawn 한다.
/// NO_COLOR·FORCE_COLOR: ANSI 색코드 섞임 차단(§9 P1, 포트 정규식·Win cp949 깨짐 예방).
/// Unix setpgid: kill_child_tree 의 killpg 가 npm→node 손자까지 닿게 한다(§9 P0).
fn build_command(exe: &Path, args: &[String], cwd: &Path) -> std::process::Command {
    let mut cmd = std::process::Command::new(exe);
    cmd.args(args);
    cmd.current_dir(cwd);
    cmd.stdin(std::process::Stdio::null());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());
    cmd.env("PATH", augmented_vib_path());
    cmd.env("NO_COLOR", "1");
    cmd.env("FORCE_COLOR", "0");
    hide_console(&mut cmd);
    #[cfg(unix)]
    unsafe {
        use std::os::unix::process::CommandExt;
        cmd.pre_exec(|| {
            libc::setpgid(0, 0);
            Ok(())
        });
    }
    cmd
}

/// port_ready Some(flag) 인 스트림(run 단계·웹/unknown)에서만 포트를 감지한다.
/// flag 는 stdout/stderr 스레드가 공유 — compare_exchange 로 첫 감지 1회만 emit 한다.
/// 감지 시 url 을 shared.preview_url 에도 적어, 탭 이탈 후 run_status 로 복원 가능하게 한다.
fn spawn_output_thread<R: std::io::Read + Send + 'static>(
    reader: R,
    app: tauri::AppHandle,
    shared: Arc<Mutex<RunRuntime>>,
    run_id: u64,
    phase: &'static str,
    stream: &'static str,
    port_ready: Option<Arc<AtomicBool>>,
) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            let Ok(line) = line else { break };
            let line = line.trim_end_matches('\r').to_string();
            if line.is_empty() {
                continue;
            }
            if let Some(flag) = port_ready.as_ref() {
                if !flag.load(Ordering::Relaxed) {
                    if let Some(url) = detect_preview_url(&line) {
                        // 첫 감지만 — 두 스트림이 동시에 잡아도 한 번만 발화.
                        if flag
                            .compare_exchange(false, true, Ordering::SeqCst, Ordering::Relaxed)
                            .is_ok()
                        {
                            // 내 실행일 때만 상태에 저장(새 실행이 점유한 슬롯을 덮지 않게).
                            if let Ok(mut guard) = shared.lock() {
                                if guard.run_id == run_id {
                                    guard.preview_url = Some(url.clone());
                                }
                            }
                            let _ = app.emit("run-preview-ready", RunPreviewReadyEvent { run_id, url });
                        }
                    }
                }
            }
            let _ = app.emit("run-output", RunOutputEvent { run_id, phase, stream, line });
        }
    });
}

enum Registered {
    Ok,
    /// 새 실행으로 교체됐거나 취소가 먼저 들어옴 — child 는 이미 트리 kill 됨.
    Aborted,
    SpawnFailed(String),
}

/// 자식 spawn → (취소 확인 · 점유 토큰 확인 · child 저장)을 **단일 critical section** 으로.
/// 확인과 저장을 두 lock 으로 쪼개면 그 틈의 취소가 추적 불가한 dev 서버를 남긴다(advisor 지적).
#[allow(clippy::too_many_arguments)]
fn spawn_and_register(
    app: &tauri::AppHandle,
    shared: &Arc<Mutex<RunRuntime>>,
    cwd: &Path,
    exe: &Path,
    args: &[String],
    run_id: u64,
    phase: &'static str,
    port_ready: Option<Arc<AtomicBool>>,
) -> Registered {
    let mut child = match build_command(exe, args, cwd).spawn() {
        Ok(c) => c,
        Err(e) => return Registered::SpawnFailed(e.to_string()),
    };
    // stdout/stderr 는 child 를 mutex 로 옮기기 전에 빼둔다.
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    {
        let Ok(mut guard) = shared.lock() else {
            kill_child_tree(&mut child);
            return Registered::Aborted;
        };
        if guard.run_id != run_id || guard.cancelled {
            kill_child_tree(&mut child);
            return Registered::Aborted;
        }
        guard.child = Some(child);
    }
    if let Some(out) = stdout {
        spawn_output_thread(out, app.clone(), Arc::clone(shared), run_id, phase, "stdout", port_ready.clone());
    }
    if let Some(err) = stderr {
        spawn_output_thread(err, app.clone(), Arc::clone(shared), run_id, phase, "stderr", port_ready);
    }
    Registered::Ok
}

enum Polled {
    /// (exit_code, success).
    Exited(Option<i32>, bool),
    /// try_wait 에러 — 종료로 간주.
    Failed,
    /// run_id 가 바뀜(새 실행 점유) — 이 오케스트레이터는 종료 보고 없이 물러난다.
    Superseded,
}

/// child 를 mutex 안에 둔 채 try_wait 폴링 — 취소가 같은 자리에서 kill_child_tree 할 수
/// 있어야 하므로 wait() 로 들고 나가지 않는다(work_room waiter 동형).
fn poll_until_exit(shared: &Arc<Mutex<RunRuntime>>, run_id: u64) -> Polled {
    loop {
        std::thread::sleep(std::time::Duration::from_millis(200));
        let Ok(mut guard) = shared.lock() else { return Polled::Superseded };
        if guard.run_id != run_id {
            return Polled::Superseded;
        }
        let Some(child) = guard.child.as_mut() else {
            return Polled::Failed;
        };
        match child.try_wait() {
            Ok(Some(status)) => {
                guard.child = None;
                return Polled::Exited(status.code(), status.success());
            }
            Ok(None) => {}
            Err(_) => {
                guard.child = None;
                return Polled::Failed;
            }
        }
    }
}

fn is_cancelled(shared: &Arc<Mutex<RunRuntime>>) -> bool {
    shared.lock().map(|g| g.cancelled).unwrap_or(true)
}

/// 진행 단계 라벨 기록 — 내 실행일 때만(run_status 복원이 진짜 단계를 보이게).
fn set_status_label(shared: &Arc<Mutex<RunRuntime>>, run_id: u64, label: &'static str) {
    if let Ok(mut g) = shared.lock() {
        if g.run_id == run_id {
            g.status_label = Some(label);
        }
    }
}

/// 종료 보고 + 슬롯 해제 — 내 실행(run_id 일치)일 때만 active/child 를 비운다
/// (이미 새 실행이 점유했으면 건드리지 않는다).
fn finish(
    app: &tauri::AppHandle,
    shared: &Arc<Mutex<RunRuntime>>,
    run_id: u64,
    status: &'static str,
    exit_code: Option<i32>,
) {
    let mut owned = false;
    if let Ok(mut guard) = shared.lock() {
        if guard.run_id == run_id {
            guard.active = false;
            guard.child = None;
            guard.preview_url = None;
            guard.status_label = None;
            owned = true;
        }
    }
    // dev 서버가 떠난 미리보기 창은 stale — 내 실행의 종료일 때만 정리한다(새 실행이
    // 점유한 슬롯이면 그 실행의 미리보기를 닫지 않는다).
    if owned {
        close_preview_window(app);
    }
    let _ = app.emit("run-status", RunStatusEvent { run_id, status, exit_code });
}

#[allow(clippy::too_many_arguments)]
fn spawn_orchestrator(
    app: tauri::AppHandle,
    shared: Arc<Mutex<RunRuntime>>,
    cwd: std::path::PathBuf,
    npm: std::path::PathBuf,
    run_exe: std::path::PathBuf,
    run_args: Vec<String>,
    run_id: u64,
    needs_install: bool,
    detect_port: bool,
) {
    std::thread::spawn(move || {
        // ── INSTALL 단계 (node_modules 없을 때 1회) ──
        if needs_install {
            set_status_label(&shared, run_id, "installing");
            let _ = app.emit(
                "run-status",
                RunStatusEvent { run_id, status: "installing", exit_code: None },
            );
            match spawn_and_register(&app, &shared, &cwd, &npm, &["install".into()], run_id, "install", None) {
                Registered::Ok => {}
                Registered::Aborted => {
                    finish(&app, &shared, run_id, "stopped", None);
                    return;
                }
                Registered::SpawnFailed(e) => {
                    let _ = app.emit(
                        "run-output",
                        RunOutputEvent {
                            run_id,
                            phase: "install",
                            stream: "stderr",
                            line: format!("[vibelign] 설치를 시작하지 못했어요: {e}"),
                        },
                    );
                    finish(&app, &shared, run_id, "failed", None);
                    return;
                }
            }
            match poll_until_exit(&shared, run_id) {
                Polled::Exited(_, true) => {}
                Polled::Exited(code, false) => {
                    if is_cancelled(&shared) {
                        finish(&app, &shared, run_id, "stopped", None);
                    } else {
                        finish(&app, &shared, run_id, "failed", code);
                    }
                    return;
                }
                Polled::Failed => {
                    finish(&app, &shared, run_id, "failed", None);
                    return;
                }
                Polled::Superseded => return,
            }
            // 설치 중 취소가 들어왔으면 실행 단계로 넘어가지 않는다.
            if is_cancelled(&shared) {
                finish(&app, &shared, run_id, "stopped", None);
                return;
            }
        }

        // ── RUN 단계 (장기 dev 프로세스) ──
        // 웹/unknown 만 포트 감지 — electron 은 자체 OS 창이라 webview 불필요.
        let port_ready = detect_port.then(|| Arc::new(AtomicBool::new(false)));
        match spawn_and_register(&app, &shared, &cwd, &run_exe, &run_args, run_id, "run", port_ready) {
            Registered::Ok => {
                set_status_label(&shared, run_id, "running");
                let _ = app.emit(
                    "run-status",
                    RunStatusEvent { run_id, status: "running", exit_code: None },
                );
            }
            Registered::Aborted => {
                finish(&app, &shared, run_id, "stopped", None);
                return;
            }
            Registered::SpawnFailed(e) => {
                let _ = app.emit(
                    "run-output",
                    RunOutputEvent {
                        run_id,
                        phase: "run",
                        stream: "stderr",
                        line: format!("[vibelign] 실행을 시작하지 못했어요: {e}"),
                    },
                );
                finish(&app, &shared, run_id, "failed", None);
                return;
            }
        }
        match poll_until_exit(&shared, run_id) {
            Polled::Exited(code, success) => {
                if is_cancelled(&shared) {
                    finish(&app, &shared, run_id, "stopped", None);
                } else if success {
                    // dev 서버가 0 으로 정상 종료(electron 창 닫음 등).
                    finish(&app, &shared, run_id, "done", code);
                } else {
                    // 비정상 종료 — 보통 시작 실패(포트 점유·문법 에러). M3 가 작업방으로 넘긴다.
                    finish(&app, &shared, run_id, "failed", code);
                }
            }
            Polled::Failed => finish(&app, &shared, run_id, "failed", None),
            Polled::Superseded => {}
        }
    });
}

/// package.json → 실행 레시피(파일 I/O 래퍼). UI 가 실행 전 타입을 보여줄 때 쓴다.
#[tauri::command]
pub(crate) fn run_detect(cwd: String) -> Option<RunRecipe> {
    let cwd_path = Path::new(&cwd);
    // 1순위 — package.json dev/start 레시피.
    if let Ok(content) = std::fs::read_to_string(cwd_path.join("package.json")) {
        if let Some(recipe) = detect_run_recipe(&content) {
            return Some(recipe);
        }
    }
    // 2순위 — package.json 이 없거나 레시피가 안 나오면, index.html 만으로 정적 미리보기.
    // 초보가 만든 단일 HTML 앱(빌드/노드 없음)을 임베드 서버로 서빙한다.
    if cwd_path.join("index.html").is_file() {
        return Some(RunRecipe {
            kind: ProjectKind::StaticWeb,
            program: RunProgram::Static,
            command_label: "정적 미리보기 (HTML)".to_string(),
            preview: PreviewKind::Webview { default_port: None },
        });
    }
    None
}

#[tauri::command]
pub(crate) fn run_start(
    app: tauri::AppHandle,
    state: tauri::State<RunState>,
    work: tauri::State<work_room::WorkRoomState>,
    cwd: String,
) -> Result<RunStartInfo, String> {
    // §5 상호배제(best-effort) — 작업방 AI 가 같은 워킹트리를 고치는 중이면 실행을 막는다.
    // 두 상태가 별도 락이라 동시 클릭의 microsecond TOCTOU 는 못 막지만(단일 사용자 GUI 라
    // 사실상 도달 불가, 실패해도 프로세스 2개일 뿐 손상 아님), 사용자 흐름상의 충돌은 막는다.
    if work_room::is_busy(&work) {
        return Err("작업방에서 AI가 작업 중이에요. 끝난 뒤 실행해 주세요.".into());
    }
    let cwd_path = std::path::PathBuf::from(&cwd);
    let recipe = run_detect(cwd.clone()).ok_or_else(|| {
        "실행 방법을 못 찾았어요. package.json 의 dev/start 스크립트 또는 index.html 이 필요해요."
            .to_string()
    })?;

    // ── 정적 HTML(index.html, package.json 없음): 임베드 tiny_http 서버 ──
    // npm/노드 없이 cwd 를 직접 서빙하고 webview 로 미리보기. 외부 프로세스가 없으므로
    // spawn_orchestrator 경로를 타지 않고 여기서 run_id 점유·서버 스레드·이벤트를 직접 만든다.
    if recipe.kind == ProjectKind::StaticWeb {
        return start_static_preview(app, &state, cwd_path, recipe);
    }

    // npm 은 install·npm 실행 양쪽에 필요. 미설치 시 온보딩으로 안내(§9 P1).
    let npm = find_executable("npm")
        .ok_or_else(|| "Node.js(npm)가 필요해요. 온보딩에서 Node 를 먼저 설치해 주세요.".to_string())?;
    let run_exe = match &recipe.program {
        RunProgram::Npm(_) => npm.clone(),
        RunProgram::Npx(_) => find_executable("npx")
            .ok_or_else(|| "npx 를 찾을 수 없어요. Node.js 설치를 확인해 주세요.".to_string())?,
        // StaticWeb 은 위에서 start_static_preview 로 early-return 되어 여기 도달하지 않는다.
        RunProgram::Static => unreachable!("StaticWeb is handled before the npm spawn path"),
    };
    let run_args = recipe.program.args().to_vec();

    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.active {
        return Err("이미 실행 중이에요. 중지한 뒤 다시 시작해 주세요.".into());
    }
    let run_id = guard.run_id + 1;
    guard.run_id = run_id;
    guard.cancelled = false;
    guard.active = true;
    guard.child = None;
    guard.preview_url = None;
    guard.status_label = None;
    drop(guard);

    let needs_install = !cwd_path.join("node_modules").is_dir();
    // electron 은 자체 OS 창 — webview 포트 감지 대상이 아니다(§4·§5).
    let detect_port = recipe.kind != ProjectKind::Electron;
    spawn_orchestrator(
        app,
        Arc::clone(&state.0),
        cwd_path,
        npm,
        run_exe,
        run_args,
        run_id,
        needs_install,
        detect_port,
    );
    Ok(RunStartInfo {
        run_id,
        command_label: recipe.command_label,
        kind: recipe.kind,
        needs_install,
    })
}

// ─── 정적 HTML 임베드 서버 (tiny_http, child 없는 실행) ─────────────────────────

/// 정적 HTML 미리보기 시작 — 127.0.0.1:0(임의 포트)에 tiny_http 를 바인드하고 cwd 를
/// 서빙하는 스레드를 띄운 뒤 webview 를 연다. 외부 프로세스(child)가 없으므로 종료 보고
/// (stopped)는 서버가 unblock 된 뒤 서빙 스레드가 직접 emit 한다.
fn start_static_preview(
    app: tauri::AppHandle,
    state: &tauri::State<RunState>,
    cwd: std::path::PathBuf,
    recipe: RunRecipe,
) -> Result<RunStartInfo, String> {
    let server = Arc::new(tiny_http::Server::http("127.0.0.1:0").map_err(|e| e.to_string())?);
    let port = server
        .server_addr()
        .to_ip()
        .map(|addr| addr.port())
        .ok_or_else(|| "미리보기 포트를 할당하지 못했어요.".to_string())?;
    let url = format!("http://localhost:{port}");

    // run_id 점유 — npm 경로와 동일한 토큰 의미(run_status/stop 일관성). 동기로
    // active/preview_url/status_label 을 세팅해 탭 복귀(run_status) 복원이 바로 동작한다.
    let run_id = {
        let mut guard = state.0.lock().map_err(|e| e.to_string())?;
        if guard.active {
            return Err("이미 실행 중이에요. 중지한 뒤 다시 시작해 주세요.".into());
        }
        let run_id = guard.run_id + 1;
        guard.run_id = run_id;
        guard.cancelled = false;
        guard.active = true;
        guard.child = None;
        guard.preview_url = Some(url.clone());
        guard.status_label = Some("running");
        guard.static_server = Some(Arc::clone(&server));
        run_id
    };

    // 서빙 스레드 — incoming_requests 가 unblock 될 때까지 cwd 의 파일을 서빙한다.
    // 루프가 끝나면(중지/앱종료) 내 실행일 때만 슬롯을 비우고 "stopped" 를 보고한다.
    let serve_app = app.clone();
    let shared = Arc::clone(&state.0);
    std::thread::spawn(move || {
        for request in server.incoming_requests() {
            serve_static_request(&cwd, request);
        }
        let mut owned = false;
        if let Ok(mut guard) = shared.lock() {
            if guard.run_id == run_id {
                guard.active = false;
                guard.preview_url = None;
                guard.status_label = None;
                guard.static_server = None;
                owned = true;
            }
        }
        if owned {
            close_preview_window(&serve_app);
            let _ = serve_app
                .emit("run-status", RunStatusEvent { run_id, status: "stopped", exit_code: None });
        }
    });

    // run-status(running)+run-preview-ready 는 짧은 지연 후 emit — runStart 응답이 프런트에서
    // 먼저 처리돼 status 가 'starting' 으로 덮이는 경쟁을 피한다(npm 경로는 orchestrator
    // 스레드의 자연 지연으로 이 문제가 없다). 위의 동기 세팅 덕에 run_status 복원은 무관.
    let ready_app = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_millis(150));
        let _ = ready_app
            .emit("run-status", RunStatusEvent { run_id, status: "running", exit_code: None });
        let _ = ready_app.emit("run-preview-ready", RunPreviewReadyEvent { run_id, url });
    });

    Ok(RunStartInfo {
        run_id,
        command_label: recipe.command_label,
        kind: recipe.kind,
        needs_install: false,
    })
}

/// 확장자 → Content-Type. 정적 미리보기에 흔한 타입만 명시, 나머지는 octet-stream.
fn content_type_for(path: &Path) -> &'static str {
    match path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_ascii_lowercase())
        .as_deref()
    {
        Some("html") | Some("htm") => "text/html; charset=utf-8",
        Some("js") | Some("mjs") => "text/javascript; charset=utf-8",
        Some("css") => "text/css; charset=utf-8",
        Some("json") => "application/json; charset=utf-8",
        Some("svg") => "image/svg+xml",
        Some("png") => "image/png",
        Some("jpg") | Some("jpeg") => "image/jpeg",
        Some("gif") => "image/gif",
        Some("ico") => "image/x-icon",
        Some("wasm") => "application/wasm",
        Some("txt") => "text/plain; charset=utf-8",
        _ => "application/octet-stream",
    }
}

/// 상태코드 응답(403/404 등) — Request 를 소비한다.
fn respond_status(request: tiny_http::Request, code: u16, body: &str) {
    let response =
        tiny_http::Response::from_string(body).with_status_code(tiny_http::StatusCode(code));
    let _ = request.respond(response);
}

/// 정적 서버의 한 요청 처리 — cwd(root) 안의 파일만 서빙한다. path-traversal 2중 방어:
/// (1) 경로 세그먼트의 ".." 거부, (2) canonicalize 후 root 내부 여부 확인(심볼릭 링크 포함).
fn serve_static_request(root: &Path, request: tiny_http::Request) {
    // request.url() 차용을 끊기 위해 즉시 owned 로 — 아래에서 request 를 소비하므로.
    let raw = request.url().to_string();
    let path_part = raw.split(['?', '#']).next().unwrap_or("/");
    let rel = path_part.trim_start_matches('/');
    let rel = if rel.is_empty() { "index.html" } else { rel };

    // (1) ".." 세그먼트 거부.
    if rel.split('/').any(|seg| seg == "..") {
        respond_status(request, 403, "Forbidden");
        return;
    }
    let candidate = root.join(rel);
    // (2) canonicalize 후 root 내부 확인.
    let (Ok(canon_root), Ok(canon_path)) = (root.canonicalize(), candidate.canonicalize()) else {
        respond_status(request, 404, "Not Found");
        return;
    };
    if !canon_path.starts_with(&canon_root) || !canon_path.is_file() {
        respond_status(request, 404, "Not Found");
        return;
    }
    match std::fs::read(&canon_path) {
        Ok(bytes) => {
            let mut response = tiny_http::Response::from_data(bytes);
            if let Ok(header) = tiny_http::Header::from_bytes(
                &b"Content-Type"[..],
                content_type_for(&canon_path).as_bytes(),
            ) {
                response = response.with_header(header);
            }
            let _ = request.respond(response);
        }
        Err(_) => respond_status(request, 404, "Not Found"),
    }
}

/// 취소 코어 — child 를 자리에 둔 채 트리 kill 만 한다. stopped 보고는 오케스트레이터가
/// poll 로 회수하며 일원화한다(work_room cancel_current 동형). 반환: 점유 중이었는지.
fn cancel_current(runtime: &Arc<Mutex<RunRuntime>>) -> bool {
    let Ok(mut guard) = runtime.lock() else { return false };
    if !guard.active {
        return false;
    }
    guard.cancelled = true;
    if let Some(child) = guard.child.as_mut() {
        kill_child_tree(child);
    }
    // 정적 실행: child 가 없고 서버 스레드가 incoming_requests 에 묶여 있다.
    // unblock 하면 그 루프가 끝나며 슬롯 해제 + "stopped" 보고를 스스로 수행한다.
    if let Some(server) = guard.static_server.take() {
        server.unblock();
    }
    true
}

#[tauri::command]
pub(crate) fn run_stop(state: tauri::State<RunState>) -> bool {
    cancel_current(&state.0)
}

#[tauri::command]
pub(crate) fn run_status(state: tauri::State<RunState>) -> RunStatusInfo {
    state
        .0
        .lock()
        .map(|g| RunStatusInfo {
            running: g.active,
            run_id: g.run_id,
            preview_url: g.preview_url.clone(),
            status: g.status_label.map(|s| s.to_string()),
        })
        .unwrap_or(RunStatusInfo { running: false, run_id: 0, preview_url: None, status: None })
}

/// 러너가 점유 중인지 — 작업방과의 §5 상호배제용(work_run 이 시작 전 읽는다).
pub(crate) fn is_busy(state: &RunState) -> bool {
    state.0.lock().map(|g| g.active).unwrap_or(false)
}

// ─── 미리보기 webview (Tauri v2 별도 창, §5) ────────────────────────────────────

fn close_preview_window(app: &tauri::AppHandle) {
    use tauri::Manager;
    if let Some(win) = app.get_webview_window(PREVIEW_LABEL) {
        let _ = win.close();
    }
}

/// 미리보기 창 열기/포커스 — 프런트의 [미리보기 열기] 버튼이 run-preview-ready 의 url 로
/// 호출한다. 이미 있으면 그 창을 해당 url 로 이동·포커스(중복 창 방지). 메인 앱과
/// 생명주기를 분리한 별도 창이라 사용자가 따로 옮기거나 닫을 수 있다(§5).
#[tauri::command]
pub(crate) fn open_preview(app: tauri::AppHandle, url: String) -> Result<(), String> {
    use tauri::Manager;
    let parsed = validate_local_url(&url)?;
    if let Some(win) = app.get_webview_window(PREVIEW_LABEL) {
        win.navigate(parsed).map_err(|e| e.to_string())?;
        let _ = win.set_focus();
        return Ok(());
    }
    tauri::WebviewWindowBuilder::new(&app, PREVIEW_LABEL, tauri::WebviewUrl::External(parsed))
        .title("미리보기 — VibeLign")
        .inner_size(1100.0, 800.0)
        // 방어심층: dev 페이지(사용자 임의 코드)가 localhost 밖 외부 origin 으로 스스로
        // 이동하는 것을 막는다. 초기 URL 은 이미 로컬이라 통과하고, HMR 의 ws:// 는
        // navigation 이 아니라 영향 없다. capability 가 이미 이 창에 백엔드 권한을 안 주지만
        // 한 겹 더 — 안전 도구 정체성(§8).
        .on_navigation(|url| {
            matches!(url.scheme(), "http" | "https")
                && matches!(
                    url.host_str(),
                    Some("localhost") | Some("127.0.0.1") | Some("0.0.0.0")
                )
        })
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
pub(crate) fn close_preview(app: tauri::AppHandle) {
    close_preview_window(&app);
}

#[cfg(test)]
mod runner_tests {
    use super::{cancel_current, new_state_pair, stop_for_exit};

    #[test]
    fn state_pair_shares_runtime_between_managed_state_and_exit_handle() {
        let (state, shutdown) = new_state_pair();
        {
            let mut guard = state.0.lock().expect("run state lock");
            guard.run_id = 7;
            guard.active = true;
        }
        let guard = shutdown.0.lock().expect("run shutdown lock");
        assert_eq!(guard.run_id, 7);
        assert!(guard.active);
    }

    #[test]
    fn cancel_without_active_run_reports_false() {
        let (state, _shutdown) = new_state_pair();
        assert!(!cancel_current(&state.0));
    }

    #[cfg(unix)]
    #[test]
    fn cancel_kills_running_child_and_marks_cancelled() {
        let (state, _shutdown) = new_state_pair();
        let child = std::process::Command::new("sleep").arg("30").spawn().expect("spawn sleep");
        {
            let mut guard = state.0.lock().expect("run state lock");
            guard.active = true;
            guard.child = Some(child);
        }
        assert!(cancel_current(&state.0));
        let mut guard = state.0.lock().expect("run state lock");
        assert!(guard.cancelled);
        let status = guard
            .child
            .as_mut()
            .expect("child stays until poll reaps")
            .try_wait()
            .expect("try_wait after kill");
        assert!(status.is_some(), "child must be dead after cancel");
    }

    #[cfg(unix)]
    #[test]
    fn stop_for_exit_kills_child_registered_in_shared_runtime() {
        let (state, shutdown) = new_state_pair();
        let child = std::process::Command::new("sleep").arg("30").spawn().expect("spawn sleep");
        {
            let mut guard = state.0.lock().expect("run state lock");
            guard.child = Some(child);
        }
        stop_for_exit(&shutdown);
        let guard = state.0.lock().expect("run state lock");
        assert!(guard.child.is_none());
    }
}

#[cfg(test)]
mod detect_tests {
    use super::*;

    fn recipe(json: &str) -> RunRecipe {
        detect_run_recipe(json).expect("recipe")
    }

    #[test]
    fn electron_with_start_script_uses_npm_start_external_window() {
        let r = recipe(r#"{"dependencies":{"electron":"^30"},"scripts":{"start":"electron ."}}"#);
        assert_eq!(r.kind, ProjectKind::Electron);
        assert_eq!(r.program, RunProgram::Npm(vec!["start".into()]));
        assert_eq!(r.command_label, "npm start");
        assert_eq!(r.preview, PreviewKind::ExternalWindow);
    }

    #[test]
    fn electron_without_start_script_falls_back_to_npx_electron_dot() {
        let r = recipe(r#"{"devDependencies":{"electron":"^30"}}"#);
        assert_eq!(r.kind, ProjectKind::Electron);
        assert_eq!(r.program, RunProgram::Npx(vec!["electron".into(), ".".into()]));
        assert_eq!(r.command_label, "npx electron .");
    }

    #[test]
    fn electron_wins_over_vite_and_dev_script() {
        // 우선순위: electron 의존성이 있으면 scripts.dev·vite 가 있어도 electron(§4).
        let r = recipe(
            r#"{"dependencies":{"electron":"^30"},"devDependencies":{"vite":"^5"},"scripts":{"dev":"vite","start":"electron ."}}"#,
        );
        assert_eq!(r.kind, ProjectKind::Electron);
    }

    #[test]
    fn vite_in_dev_dependencies_is_detected_as_web_npm_run_dev() {
        // vite 는 거의 devDependencies — dep_present 가 양쪽을 봐야 한다(핵심 회귀).
        let r = recipe(r#"{"devDependencies":{"vite":"^5"},"scripts":{"dev":"vite"}}"#);
        assert_eq!(r.kind, ProjectKind::Web);
        assert_eq!(r.program, RunProgram::Npm(vec!["run".into(), "dev".into()]));
        assert_eq!(r.command_label, "npm run dev");
        assert_eq!(r.preview, PreviewKind::Webview { default_port: None });
    }

    #[test]
    fn next_detected_with_default_port_3000() {
        let r = recipe(r#"{"dependencies":{"next":"^14"},"scripts":{"dev":"next dev"}}"#);
        assert_eq!(r.kind, ProjectKind::Web);
        assert_eq!(r.program, RunProgram::Npm(vec!["run".into(), "dev".into()]));
        assert_eq!(r.preview, PreviewKind::Webview { default_port: Some(3000) });
    }

    #[test]
    fn react_scripts_detected_as_npm_start_port_3000() {
        let r = recipe(r#"{"dependencies":{"react-scripts":"5"},"scripts":{"start":"react-scripts start"}}"#);
        assert_eq!(r.kind, ProjectKind::Web);
        assert_eq!(r.program, RunProgram::Npm(vec!["start".into()]));
        assert_eq!(r.preview, PreviewKind::Webview { default_port: Some(3000) });
    }

    #[test]
    fn next_takes_priority_over_react_scripts() {
        let r = recipe(r#"{"dependencies":{"next":"^14","react-scripts":"5"},"scripts":{"dev":"next dev","start":"x"}}"#);
        // next 가 표에서 위 — npm run dev 여야 한다.
        assert_eq!(r.program, RunProgram::Npm(vec!["run".into(), "dev".into()]));
    }

    #[test]
    fn generic_dev_script_without_known_framework_is_web() {
        let r = recipe(r#"{"scripts":{"dev":"node server.js"}}"#);
        assert_eq!(r.kind, ProjectKind::Web);
        assert_eq!(r.program, RunProgram::Npm(vec!["run".into(), "dev".into()]));
        assert_eq!(r.preview, PreviewKind::Webview { default_port: None });
    }

    #[test]
    fn only_start_script_is_unknown_log_only() {
        let r = recipe(r#"{"scripts":{"start":"node index.js"}}"#);
        assert_eq!(r.kind, ProjectKind::Unknown);
        assert_eq!(r.program, RunProgram::Npm(vec!["start".into()]));
        assert_eq!(r.preview, PreviewKind::LogOnly);
    }

    #[test]
    fn dev_script_beats_start_only_branch() {
        // dev 와 start 둘 다 있으면 dev(웹) 가 먼저(§4 5행 > 6행).
        let r = recipe(r#"{"scripts":{"dev":"vite","start":"serve"}}"#);
        assert_eq!(r.kind, ProjectKind::Web);
        assert_eq!(r.program, RunProgram::Npm(vec!["run".into(), "dev".into()]));
    }

    #[test]
    fn no_deps_no_scripts_returns_none() {
        assert!(detect_run_recipe(r#"{"name":"x","version":"1.0.0"}"#).is_none());
    }

    #[test]
    fn empty_scripts_object_returns_none() {
        assert!(detect_run_recipe(r#"{"scripts":{}}"#).is_none());
    }

    #[test]
    fn invalid_json_returns_none() {
        assert!(detect_run_recipe("{ not json").is_none());
        assert!(detect_run_recipe("").is_none());
    }

    // ─── 정적 HTML 감지 (run_detect, 파일 I/O) ────────────────────────────────────

    #[test]
    fn index_html_without_package_json_is_static_web() {
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("index.html"), "<h1>hi</h1>").expect("write index.html");
        let r = run_detect(dir.path().to_string_lossy().to_string()).expect("static recipe");
        assert_eq!(r.kind, ProjectKind::StaticWeb);
        assert_eq!(r.program, RunProgram::Static);
        assert_eq!(r.command_label, "정적 미리보기 (HTML)");
        assert_eq!(r.preview, PreviewKind::Webview { default_port: None });
    }

    #[test]
    fn package_json_recipe_wins_over_index_html() {
        // dev 스크립트가 있으면 정적 폴백이 아니라 web 레시피여야 한다(1순위).
        let dir = tempfile::tempdir().expect("tempdir");
        std::fs::write(dir.path().join("index.html"), "<h1>hi</h1>").expect("write");
        std::fs::write(dir.path().join("package.json"), r#"{"scripts":{"dev":"vite"}}"#)
            .expect("write");
        let r = run_detect(dir.path().to_string_lossy().to_string()).expect("recipe");
        assert_eq!(r.kind, ProjectKind::Web);
    }

    #[test]
    fn empty_dir_without_package_json_or_index_returns_none() {
        let dir = tempfile::tempdir().expect("tempdir");
        assert!(run_detect(dir.path().to_string_lossy().to_string()).is_none());
    }

    // ─── 포트 감지 ──────────────────────────────────────────────────────────────

    #[test]
    fn vite_local_line_detected() {
        assert_eq!(
            detect_preview_url("  ➜  Local:   http://localhost:5173/"),
            Some("http://localhost:5173".to_string())
        );
    }

    #[test]
    fn next_local_line_detected() {
        assert_eq!(
            detect_preview_url("   - Local:        http://localhost:3000"),
            Some("http://localhost:3000".to_string())
        );
    }

    #[test]
    fn cra_local_line_detected() {
        assert_eq!(
            detect_preview_url("  Local:            http://localhost:3000"),
            Some("http://localhost:3000".to_string())
        );
    }

    #[test]
    fn loopback_ip_normalized_to_localhost() {
        assert_eq!(
            detect_preview_url("Server running at http://127.0.0.1:8080/"),
            Some("http://localhost:8080".to_string())
        );
    }

    #[test]
    fn any_interface_address_normalized_to_localhost() {
        assert_eq!(
            detect_preview_url("App listening on http://0.0.0.0:4000"),
            Some("http://localhost:4000".to_string())
        );
    }

    #[test]
    fn local_preferred_over_network_address() {
        // vite 는 Local 과 Network 을 같은 블록에 찍는다 — 한 줄에 섞여도 로컬을 고른다.
        assert_eq!(
            detect_preview_url("Local: http://localhost:5173/  Network: http://192.168.0.5:5173/"),
            Some("http://localhost:5173".to_string())
        );
    }

    #[test]
    fn network_only_line_is_ignored() {
        assert!(detect_preview_url("  ➜  Network: http://192.168.0.5:5173/").is_none());
    }

    #[test]
    fn line_without_url_is_none() {
        assert!(detect_preview_url("VITE v5.0.0  ready in 320 ms").is_none());
    }

    #[test]
    fn localhost_without_port_is_none() {
        assert!(detect_preview_url("open http://localhost/ now").is_none());
    }

    #[test]
    fn validate_local_url_accepts_localhost_rejects_external() {
        assert!(validate_local_url("http://localhost:5173").is_ok());
        assert!(validate_local_url("http://127.0.0.1:3000").is_ok());
        assert!(validate_local_url("https://evil.example.com").is_err());
        assert!(validate_local_url("file:///etc/passwd").is_err());
        assert!(validate_local_url("not a url").is_err());
    }
}
// === ANCHOR: RUN_PREVIEW_END ===
