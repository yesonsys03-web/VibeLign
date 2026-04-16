#![cfg(not(target_os = "windows"))]

use vibelign_gui_lib::testing::{run_command_capture_streamed_for_test, CommandCaptureForTest};

#[test]
fn run_command_capture_streamed_captures_echo_on_macos() {
    let mut lines: Vec<String> = Vec::new();
    let result: CommandCaptureForTest = run_command_capture_streamed_for_test(
        "/bin/echo",
        &["hello-from-vibelign"],
        &[],
        |_title: &str, line: &str| lines.push(line.to_string()),
    )
    .expect("spawn succeeds");

    assert!(result.ok, "exit code should be 0, got {}", result.exit_code);
    assert!(
        result.stdout.contains("hello-from-vibelign"),
        "stdout should contain echoed text, got {:?}",
        result.stdout
    );
    assert!(
        lines.iter().any(|l| l.contains("hello-from-vibelign")),
        "streaming sink should have received the echoed line"
    );
}
