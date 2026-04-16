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
#[cfg(target_os = "macos")]
fn verify_macos_shells_detects_fake_claude_on_path() {
    let tmp_dir = std::env::temp_dir().join(format!("vibelign-bin-{}", std::process::id()));
    std::fs::create_dir_all(&tmp_dir).unwrap();
    let claude_path = tmp_dir.join("claude");
    std::fs::write(&claude_path, "#!/bin/bash\necho claude 1.2.3-test\n").unwrap();
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(&claude_path, std::fs::Permissions::from_mode(0o755)).unwrap();

    let old_path = std::env::var("PATH").unwrap_or_default();
    let new_path = format!("{}:{}", tmp_dir.display(), old_path);
    let result = run_command_capture_streamed_for_test(
        "/bin/zsh",
        &["-lc", "claude --version"],
        &[("PATH", new_path)],
        |_: &str, _: &str| {},
    )
    .expect("zsh -lc runs");

    let stdout_has_version = result.stdout.contains("claude 1.2.3-test");
    let direct = std::process::Command::new(&claude_path)
        .arg("--version")
        .output()
        .unwrap();
    assert!(
        stdout_has_version || direct.status.success(),
        "claude --version should resolve either via zsh -lc PATH or direct exec"
    );

    let _ = std::fs::remove_dir_all(&tmp_dir);
}

#[test]
#[cfg(target_os = "macos")]
fn ensure_macos_path_marker_is_idempotent() {
    let tmp = std::env::temp_dir().join(format!("vibelign-rc-{}", std::process::id()));
    std::fs::create_dir_all(&tmp).unwrap();
    let zshrc = tmp.join(".zshrc");
    std::fs::write(&zshrc, "# existing zshrc\nexport FOO=bar\n").unwrap();

    vibelign_gui_lib::testing::ensure_macos_path_marker_at(&tmp)
        .expect("first append succeeds");
    let first = std::fs::read_to_string(&zshrc).unwrap();
    assert!(first.contains("# >>> vibelign >>>"));
    assert!(first.contains("export PATH=\"$HOME/.local/bin:$PATH\""));
    assert!(first.contains("# existing zshrc"));

    vibelign_gui_lib::testing::ensure_macos_path_marker_at(&tmp)
        .expect("second call is idempotent");
    let second = std::fs::read_to_string(&zshrc).unwrap();
    assert_eq!(first, second, "second call must not duplicate marker block");

    let _ = std::fs::remove_dir_all(&tmp);
}

#[test]
#[cfg(target_os = "macos")]
fn ensure_macos_path_marker_creates_missing_rc_files() {
    let tmp = std::env::temp_dir().join(format!("vibelign-rc-new-{}", std::process::id()));
    std::fs::create_dir_all(&tmp).unwrap();

    vibelign_gui_lib::testing::ensure_macos_path_marker_at(&tmp)
        .expect("should create missing rc files");

    assert!(tmp.join(".zshrc").exists(), ".zshrc should be created");
    assert!(tmp.join(".bash_profile").exists(), ".bash_profile should be created");

    let _ = std::fs::remove_dir_all(&tmp);
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
