// === ANCHOR: WORK_ROOM_START ===
//! 작업방 Tier 1 — 범용 CLI 스트리밍 러너 (plans/2026-06-12-작업방-tier1-design.md §3·§8-1).
//! watch.rs 수명주기(프로세스 그룹·트리 kill) + vib_bridge 라인 스트리밍 emit 의 결합.
//!
//! 설계 불변식 (기획안 §9·§10 P0):
//! - 지시문은 argv 가 아니라 **stdin** 으로 전달 — Windows .cmd 셔임의 cmd.exe 파싱
//!   mangling 과 ~8191자 라인 제한을 회피한다.
//! - 취소·종료는 반드시 **프로세스 트리 전체** kill — plain `child.kill()` 은 .cmd 셔임의
//!   node 손자를 살려둬 "취소했는데 에이전트가 계속 파일을 고치는" 사고가 난다.
//! - 타임아웃 없음 — 작업 길이는 예측 불가. 출구는 정상 종료·취소·앱 종료뿐
//!   (idle 경고는 UI 가 work-output 타임스탬프로 판단).
//! - 동시 실행 1개 — 두 에이전트가 같은 워킹트리를 고치면 체크포인트·guard 기준점 오염.

use std::io::{BufRead, BufReader, Write};
use std::sync::{Arc, Mutex};

use serde::Serialize;
use tauri::Emitter;

use super::planning_persona::find_executable;
use super::platform::{augmented_vib_path, hide_console};
use super::run_preview;
use super::watch::kill_watch_child as kill_child_tree;

struct WorkRoomRuntime {
    child: Option<std::process::Child>,
    /// 단조 증가 실행 id — 이벤트 수신측이 이전 실행의 잔여 라인을 걸러낼 기준.
    run_id: u64,
    /// 취소 요청 여부 — waiter 가 종료 상태를 cancelled 로 보고하게 한다.
    cancelled: bool,
    /// 실행별 임시 MCP 설정 파일 — waiter 가 종료 시 정리한다.
    mcp_config: Option<std::path::PathBuf>,
    /// 실행 로그 파일 핸들 — waiter 가 종료 메타를 적고 닫는다.
    run_log: Option<Arc<Mutex<std::fs::File>>>,
}

impl WorkRoomRuntime {
    fn new() -> Self {
        Self { child: None, run_id: 0, cancelled: false, mcp_config: None, run_log: None }
    }
}

pub(crate) struct WorkRoomState(Arc<Mutex<WorkRoomRuntime>>);

pub(crate) struct WorkRoomShutdownHandle(Arc<Mutex<WorkRoomRuntime>>);

pub(crate) fn new_state_pair() -> (WorkRoomState, WorkRoomShutdownHandle) {
    let inner = Arc::new(Mutex::new(WorkRoomRuntime::new()));
    (WorkRoomState(Arc::clone(&inner)), WorkRoomShutdownHandle(inner))
}

/// 작업방이 실행 중인지 — 실행해보기 러너와의 §5 상호배제용(run_start 가 시작 전 읽는다).
pub(crate) fn is_busy(state: &WorkRoomState) -> bool {
    state.0.lock().map(|g| g.child.is_some()).unwrap_or(false)
}

/// 앱 종료 경로 공통 정리 — 확인 다이얼로그가 못 뜨는 종료(로그오프 등)에서도
/// 고아 에이전트가 남지 않게 무조건 트리 kill 만은 보장한다(§10 P1).
pub(crate) fn stop_for_exit(handle: &WorkRoomShutdownHandle) {
    if let Ok(mut guard) = handle.0.lock() {
        if let Some(mut child) = guard.child.take() {
            kill_child_tree(&mut child);
        }
    }
}

impl Drop for WorkRoomState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.child.take() {
                kill_child_tree(&mut child);
            }
        }
    }
}

/// 프로바이더별 헤드리스 어댑터. 지시문은 모든 CLI 공통으로 stdin 으로 들어간다(§10 P0).
/// MVP 는 코딩 에이전트로 검증된 CLI 만 연다(기획안 §1). 위험 플래그 금지(기획안 §3).
struct WorkAdapter {
    executable: &'static str,
    args: &'static [&'static str],
    /// --mcp-config 류 주입 인자를 이해하는 CLI 만 true — codex 는 설정 체계(-c TOML)가
    /// 달라 MVP 미주입. 사후 guard(M3)가 안전망이고, 어댑터별 주입은 후속.
    mcp_injection: bool,
    /// 테스트 실행 화이트리스트(2026-06-12 결정) — acceptEdits 는 편집만 자동 승인이라
    /// 헤드리스에서 에이전트가 자기 코드를 테스트하지 못했다("코드는 썼지만 실행 검증
    /// 불가"). 정확히 테스트 명령만 허용 — 그 외 셸 명령은 여전히 차단된다.
    test_allowlist: &'static [&'static str],
}

fn work_adapter(provider: &str) -> Option<WorkAdapter> {
    match provider {
        // claude -p 는 인자 프롬프트가 없으면 stdin 을 읽는다(EOF 필요).
        // stream-json 은 print 모드에서 --verbose 가 있어야 동작하는 CLI 제약.
        // acceptEdits: 워크스페이스 내 편집만 자동 승인.
        "claude" => Some(WorkAdapter {
            executable: "claude",
            args: &["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits"],
            mcp_injection: true,
            // 정확형 + 접두형(:* = 인자 허용) 쌍 — npm test / node --test 만.
            test_allowlist: &[
                "Bash(npm test)",
                "Bash(npm test:*)",
                "Bash(node --test)",
                "Bash(node --test:*)",
            ],
        }),
        // exec 는 stdin 지시문을 공식 지원(2026-06-12 실검증, codex-cli 0.139).
        // workspace-write: 워크스페이스 한정 쓰기. skip-git-repo-check: 비-git 프로젝트
        // 지원(가이드 스펙 §3.1 정합). --json: JSONL 이벤트(streamJson.ts 가 해석).
        // codex 는 자체 샌드박스(workspace-write)가 명령 실행을 워크스페이스 한정으로
        // 이미 허용·격리한다 — 별도 화이트리스트 불필요.
        "codex" => Some(WorkAdapter {
            executable: "codex",
            args: &["exec", "--json", "--sandbox", "workspace-write", "--skip-git-repo-check"],
            mcp_injection: false,
            test_allowlist: &[],
        }),
        _ => None,
    }
}

// ─── 실행 로그 영속 ─────────────────────────────────────────────────────────────
// 앱 재시작 후에도 "지난 실행"을 볼 수 있게 raw 라인을 프로젝트의
// .vibelign/logs/work-room-last.jsonl 에 남긴다(마지막 1회분 — 알람앱 트라이얼 요구).
// raw 보존 이유: 해석(streamJson.ts)은 프런트 몫이라 파서가 좋아져도 과거 로그에 적용된다.
// .vibelign/ 은 guard·가이드 신호의 무시 prefix 라 변경 감지를 오염시키지 않는다.

const RUN_LOG_FILE: &str = "work-room-last.jsonl";
/// 복원 시 읽는 라인 상한 — 긴 실행에서도 UI·메모리를 보호한다(앞부분부터 버림).
const RUN_LOG_READ_CAP: usize = 2000;

fn unix_now() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

fn run_log_path(cwd: &std::path::Path) -> std::path::PathBuf {
    cwd.join(".vibelign").join("logs").join(RUN_LOG_FILE)
}

fn open_run_log(
    cwd: &std::path::Path,
    provider: &str,
    plan_path: Option<&str>,
) -> Option<Arc<Mutex<std::fs::File>>> {
    use std::io::Write;
    let path = run_log_path(cwd);
    std::fs::create_dir_all(path.parent()?).ok()?;
    let mut file = std::fs::File::create(&path).ok()?;
    // planPath: "이 기획안은 이미 실행 완료" 재실행 안내의 매칭 키(불필요 토큰 소모 방지).
    let meta = serde_json::json!({
        "meta": { "provider": provider, "startedAt": unix_now(), "planPath": plan_path }
    });
    writeln!(file, "{meta}").ok()?;
    Some(Arc::new(Mutex::new(file)))
}

fn append_log_line(log: &Option<Arc<Mutex<std::fs::File>>>, stream: &str, line: &str) {
    use std::io::Write;
    if let Some(log) = log {
        if let Ok(mut f) = log.lock() {
            let _ = writeln!(f, "{}", serde_json::json!({ "stream": stream, "line": line }));
        }
    }
}

fn append_log_meta(log: Option<Arc<Mutex<std::fs::File>>>, status: &str, exit_code: Option<i32>) {
    use std::io::Write;
    if let Some(log) = log {
        if let Ok(mut f) = log.lock() {
            let meta = serde_json::json!({
                "meta": { "status": status, "exitCode": exit_code, "finishedAt": unix_now() }
            });
            let _ = writeln!(f, "{meta}");
        }
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct WorkLastLogLine {
    stream: String,
    line: String,
}

#[derive(Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct WorkLastLog {
    provider: Option<String>,
    plan_path: Option<String>,
    started_at: Option<u64>,
    finished_at: Option<u64>,
    status: Option<String>,
    exit_code: Option<i32>,
    lines: Vec<WorkLastLogLine>,
}

fn read_last_log(cwd: &std::path::Path) -> Option<WorkLastLog> {
    let text = std::fs::read_to_string(run_log_path(cwd)).ok()?;
    let mut out = WorkLastLog::default();
    let mut lines: std::collections::VecDeque<WorkLastLogLine> =
        std::collections::VecDeque::with_capacity(RUN_LOG_READ_CAP);
    for raw in text.lines() {
        let Ok(value) = serde_json::from_str::<serde_json::Value>(raw) else { continue };
        if let Some(meta) = value.get("meta") {
            if let Some(p) = meta.get("provider").and_then(|v| v.as_str()) {
                out.provider = Some(p.to_string());
            }
            if let Some(p) = meta.get("planPath").and_then(|v| v.as_str()) {
                out.plan_path = Some(p.to_string());
            }
            if let Some(t) = meta.get("startedAt").and_then(|v| v.as_u64()) {
                out.started_at = Some(t);
            }
            if let Some(t) = meta.get("finishedAt").and_then(|v| v.as_u64()) {
                out.finished_at = Some(t);
            }
            if let Some(s) = meta.get("status").and_then(|v| v.as_str()) {
                out.status = Some(s.to_string());
            }
            if let Some(c) = meta.get("exitCode").and_then(|v| v.as_i64()) {
                out.exit_code = Some(c as i32);
            }
            continue;
        }
        let (Some(stream), Some(line)) = (
            value.get("stream").and_then(|v| v.as_str()),
            value.get("line").and_then(|v| v.as_str()),
        ) else {
            continue;
        };
        if lines.len() >= RUN_LOG_READ_CAP {
            let _ = lines.pop_front();
        }
        lines.push_back(WorkLastLogLine { stream: stream.to_string(), line: line.to_string() });
    }
    out.lines = lines.into_iter().collect();
    Some(out)
}

#[tauri::command]
pub(crate) fn work_last_log(cwd: String) -> Option<WorkLastLog> {
    read_last_log(std::path::Path::new(&cwd))
}

// ─── MCP 자동 주입 (기획안 §9 확정·§10 P0) ─────────────────────────────────────
// 실행별 임시 mcp-config 를 만들어 CLI에 붙인다 — 사용자 전역 설정 불변.
// 절대경로 필수: claude 가 MCP 서버를 spawn 할 때 GUI 의 augmented PATH 를 상속받지
// 못한다. 서버 미설치(번들 vib-runtime 에는 vibelign-mcp 가 없음)·쓰기 실패 시 None
// → 사후 guard 폴백(M3 시퀀스가 그대로 안전망).

/// mcp-config 본문 — serde 직렬화가 공백·한글 경로의 JSON 이스케이프를 보장한다.
fn mcp_config_body(server: &std::path::Path) -> Vec<u8> {
    let config = serde_json::json!({
        "mcpServers": {
            "vibelign": { "command": server.to_string_lossy() }
        }
    });
    serde_json::to_vec_pretty(&config).unwrap_or_default()
}

fn prepare_mcp_injection(run_id: u64) -> Option<std::path::PathBuf> {
    let server = find_executable("vibelign-mcp")?;
    let path = std::env::temp_dir().join(format!("vibelign-workroom-mcp-{run_id}.json"));
    let body = mcp_config_body(&server);
    if body.is_empty() {
        return None;
    }
    std::fs::write(&path, body).ok()?;
    Some(path)
}

/// 주입 시 CLI 인자 — strict: 사용자 전역 MCP 서버(메일 등)를 헤드리스 실행에
/// 끌어들이지 않는다(2026-06-12 실검증: 미지정 시 전역 서버가 함께 로드됨).
/// 도구 승인(--allowedTools)은 테스트 화이트리스트와 합쳐 한 번만 내보낸다.
fn injection_args(config: &std::path::Path) -> Vec<String> {
    vec![
        "--mcp-config".to_string(),
        config.to_string_lossy().to_string(),
        "--strict-mcp-config".to_string(),
    ]
}

/// --allowedTools 값 조립 — 테스트 화이트리스트 + (주입 성공 시) vibelign MCP.
/// 쉼표 결합 단일 플래그: 플래그를 두 번 주면 CLI 파서가 덮어쓸 수 있다.
fn allowed_tools_value(test_allowlist: &[&str], mcp_injected: bool) -> Option<String> {
    let mut allowed: Vec<&str> = test_allowlist.to_vec();
    if mcp_injected {
        allowed.push("mcp__vibelign");
    }
    if allowed.is_empty() {
        None
    } else {
        Some(allowed.join(","))
    }
}

/// 주입 성공 시 지시문 뒤에 붙는 안내 — 러너가 stdin 페이로드에 합류시킨다
/// (주입 실패 폴백에서 없는 도구를 지시문이 언급하지 않게 러너 쪽에서 결합).
const MCP_INSTRUCTION_SUFFIX: &str = "\n\n[VibeLign MCP 도구 안내]\nvibelign MCP 도구가 연결되어 있습니다. 파일을 수정하기 전 anchor_list·anchor_read_content 로 앵커 경계를 확인하고, 작업을 마치면 guard_check 로 약속 범위를 자체 검증하세요.";

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct WorkOutputEvent {
    run_id: u64,
    stream: &'static str,
    line: String,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct WorkStatusEvent {
    run_id: u64,
    status: &'static str,
    exit_code: Option<i32>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct WorkRoomStatus {
    running: bool,
    run_id: u64,
}

/// stream-json 은 \n 구분 JSON 라인이라 lines() 로 충분하다(.cmd 경유 CRLF 는
/// trim_end 로 흡수). watch.rs 의 Windows 바이트 리더는 \r 단독 진행바용 — 여기선 불필요.
fn spawn_output_thread<R: std::io::Read + Send + 'static>(
    reader: R,
    app: tauri::AppHandle,
    run_id: u64,
    stream: &'static str,
    log: Option<Arc<Mutex<std::fs::File>>>,
) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            let Ok(line) = line else { break };
            let line = line.trim_end_matches('\r').to_string();
            if line.is_empty() {
                continue;
            }
            append_log_line(&log, stream, &line);
            let _ = app.emit("work-output", WorkOutputEvent { run_id, stream, line });
        }
    });
}

/// 실행 종료 공통 정리 — child 해제, mcp 임시 설정 삭제, 로그 메타 기록, 종료 이벤트 발신.
/// 정상 종료/에러 두 경로가 같은 순서를 타야 임시 파일 잔존이 안 생긴다(리뷰 #7).
fn finish_run(
    app: &tauri::AppHandle,
    guard: &mut WorkRoomRuntime,
    run_id: u64,
    label: &'static str,
    exit_code: Option<i32>,
) {
    guard.child = None;
    if let Some(cfg) = guard.mcp_config.take() {
        let _ = std::fs::remove_file(cfg);
    }
    append_log_meta(guard.run_log.take(), label, exit_code);
    let _ = app.emit("work-status", WorkStatusEvent { run_id, status: label, exit_code });
}

/// 종료 감시 — try_wait 폴링으로 child 소유권을 Mutex 안에 유지한다(취소가 같은
/// 자리에서 kill 할 수 있어야 하므로 wait() 로 들고 나가면 안 된다).
fn spawn_waiter_thread(app: tauri::AppHandle, state: Arc<Mutex<WorkRoomRuntime>>, run_id: u64) {
    std::thread::spawn(move || loop {
        std::thread::sleep(std::time::Duration::from_millis(200));
        let Ok(mut guard) = state.lock() else { return };
        if guard.run_id != run_id {
            return; // 새 실행으로 교체됨 — 이 waiter 의 역할 끝
        }
        let Some(child) = guard.child.as_mut() else { return };
        match child.try_wait() {
            Ok(Some(status)) => {
                let label = if guard.cancelled {
                    "cancelled"
                } else if status.success() {
                    "done"
                } else {
                    "failed"
                };
                finish_run(&app, &mut guard, run_id, label, status.code());
                return;
            }
            Ok(None) => {}
            Err(_) => {
                finish_run(&app, &mut guard, run_id, "failed", None);
                return;
            }
        }
    });
}

#[tauri::command]
pub(crate) fn work_run(
    app: tauri::AppHandle,
    state: tauri::State<WorkRoomState>,
    run: tauri::State<run_preview::RunState>,
    provider: String,
    instruction: String,
    cwd: String,
    plan_path: Option<String>,
) -> Result<u64, String> {
    // §5 상호배제(best-effort) — 실행해보기가 같은 워킹트리에서 도는 중이면 작업을 막는다
    // (run_start 의 반대 방향. 별도 락 TOCTOU 는 run_preview 쪽 주석 참조).
    if run_preview::is_busy(&run) {
        return Err("실행해보기가 도는 중이에요. 중지한 뒤 작업해 주세요.".into());
    }
    let adapter =
        work_adapter(&provider).ok_or_else(|| format!("지원하지 않는 프로바이더입니다: {provider}"))?;
    let executable = find_executable(adapter.executable).ok_or_else(|| {
        format!("{} CLI를 찾을 수 없습니다. 설치·로그인 후 다시 시도해 주세요.", adapter.executable)
    })?;

    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.child.is_some() {
        return Err("이미 작업이 실행 중입니다. 끝나기를 기다리거나 취소해 주세요.".into());
    }
    let run_id = guard.run_id + 1;

    let mcp_config = if adapter.mcp_injection { prepare_mcp_injection(run_id) } else { None };
    let run_log = open_run_log(std::path::Path::new(&cwd), &provider, plan_path.as_deref());

    let mut cmd = std::process::Command::new(&executable);
    cmd.args(adapter.args);
    if let Some(cfg) = mcp_config.as_deref() {
        cmd.args(injection_args(cfg));
    }
    if let Some(allowed) = allowed_tools_value(adapter.test_allowlist, mcp_config.is_some()) {
        cmd.arg("--allowedTools");
        cmd.arg(allowed);
    }
    cmd.current_dir(std::path::PathBuf::from(&cwd));
    cmd.stdin(std::process::Stdio::piped());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());
    cmd.env("PATH", augmented_vib_path());
    cmd.env("NO_COLOR", "1");
    hide_console(&mut cmd);
    // Unix: 새 프로세스 그룹 생성 → kill_child_tree 의 killpg 가 손자까지 닿는다.
    #[cfg(unix)]
    unsafe {
        use std::os::unix::process::CommandExt;
        cmd.pre_exec(|| {
            libc::setpgid(0, 0);
            Ok(())
        });
    }

    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => {
            if let Some(cfg) = mcp_config.as_deref() {
                let _ = std::fs::remove_file(cfg);
            }
            return Err(e.to_string());
        }
    };

    // 지시문 stdin 주입 — 파이프 버퍼보다 긴 지시문이 write 에서 막혀도 커맨드 스레드가
    // 잠기지 않도록 별도 스레드에서 쓰고, drop 으로 닫아 EOF 를 보낸다(claude -p 시작 조건).
    // MCP 안내는 주입 성공시에만 합류 — 폴백에서 없는 도구를 지시문이 언급하지 않게.
    let payload = if mcp_config.is_some() {
        format!("{instruction}{MCP_INSTRUCTION_SUFFIX}")
    } else {
        instruction
    };
    if let Some(mut stdin) = child.stdin.take() {
        std::thread::spawn(move || {
            let _ = stdin.write_all(payload.as_bytes());
        });
    }

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    guard.run_id = run_id;
    guard.cancelled = false;
    let injected = mcp_config.is_some();
    guard.mcp_config = mcp_config;
    guard.run_log = run_log.clone();
    guard.child = Some(child);
    let shared = Arc::clone(&state.0);
    drop(guard);

    // 주입을 기대하는 프로바이더(claude)에서 실패했을 때만 알린다 — codex 는 설계상
    // 미주입이라 매 실행 알림은 소음이다. 사후 guard(M3)는 양쪽 모두 동일하게 돈다.
    if adapter.mcp_injection && !injected {
        let _ = app.emit(
            "work-output",
            WorkOutputEvent {
                run_id,
                stream: "stderr",
                line: "[vibelign] 검증 도구(MCP) 없이 실행합니다 — 종료 후 자동 검사만 적용돼요".to_string(),
            },
        );
    }

    if let Some(out) = stdout {
        spawn_output_thread(out, app.clone(), run_id, "stdout", run_log.clone());
    }
    if let Some(err) = stderr {
        spawn_output_thread(err, app.clone(), run_id, "stderr", run_log);
    }
    spawn_waiter_thread(app, shared, run_id);
    Ok(run_id)
}

/// 취소 코어 — child 를 자리에 둔 채 트리 kill 만 한다. 종료 보고(cancelled)는
/// waiter 가 try_wait 로 회수하며 일원화한다. 반환: 실행 중이던 작업이 있었는지.
fn cancel_current(runtime: &Arc<Mutex<WorkRoomRuntime>>) -> bool {
    let Ok(mut guard) = runtime.lock() else { return false };
    if guard.child.is_none() {
        return false;
    }
    guard.cancelled = true;
    if let Some(child) = guard.child.as_mut() {
        kill_child_tree(child);
    }
    true
}

#[tauri::command]
pub(crate) fn work_cancel(state: tauri::State<WorkRoomState>) -> bool {
    cancel_current(&state.0)
}

#[tauri::command]
pub(crate) fn work_status(state: tauri::State<WorkRoomState>) -> WorkRoomStatus {
    state
        .0
        .lock()
        .map(|g| WorkRoomStatus { running: g.child.is_some(), run_id: g.run_id })
        .unwrap_or(WorkRoomStatus { running: false, run_id: 0 })
}

#[cfg(test)]
mod tests {
    use super::{cancel_current, new_state_pair, stop_for_exit, work_adapter};

    #[test]
    fn claude_adapter_uses_stream_json_and_accept_edits_without_danger_flags() {
        let adapter = work_adapter("claude").expect("claude adapter");
        assert_eq!(adapter.executable, "claude");
        assert!(adapter.args.contains(&"stream-json"));
        assert!(adapter.args.contains(&"acceptEdits"));
        assert!(adapter.mcp_injection);
        // 위험 권한 플래그 금지(기획안 §3) — 어댑터 차원에서 회귀 방지
        assert!(!adapter.args.iter().any(|a| a.contains("dangerously")));
    }

    #[test]
    fn codex_adapter_is_workspace_sandboxed_without_injection_or_danger_flags() {
        let adapter = work_adapter("codex").expect("codex adapter");
        assert_eq!(adapter.executable, "codex");
        assert!(adapter.args.contains(&"workspace-write"));
        assert!(adapter.args.contains(&"--skip-git-repo-check"));
        assert!(!adapter.mcp_injection);
        assert!(!adapter.args.iter().any(|a| a.contains("dangerously")));
    }

    #[test]
    fn unknown_provider_has_no_adapter() {
        assert!(work_adapter("opencode").is_none());
        assert!(work_adapter("").is_none());
    }

    #[test]
    fn run_log_round_trip_persists_meta_and_lines() {
        use std::sync::Arc;
        let dir = tempfile::tempdir().expect("tempdir");
        let log =
            super::open_run_log(dir.path(), "claude", Some("plans/알람앱.md")).expect("open log");
        super::append_log_line(&Some(Arc::clone(&log)), "stdout", "{\"type\":\"assistant\"}");
        super::append_log_meta(Some(log), "done", Some(0));

        let parsed = super::read_last_log(dir.path()).expect("read log");
        assert_eq!(parsed.provider.as_deref(), Some("claude"));
        assert_eq!(parsed.plan_path.as_deref(), Some("plans/알람앱.md"));
        assert_eq!(parsed.status.as_deref(), Some("done"));
        assert_eq!(parsed.exit_code, Some(0));
        assert!(parsed.started_at.is_some() && parsed.finished_at.is_some());
        assert_eq!(parsed.lines.len(), 1);
        assert_eq!(parsed.lines[0].stream, "stdout");
        assert_eq!(parsed.lines[0].line, "{\"type\":\"assistant\"}");
    }

    #[test]
    fn mcp_config_escapes_space_and_korean_paths() {
        // §10 P0 — 한글 사용자명·공백("Application Support") 경로가 JSON 에서 깨지면
        // claude 가 MCP 서버를 못 찾는다. serde 직렬화 보장을 회귀 테스트로 고정.
        let body = super::mcp_config_body(std::path::Path::new(
            "/Users/홍길동/Application Support/vibelign-mcp",
        ));
        let parsed: serde_json::Value = serde_json::from_slice(&body).expect("valid json");
        assert_eq!(
            parsed["mcpServers"]["vibelign"]["command"],
            "/Users/홍길동/Application Support/vibelign-mcp"
        );
    }

    #[test]
    fn injection_args_use_strict_mcp_config() {
        let args = super::injection_args(std::path::Path::new("/tmp/cfg.json"));
        assert_eq!(args, vec!["--mcp-config", "/tmp/cfg.json", "--strict-mcp-config"]);
    }

    #[test]
    fn allowed_tools_combine_test_allowlist_and_mcp_in_single_value() {
        // 화이트리스트 + MCP 를 쉼표 결합 단일 값으로 — 플래그 중복 시 파서가 덮어쓸 수 있다.
        let adapter = work_adapter("claude").expect("claude adapter");
        let value = super::allowed_tools_value(adapter.test_allowlist, true).expect("value");
        assert!(value.contains("Bash(npm test:*)"));
        assert!(value.contains("Bash(node --test:*)"));
        assert!(value.ends_with("mcp__vibelign"));
        // 테스트 명령 외 임의 셸 허용이 끼어들지 않게 — 전부 Bash(테스트…) 또는 mcp 네임스페이스.
        for tool in value.split(',') {
            assert!(
                tool.starts_with("Bash(npm test") || tool.starts_with("Bash(node --test") || tool == "mcp__vibelign",
                "unexpected allowed tool: {tool}"
            );
        }
        // 주입 실패 시에도 테스트 화이트리스트는 유지된다.
        let fallback = super::allowed_tools_value(adapter.test_allowlist, false).expect("value");
        assert!(!fallback.contains("mcp__vibelign"));
        assert!(fallback.contains("Bash(npm test)"));
        // codex 는 자체 샌드박스 — 화이트리스트 없음 → 플래그 미발행.
        let codex = work_adapter("codex").expect("codex adapter");
        assert!(super::allowed_tools_value(codex.test_allowlist, false).is_none());
    }

    #[test]
    fn cancel_without_running_child_reports_false() {
        let (state, _shutdown) = new_state_pair();
        assert!(!cancel_current(&state.0));
    }

    #[cfg(unix)]
    #[test]
    fn cancel_kills_running_child_and_marks_cancelled() {
        let (state, _shutdown) = new_state_pair();
        let child = std::process::Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("spawn sleep child");

        {
            let mut guard = state.0.lock().expect("work state lock");
            guard.child = Some(child);
        }

        assert!(cancel_current(&state.0));

        let mut guard = state.0.lock().expect("work state lock");
        assert!(guard.cancelled);
        // kill_child_tree 가 wait 까지 끝냈으므로 종료 상태가 즉시 회수돼야 한다.
        let status = guard
            .child
            .as_mut()
            .expect("child stays until waiter reaps")
            .try_wait()
            .expect("try_wait after kill");
        assert!(status.is_some(), "child must be dead after cancel");
    }

    #[cfg(unix)]
    #[test]
    fn stop_for_exit_kills_child_registered_in_shared_runtime() {
        let (state, shutdown) = new_state_pair();
        let child = std::process::Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("spawn sleep child");

        {
            let mut guard = state.0.lock().expect("work state lock");
            guard.child = Some(child);
        }

        stop_for_exit(&shutdown);

        let guard = state.0.lock().expect("work state lock");
        assert!(guard.child.is_none());
    }
}
// === ANCHOR: WORK_ROOM_END ===
