// === ANCHOR: BENCH_ENGINE_DIRECT_START ===
//! Phase 3 PoC bench: in-process `handle()` call vs `vibelign-engine` subprocess.
//!
//! Usage:
//! ```
//! cargo run --release --example bench_engine_direct -- /tmp/vib-bench-list 50
//! ```
//!
//! Prints min/median/max for each path and the ratio. Run after `vib install`
//! has populated `.vibelign/checkpoints.db` in the target root.

use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::Instant;
use std::io::Write;

use vibelign_core::ipc::handler::handle;
use vibelign_core::ipc::protocol::EngineRequest;

fn main() {
    let mut args = std::env::args().skip(1);
    let root = args
        .next()
        .map(PathBuf::from)
        .expect("usage: bench_engine_direct <root> <iterations>");
    let iterations: usize = args
        .next()
        .map(|raw| raw.parse().expect("iterations must be a number"))
        .unwrap_or(50);

    let engine_bin = std::env::current_exe()
        .ok()
        .and_then(|exe| exe.parent().and_then(|deps| deps.parent()).map(|profile| profile.join("vibelign-engine")))
        .filter(|path| path.exists())
        .unwrap_or_else(|| {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("target")
                .join("release")
                .join("vibelign-engine")
        });
    assert!(engine_bin.exists(), "engine binary not found: {:?}", engine_bin);

    println!("root         : {}", root.display());
    println!("engine binary: {}", engine_bin.display());
    println!("iterations   : {iterations}");
    println!();

    // ── direct in-process ──
    let mut direct = Vec::with_capacity(iterations);
    for _ in 0..iterations {
        let request = EngineRequest::CheckpointList { root: root.clone() };
        let start = Instant::now();
        let _response = handle(request);
        direct.push(start.elapsed().as_secs_f64() * 1000.0);
    }

    // ── subprocess (mimics 1-shot CLI invocation) ──
    let request_json = serde_json::to_string(&serde_json::json!({
        "command": "checkpoint_list",
        "root": root.to_string_lossy(),
    }))
    .expect("serialize request");

    let mut subprocess = Vec::with_capacity(iterations);
    for _ in 0..iterations {
        let start = Instant::now();
        let mut child = Command::new(&engine_bin)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn engine");
        child
            .stdin
            .as_mut()
            .expect("stdin handle")
            .write_all(request_json.as_bytes())
            .expect("write stdin");
        let _output = child.wait_with_output().expect("engine output");
        subprocess.push(start.elapsed().as_secs_f64() * 1000.0);
    }

    print_stats("direct (handle)        ", &direct);
    print_stats("subprocess (1-shot CLI)", &subprocess);

    let direct_median = median(&direct);
    let subprocess_median = median(&subprocess);
    println!();
    println!(
        "subprocess / direct median: {:.1}x  ({} ms saved per call)",
        subprocess_median / direct_median,
        (subprocess_median - direct_median).round() as i64
    );
}

fn print_stats(label: &str, samples: &[f64]) {
    let mut sorted = samples.to_vec();
    sorted.sort_by(|left, right| left.partial_cmp(right).expect("no NaN"));
    let min = sorted.first().copied().unwrap_or_default();
    let max = sorted.last().copied().unwrap_or_default();
    let mean = samples.iter().sum::<f64>() / samples.len() as f64;
    println!(
        "{label}  min {:>7.3} ms  median {:>7.3} ms  mean {:>7.3} ms  max {:>7.3} ms  (n={})",
        min,
        median(samples),
        mean,
        max,
        samples.len(),
    );
}

fn median(samples: &[f64]) -> f64 {
    let mut sorted = samples.to_vec();
    sorted.sort_by(|left, right| left.partial_cmp(right).expect("no NaN"));
    let mid = sorted.len() / 2;
    if sorted.len() % 2 == 1 {
        sorted[mid]
    } else {
        (sorted[mid - 1] + sorted[mid]) / 2.0
    }
}
// === ANCHOR: BENCH_ENGINE_DIRECT_END ===
