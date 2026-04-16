#![cfg(not(target_os = "windows"))]

use vibelign_gui_lib::testing::{run_command_capture_streamed_for_test, CommandCaptureForTest};

#[test]
#[cfg(target_os = "macos")]
fn macos_install_fake_script_produces_runnable_artifact() {
    use std::io::Write;
    let tmp = std::env::temp_dir().join(format!(
        "vibelign-fake-install-{}.sh",
        std::process::id()
    ));
    let mut f = std::fs::File::create(&tmp).unwrap();
    writeln!(f, "#!/bin/bash").unwrap();
    writeln!(f, "mkdir -p \"$HOME/.local/bin\"").unwrap();
    writeln!(f, "cat > \"$HOME/.local/bin/claude-vibelign-test\" <<'EOF'").unwrap();
    writeln!(f, "#!/bin/bash").unwrap();
    writeln!(f, "echo claude-vibelign-test 0.0.0").unwrap();
    writeln!(f, "EOF").unwrap();
    writeln!(f, "chmod +x \"$HOME/.local/bin/claude-vibelign-test\"").unwrap();
    drop(f);

    let result = run_command_capture_streamed_for_test(
        "/bin/bash",
        &[tmp.to_str().unwrap()],
        &[],
        |_: &str, _: &str| {},
    )
    .expect("fake installer runs");

    assert!(result.ok, "fake installer should exit 0");
    let home = std::env::var("HOME").unwrap();
    let bin = std::path::PathBuf::from(&home).join(".local/bin/claude-vibelign-test");
    assert!(bin.exists(), "fake binary should exist at {}", bin.display());

    let _ = std::fs::remove_file(&tmp);
    let _ = std::fs::remove_file(&bin);
}

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
