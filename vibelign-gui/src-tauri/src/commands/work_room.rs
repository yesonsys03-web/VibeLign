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
use super::watch::kill_watch_child as kill_child_tree;

struct WorkRoomRuntime {
    child: Option<std::process::Child>,
    /// 단조 증가 실행 id — 이벤트 수신측이 이전 실행의 잔여 라인을 걸러낼 기준.
    run_id: u64,
    /// 취소 요청 여부 — waiter 가 종료 상태를 cancelled 로 보고하게 한다.
    cancelled: bool,
    /// 실행별 임시 MCP 설정 파일 — waiter 가 종료 시 정리한다.
    mcp_config: Option<std::path::PathBuf>,
}

impl WorkRoomRuntime {
    fn new() -> Self {
        Self { child: None, run_id: 0, cancelled: false, mcp_config: None }
    }
}

pub(crate) struct WorkRoomState(Arc<Mutex<WorkRoomRuntime>>);

pub(crate) struct WorkRoomShutdownHandle(Arc<Mutex<WorkRoomRuntime>>);

pub(crate) fn new_state_pair() -> (WorkRoomState, WorkRoomShutdownHandle) {
    let inner = Arc::new(Mutex::new(WorkRoomRuntime::new()));
    (WorkRoomState(Arc::clone(&inner)), WorkRoomShutdownHandle(inner))
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

/// 프로바이더별 헤드리스 어댑터 — (실행파일명, 고정 인자). 지시문은 stdin 으로 들어간다.
/// MVP 는 코딩 에이전트로 검증된 CLI 만 연다(기획안 §1) — Codex 는 마일스톤 5 에서 추가.
/// MCP 주입(--mcp-config)은 마일스톤 4 에서 이 인자 빌더에 합류한다.
fn work_adapter(provider: &str) -> Option<(&'static str, &'static [&'static str])> {
    match provider {
        // claude -p 는 인자 프롬프트가 없으면 stdin 을 읽는다(EOF 필요).
        // stream-json 은 print 모드에서 --verbose 가 있어야 동작하는 CLI 제약.
        // acceptEdits: 워크스페이스 내 편집만 자동 승인 — 위험 플래그 금지(기획안 §3).
        "claude" => Some((
            "claude",
            &["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits"],
        )),
        _ => None,
    }
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

/// 주입 시 CLI 인자 — allowedTools 로 vibelign 서버 도구를 헤드리스에서 승인한다
/// (acceptEdits 는 편집만 자동 승인하므로 MCP 도구는 별도 허용이 필요).
/// strict: 사용자 전역 MCP 서버(메일 등)를 헤드리스 실행에 끌어들이지 않는다 —
/// 결정론·소음 차단(2026-06-12 실검증: 미지정 시 전역 서버가 함께 로드됨).
fn injection_args(config: &std::path::Path) -> Vec<String> {
    vec![
        "--mcp-config".to_string(),
        config.to_string_lossy().to_string(),
        "--strict-mcp-config".to_string(),
        "--allowedTools".to_string(),
        "mcp__vibelign".to_string(),
    ]
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
) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            let Ok(line) = line else { break };
            let line = line.trim_end_matches('\r').to_string();
            if line.is_empty() {
                continue;
            }
            let _ = app.emit("work-output", WorkOutputEvent { run_id, stream, line });
        }
    });
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
                guard.child = None;
                if let Some(cfg) = guard.mcp_config.take() {
                    let _ = std::fs::remove_file(cfg);
                }
                let label = if guard.cancelled {
                    "cancelled"
                } else if status.success() {
                    "done"
                } else {
                    "failed"
                };
                let _ = app.emit(
                    "work-status",
                    WorkStatusEvent { run_id, status: label, exit_code: status.code() },
                );
                return;
            }
            Ok(None) => {}
            Err(_) => {
                guard.child = None;
                if let Some(cfg) = guard.mcp_config.take() {
                    let _ = std::fs::remove_file(cfg);
                }
                let _ = app.emit(
                    "work-status",
                    WorkStatusEvent { run_id, status: "failed", exit_code: None },
                );
                return;
            }
        }
    });
}

#[tauri::command]
pub(crate) fn work_run(
    app: tauri::AppHandle,
    state: tauri::State<WorkRoomState>,
    provider: String,
    instruction: String,
    cwd: String,
) -> Result<u64, String> {
    let (executable_name, args) =
        work_adapter(&provider).ok_or_else(|| format!("지원하지 않는 프로바이더입니다: {provider}"))?;
    let executable = find_executable(executable_name).ok_or_else(|| {
        format!("{executable_name} CLI를 찾을 수 없습니다. 설치·로그인 후 다시 시도해 주세요.")
    })?;

    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if guard.child.is_some() {
        return Err("이미 작업이 실행 중입니다. 끝나기를 기다리거나 취소해 주세요.".into());
    }
    let run_id = guard.run_id + 1;

    let mcp_config = prepare_mcp_injection(run_id);

    let mut cmd = std::process::Command::new(&executable);
    cmd.args(args);
    if let Some(cfg) = mcp_config.as_deref() {
        cmd.args(injection_args(cfg));
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
    guard.child = Some(child);
    let shared = Arc::clone(&state.0);
    drop(guard);

    if !injected {
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
        spawn_output_thread(out, app.clone(), run_id, "stdout");
    }
    if let Some(err) = stderr {
        spawn_output_thread(err, app.clone(), run_id, "stderr");
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
        let (executable, args) = work_adapter("claude").expect("claude adapter");
        assert_eq!(executable, "claude");
        assert!(args.contains(&"stream-json"));
        assert!(args.contains(&"acceptEdits"));
        // 위험 권한 플래그 금지(기획안 §3) — 어댑터 차원에서 회귀 방지
        assert!(!args.iter().any(|a| a.contains("dangerously")));
    }

    #[test]
    fn unknown_provider_has_no_adapter() {
        assert!(work_adapter("opencode").is_none());
        assert!(work_adapter("").is_none());
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
    fn injection_args_use_mcp_config_and_server_level_allow() {
        let args = super::injection_args(std::path::Path::new("/tmp/cfg.json"));
        assert_eq!(
            args,
            vec!["--mcp-config", "/tmp/cfg.json", "--strict-mcp-config", "--allowedTools", "mcp__vibelign"]
        );
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
