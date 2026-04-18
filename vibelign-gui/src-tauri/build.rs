// === ANCHOR: BUILD_START ===
fn main() {
    // TARGET_TRIPLE을 컴파일 타임 상수로 굽는다.
    // vib_path.rs에서 env!("TARGET_TRIPLE")로 sidecar 파일명을 정확히 찾는다.
    println!(
        "cargo:rustc-env=TARGET_TRIPLE={}",
        std::env::var("TARGET").unwrap()
    );
    tauri_build::build()
}
// === ANCHOR: BUILD_END ===
