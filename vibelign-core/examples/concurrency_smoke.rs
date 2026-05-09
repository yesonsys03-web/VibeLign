// === ANCHOR: CONCURRENCY_SMOKE_START ===
//! advisor 지적: GUI direct + Rust daemon + Python subprocess 가 같은
//! `vibelign.db` 에 동시 접근 시 `database is locked` 회귀가 없는지 검증.
//! WAL + `busy_timeout=5000ms` (per Phase -1 결정) 가 실제로 contention 을 흡수하는지
//! 측정한다. CheckpointCreate (write 경로) 와 CheckpointList (read 경로) 를
//! in-process `handle()` 와 1-shot subprocess 양쪽에서 병렬로 두드린다.
//!
//! Usage:
//! ```
//! cargo run --release --example concurrency_smoke -- /tmp/vib-concurrency-smoke 20
//! ```

use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use vibelign_core::ipc::handler::handle;
use vibelign_core::ipc::protocol::{EngineRequest, EngineResponse};

fn main() {
    let mut args = std::env::args().skip(1);
    let root = args
        .next()
        .map(PathBuf::from)
        .expect("usage: concurrency_smoke <root> <iterations>");
    let iterations: usize = args
        .next()
        .map(|raw| raw.parse().expect("iterations must be a number"))
        .unwrap_or(20);

    let engine_bin = engine_binary_path();
    assert!(engine_bin.exists(), "engine binary not found at {:?}", engine_bin);

    println!("root         : {}", root.display());
    println!("engine binary: {}", engine_bin.display());
    println!("iterations   : {iterations} (per worker)");
    println!();

    let direct_writes_ok = AtomicUsize::new(0);
    let subprocess_writes_ok = AtomicUsize::new(0);
    let direct_reads_ok = AtomicUsize::new(0);
    let subprocess_reads_ok = AtomicUsize::new(0);
    let direct_errors = AtomicUsize::new(0);
    let subprocess_errors = AtomicUsize::new(0);
    let mut error_messages: Vec<String> = Vec::new();

    let start = Instant::now();
    std::thread::scope(|scope| {
        // ── writer A: in-process handle() ──
        let root_a = root.clone();
        let direct_writes_ref = &direct_writes_ok;
        let direct_errors_ref = &direct_errors;
        scope.spawn(move || {
            for index in 0..iterations {
                touch_file(&root_a, &format!("worker_a/{index}.txt"));
                let request = EngineRequest::CheckpointCreate {
                    root: root_a.clone(),
                    message: format!("worker_a-{index}"),
                    trigger: Some("concurrency_smoke".to_string()),
                    git_commit_sha: None,
                    git_commit_message: None,
                };
                match handle(request) {
                    EngineResponse::Ok { .. } => {
                        direct_writes_ref.fetch_add(1, Ordering::Relaxed);
                    }
                    EngineResponse::Error { code, message } => {
                        direct_errors_ref.fetch_add(1, Ordering::Relaxed);
                        eprintln!("direct write error: {code} :: {message}");
                    }
                    _ => {}
                }
            }
        });

        // ── writer B: 1-shot subprocess ──
        let root_b = root.clone();
        let engine_b = engine_bin.clone();
        let subprocess_writes_ref = &subprocess_writes_ok;
        let subprocess_errors_ref = &subprocess_errors;
        scope.spawn(move || {
            for index in 0..iterations {
                touch_file(&root_b, &format!("worker_b/{index}.txt"));
                let request_json = serde_json::to_string(&serde_json::json!({
                    "command": "checkpoint_create",
                    "root": root_b.to_string_lossy(),
                    "message": format!("worker_b-{index}"),
                    "trigger": "concurrency_smoke",
                    "git_commit_sha": null,
                    "git_commit_message": null,
                }))
                .expect("serialize");
                if run_engine_subprocess(&engine_b, &request_json) {
                    subprocess_writes_ref.fetch_add(1, Ordering::Relaxed);
                } else {
                    subprocess_errors_ref.fetch_add(1, Ordering::Relaxed);
                }
            }
        });

        // ── reader threads: 4x in-process CheckpointList ──
        for _ in 0..4 {
            let root_r = root.clone();
            let direct_reads_ref = &direct_reads_ok;
            let direct_errors_ref = &direct_errors;
            scope.spawn(move || {
                for _ in 0..iterations {
                    let response = handle(EngineRequest::CheckpointList { root: root_r.clone() });
                    match response {
                        EngineResponse::Ok { .. } => {
                            direct_reads_ref.fetch_add(1, Ordering::Relaxed);
                        }
                        EngineResponse::Error { code, message } => {
                            direct_errors_ref.fetch_add(1, Ordering::Relaxed);
                            eprintln!("direct read error: {code} :: {message}");
                        }
                        _ => {}
                    }
                }
            });
        }

        // ── reader threads: 4x subprocess CheckpointList ──
        for _ in 0..4 {
            let root_r = root.clone();
            let engine_r = engine_bin.clone();
            let subprocess_reads_ref = &subprocess_reads_ok;
            let subprocess_errors_ref = &subprocess_errors;
            scope.spawn(move || {
                let request_json = serde_json::to_string(&serde_json::json!({
                    "command": "checkpoint_list",
                    "root": root_r.to_string_lossy(),
                }))
                .expect("serialize");
                for _ in 0..iterations {
                    if run_engine_subprocess(&engine_r, &request_json) {
                        subprocess_reads_ref.fetch_add(1, Ordering::Relaxed);
                    } else {
                        subprocess_errors_ref.fetch_add(1, Ordering::Relaxed);
                    }
                }
            });
        }
    });
    let elapsed = start.elapsed();

    println!();
    println!("elapsed                  : {:?}", elapsed);
    println!("direct write ok          : {}", direct_writes_ok.load(Ordering::Relaxed));
    println!("subprocess write ok      : {}", subprocess_writes_ok.load(Ordering::Relaxed));
    println!("direct read ok           : {}", direct_reads_ok.load(Ordering::Relaxed));
    println!("subprocess read ok       : {}", subprocess_reads_ok.load(Ordering::Relaxed));
    println!("direct error count       : {}", direct_errors.load(Ordering::Relaxed));
    println!("subprocess error count   : {}", subprocess_errors.load(Ordering::Relaxed));
    if !error_messages.is_empty() {
        println!("first errors             :");
        for msg in error_messages.iter().take(5) {
            println!("  {msg}");
        }
    }

    let total_errors =
        direct_errors.load(Ordering::Relaxed) + subprocess_errors.load(Ordering::Relaxed);
    if total_errors > 0 {
        eprintln!();
        eprintln!("FAIL: {total_errors} contention error(s) observed");
        std::process::exit(1);
    }
    println!();
    println!("PASS: WAL + busy_timeout 가 contention 을 흡수함");
}

fn touch_file(root: &Path, rel: &str) {
    let path = root.join(rel);
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let payload = format!(
        "concurrency-smoke {} {}\n",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default(),
    );
    let _ = std::fs::write(path, payload);
}

fn run_engine_subprocess(engine_bin: &Path, request_json: &str) -> bool {
    let mut child = match Command::new(engine_bin)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
    {
        Ok(child) => child,
        Err(error) => {
            eprintln!("subprocess spawn error: {error}");
            return false;
        }
    };
    if let Some(stdin) = child.stdin.as_mut() {
        if let Err(error) = stdin.write_all(request_json.as_bytes()) {
            eprintln!("subprocess stdin error: {error}");
            return false;
        }
    }
    let output = match child.wait_with_output() {
        Ok(output) => output,
        Err(error) => {
            eprintln!("subprocess wait error: {error}");
            return false;
        }
    };
    let stdout = String::from_utf8_lossy(&output.stdout);
    let trimmed = stdout.trim();
    if trimmed.contains("\"status\":\"error\"") {
        eprintln!("subprocess engine error: {trimmed}");
        return false;
    }
    output.status.success()
}

fn engine_binary_path() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest.join("target/release/vibelign-engine")
}
// === ANCHOR: CONCURRENCY_SMOKE_END ===
