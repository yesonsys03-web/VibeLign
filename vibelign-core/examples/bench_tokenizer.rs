// === ANCHOR: BENCH_TOKENIZER_START ===
//! Rust isolated bench: in-process pure tokenizer 의 floor 시간 측정.
//!
//! Advisor 권고 (2026-05-13): "If Rust itself is 100ms for 1M calls, you have
//! 90% of your savings even with IPC overhead. If Rust is 10ms for 1M, IPC
//! dominates and B wins decisively."
//!
//! Run: `cargo run --release --example bench_tokenizer`

#![allow(dead_code)] // path-included module 의 일부 fn 만 bench

use std::time::Instant;

// tokenizer 는 `mod tokenizer;` 로 private. example 은 lib 의 private 모듈에
// 접근 불가하므로 path 로 직접 include — bench 만의 우회. production code 는
// ipc 경로로만 노출.
#[path = "../src/tokenizer.rs"]
mod tokenizer;

fn main() {
    // 실제 score_path 가 패스/intent 를 통과시킬 때 자주 나오는 입력 분포.
    let inputs: &[&str] = &[
        "로그인 button 사용자 화면",
        "ClaudeHookCard.tsx",
        "vibelign/core/patch_suggester.py",
        "비밀번호 변경 화면 설정",
        "src/components/LoginButton.tsx",
        "회원가입 메뉴 활성화 비활성화",
        "submit form click handle",
        "토큰 발급 저장 캐시",
    ];

    let iterations: usize = 1_000_000;

    // Warmup 한 사이클.
    for s in inputs {
        let _ = tokenizer::intent_tokens(s);
    }

    let start = Instant::now();
    for i in 0..iterations {
        let s = inputs[i % inputs.len()];
        let _ = tokenizer::intent_tokens(s);
    }
    let elapsed = start.elapsed();

    let per_call_ns = elapsed.as_nanos() as f64 / iterations as f64;
    println!(
        "intent_tokens × {iters}: {elapsed:.3?} → {per:.0} ns/call",
        iters = iterations,
        elapsed = elapsed,
        per = per_call_ns,
    );

    // expand_token 만도 측정 — score_path 내부에서 가장 자주 호출.
    let start = Instant::now();
    for i in 0..iterations {
        let s = inputs[i % inputs.len()];
        let _ = tokenizer::expand_token(s);
    }
    let elapsed = start.elapsed();
    let per_call_ns = elapsed.as_nanos() as f64 / iterations as f64;
    println!(
        "expand_token  × {iters}: {elapsed:.3?} → {per:.0} ns/call",
        iters = iterations,
        elapsed = elapsed,
        per = per_call_ns,
    );

    // decompose_korean_compound (가장 호출 빈도 높은 leaf).
    let start = Instant::now();
    for i in 0..iterations {
        let s = inputs[i % inputs.len()];
        let _ = tokenizer::decompose_korean_compound(s);
    }
    let elapsed = start.elapsed();
    let per_call_ns = elapsed.as_nanos() as f64 / iterations as f64;
    println!(
        "decompose     × {iters}: {elapsed:.3?} → {per:.0} ns/call",
        iters = iterations,
        elapsed = elapsed,
        per = per_call_ns,
    );
}
// === ANCHOR: BENCH_TOKENIZER_END ===
