// === ANCHOR: DAEMON_START ===
#![allow(dead_code)]

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use super::protocol::{handle, EngineRequest, EngineResponse};

pub fn socket_path(root: &Path) -> PathBuf {
    root.join(".vibelign").join("engine.sock")
}

pub fn pid_path(root: &Path) -> PathBuf {
    root.join(".vibelign").join("engine.pid")
}

pub fn run_daemon(root: PathBuf) -> Result<(), String> {
    #[cfg(unix)]
    {
        unix::run_daemon(root)
    }
    #[cfg(not(unix))]
    {
        let _ = root;
        Err("daemon transport is not implemented on this platform yet".to_string())
    }
}

#[derive(Debug, Deserialize)]
pub struct DaemonEnvelope {
    request_id: String,
    payload: DaemonPayload,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "snake_case")]
enum DaemonPayload {
    EngineInfo,
    EngineVersion,
    Shutdown,
    CheckpointCreate {
        root: PathBuf,
        message: String,
        trigger: Option<String>,
        git_commit_sha: Option<String>,
        git_commit_message: Option<String>,
    },
    CheckpointList {
        root: PathBuf,
    },
    CheckpointRestore {
        root: PathBuf,
        checkpoint_id: String,
    },
    CheckpointDiff {
        root: PathBuf,
        from_checkpoint_id: String,
        to_checkpoint_id: String,
    },
    CheckpointRestorePreview {
        root: PathBuf,
        checkpoint_id: String,
    },
    CheckpointRestoreFilesPreview {
        root: PathBuf,
        checkpoint_id: String,
        relative_paths: Vec<String>,
    },
    CheckpointRestoreFilesSafe {
        root: PathBuf,
        checkpoint_id: String,
        relative_paths: Vec<String>,
    },
    CheckpointRestoreSuggestions {
        root: PathBuf,
        checkpoint_id: String,
        cap: Option<usize>,
    },
    CheckpointPrune {
        root: PathBuf,
        keep_latest: usize,
    },
    RetentionApply {
        root: PathBuf,
    },
    BackupDbViewerInspect {
        root: PathBuf,
    },
    BackupDbMaintenance {
        root: PathBuf,
        apply: bool,
    },
    BackupGraphSummary {
        root: PathBuf,
    },
    ProjectScan {
        root: PathBuf,
    },
}

#[derive(Debug, Serialize)]
pub struct DaemonResponseEnvelope {
    request_id: String,
    #[serde(flatten)]
    response: DaemonResponse,
}

#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
enum DaemonResponse {
    Ok {
        result: String,
        payload: Option<EngineResponse>,
    },
    Error {
        code: String,
        message: String,
    },
}

pub fn handle_envelope(daemon_root: &Path, envelope: DaemonEnvelope) -> DaemonResponseEnvelope {
    let request_id = envelope.request_id;
    let response = match envelope.payload {
        DaemonPayload::Shutdown => DaemonResponse::Ok {
            result: "shutdown".to_string(),
            payload: None,
        },
        DaemonPayload::EngineVersion => DaemonResponse::Ok {
            result: "engine_version".to_string(),
            payload: Some(EngineResponse::Ok {
                result: "engine_version".to_string(),
                checkpoint_id: None,
                created_at: None,
                message: Some(env!("CARGO_PKG_VERSION").to_string()),
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: None,
                restored_count: None,
                suggestions: None,
                legacy_notice: None,
            }),
        },
        payload => match payload.into_engine_request(daemon_root) {
            Ok(request) => DaemonResponse::Ok {
                result: "handled".to_string(),
                payload: Some(handle(request)),
            },
            Err(message) => DaemonResponse::Error {
                code: "DAEMON_ROOT_MISMATCH".to_string(),
                message,
            },
        },
    };
    DaemonResponseEnvelope { request_id, response }
}

fn handle_line(daemon_root: &Path, line: &str) -> (String, bool) {
    let parsed = serde_json::from_str::<DaemonEnvelope>(line);
    let envelope = match parsed {
        Ok(envelope) => envelope,
        Err(error) => {
            let response = DaemonResponseEnvelope {
                request_id: "".to_string(),
                response: DaemonResponse::Error {
                    code: "INVALID_DAEMON_JSON".to_string(),
                    message: error.to_string(),
                },
            };
            return (serialize_response(&response), false);
        }
    };
    let should_shutdown = matches!(envelope.payload, DaemonPayload::Shutdown);
    let response = handle_envelope(daemon_root, envelope);
    (serialize_response(&response), should_shutdown)
}

fn serialize_response(response: &DaemonResponseEnvelope) -> String {
    serde_json::to_string(response).unwrap_or_else(|error| {
        format!(
            "{{\"request_id\":\"\",\"status\":\"error\",\"code\":\"SERIALIZE_FAILED\",\"message\":{}}}",
            serde_json::to_string(&error.to_string()).unwrap_or_else(|_| "\"unknown\"".to_string())
        )
    })
}

impl DaemonPayload {
    fn into_engine_request(self, daemon_root: &Path) -> Result<EngineRequest, String> {
        match self {
            Self::EngineInfo => Ok(EngineRequest::EngineInfo),
            Self::CheckpointCreate {
                root,
                message,
                trigger,
                git_commit_sha,
                git_commit_message,
            } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointCreate {
                    root,
                    message,
                    trigger,
                    git_commit_sha,
                    git_commit_message,
                })
            }
            Self::CheckpointList { root } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointList { root })
            }
            Self::CheckpointRestore { root, checkpoint_id } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointRestore { root, checkpoint_id })
            }
            Self::CheckpointDiff {
                root,
                from_checkpoint_id,
                to_checkpoint_id,
            } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointDiff {
                    root,
                    from_checkpoint_id,
                    to_checkpoint_id,
                })
            }
            Self::CheckpointRestorePreview { root, checkpoint_id } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointRestorePreview { root, checkpoint_id })
            }
            Self::CheckpointRestoreFilesPreview {
                root,
                checkpoint_id,
                relative_paths,
            } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointRestoreFilesPreview {
                    root,
                    checkpoint_id,
                    relative_paths,
                })
            }
            Self::CheckpointRestoreFilesSafe {
                root,
                checkpoint_id,
                relative_paths,
            } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointRestoreFilesSafe {
                    root,
                    checkpoint_id,
                    relative_paths,
                })
            }
            Self::CheckpointRestoreSuggestions {
                root,
                checkpoint_id,
                cap,
            } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointRestoreSuggestions {
                    root,
                    checkpoint_id,
                    cap,
                })
            }
            Self::CheckpointPrune { root, keep_latest } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::CheckpointPrune { root, keep_latest })
            }
            Self::RetentionApply { root } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::RetentionApply { root })
            }
            Self::BackupDbViewerInspect { root } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::BackupDbViewerInspect { root })
            }
            Self::BackupDbMaintenance { root, apply } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::BackupDbMaintenance { root, apply })
            }
            Self::BackupGraphSummary { root } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::BackupGraphSummary { root })
            }
            Self::ProjectScan { root } => {
                validate_request_root(daemon_root, &root)?;
                Ok(EngineRequest::ProjectScan { root })
            }
            Self::EngineVersion | Self::Shutdown => unreachable!("daemon control commands are handled before conversion"),
        }
    }
}

fn validate_request_root(daemon_root: &Path, request_root: &Path) -> Result<(), String> {
    let daemon_root = canonical_or_original(daemon_root);
    let request_root = canonical_or_original(request_root);
    if daemon_root == request_root {
        Ok(())
    } else {
        Err(format!(
            "daemon root mismatch: daemon_root={}, request_root={}",
            daemon_root.display(),
            request_root.display()
        ))
    }
}

fn canonical_or_original(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

#[cfg(unix)]
mod unix {
    use std::io::ErrorKind;
    use std::io::{BufRead, BufReader, Write};
    use std::os::unix::net::{UnixListener, UnixStream};
    use std::path::{Path, PathBuf};
    use std::time::{Duration, Instant};

    use super::{handle_line, pid_path, socket_path};

    pub(super) fn run_daemon(root: PathBuf) -> Result<(), String> {
        let root = root
            .canonicalize()
            .map_err(|error| format!("daemon root is invalid: {error}"))?;
        let meta_dir = root.join(".vibelign");
        std::fs::create_dir_all(&meta_dir)
            .map_err(|error| format!("daemon metadata directory create failed: {error}"))?;
        let socket = socket_path(&root);
        let pid = pid_path(&root);
        prepare_daemon_artifacts(&socket, &pid)?;
        let listener = UnixListener::bind(&socket)
            .map_err(|error| format!("daemon socket bind failed: {error}"))?;
        listener
            .set_nonblocking(true)
            .map_err(|error| format!("daemon socket nonblocking setup failed: {error}"))?;
        write_pid_file(&pid)?;
        let _cleanup = DaemonArtifactCleanup::new(socket.clone(), pid);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&socket, std::fs::Permissions::from_mode(0o600));
        }

        let idle_timeout = idle_timeout();
        let mut last_activity = Instant::now();
        loop {
            match listener.accept() {
                Ok((stream, _addr)) => {
                    if handle_stream(&root, stream)? {
                        return Ok(());
                    }
                    last_activity = Instant::now();
                }
                Err(error) if error.kind() == ErrorKind::WouldBlock => {
                    if idle_expired(last_activity, Instant::now(), idle_timeout) {
                        return Ok(());
                    }
                    std::thread::sleep(Duration::from_millis(2));
                }
                Err(error) => return Err(format!("daemon socket accept failed: {error}")),
            }
        }
    }

    pub(super) fn idle_timeout() -> Duration {
        std::env::var("VIBELIGN_ENGINE_IDLE_TIMEOUT_SECONDS")
            .ok()
            .and_then(|value| value.parse::<f64>().ok())
            .filter(|seconds| seconds.is_finite() && *seconds > 0.0)
            .map(Duration::from_secs_f64)
            .unwrap_or_else(|| Duration::from_secs(300))
    }

    pub(super) fn idle_expired(last_activity: Instant, now: Instant, timeout: Duration) -> bool {
        now.duration_since(last_activity) >= timeout
    }

    pub(super) fn prepare_daemon_artifacts(socket: &Path, pid: &Path) -> Result<(), String> {
        if socket.exists() {
            if UnixStream::connect(socket).is_ok() {
                return Err(format!(
                    "daemon already running for this root: {}",
                    socket.display()
                ));
            }
            std::fs::remove_file(socket)
                .map_err(|error| format!("stale daemon socket remove failed: {error}"))?;
            let _ = std::fs::remove_file(pid);
        } else if pid.exists() {
            let _ = std::fs::remove_file(pid);
        }
        Ok(())
    }

    fn write_pid_file(pid: &Path) -> Result<(), String> {
        std::fs::write(pid, format!("{}\n", std::process::id()))
            .map_err(|error| format!("daemon pid file write failed: {error}"))?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(pid, std::fs::Permissions::from_mode(0o600));
        }
        Ok(())
    }

    struct DaemonArtifactCleanup {
        socket: PathBuf,
        pid: PathBuf,
    }

    impl DaemonArtifactCleanup {
        fn new(socket: PathBuf, pid: PathBuf) -> Self {
            Self { socket, pid }
        }
    }

    impl Drop for DaemonArtifactCleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.socket);
            let _ = std::fs::remove_file(&self.pid);
        }
    }

    fn handle_stream(root: &Path, mut stream: UnixStream) -> Result<bool, String> {
        stream
            .set_nonblocking(false)
            .map_err(|error| format!("daemon stream blocking setup failed: {error}"))?;
        let reader_stream = stream
            .try_clone()
            .map_err(|error| format!("daemon stream clone failed: {error}"))?;
        let mut reader = BufReader::new(reader_stream);
        let mut line = String::new();
        let mut should_shutdown = false;
        loop {
            line.clear();
            let read = reader
                .read_line(&mut line)
                .map_err(|error| format!("daemon stream read failed: {error}"))?;
            if read == 0 {
                break;
            }
            let trimmed = line.trim_end_matches(['\r', '\n']);
            if trimmed.is_empty() {
                continue;
            }
            let (response, shutdown) = handle_line(root, trimmed);
            stream
                .write_all(response.as_bytes())
                .and_then(|_| stream.write_all(b"\n"))
                .map_err(|error| format!("daemon stream write failed: {error}"))?;
            should_shutdown |= shutdown;
            if shutdown {
                break;
            }
        }
        Ok(should_shutdown)
    }
}

#[cfg(test)]
mod tests {
    use serde_json::Value;
    use tempfile::TempDir;

    use super::{handle_envelope, pid_path, socket_path, DaemonEnvelope};

    #[test]
    fn engine_info_echoes_request_id_and_preserves_v1_payload() {
        let root = TempDir::new().expect("temp root");
        let envelope: DaemonEnvelope = serde_json::from_value(serde_json::json!({
            "request_id": "req-1",
            "payload": {"command": "engine_info"}
        }))
        .expect("daemon envelope");

        let response = serde_json::to_value(handle_envelope(root.path(), envelope)).expect("response json");

        assert_eq!(response["request_id"], "req-1");
        assert_eq!(response["status"], "ok");
        assert_eq!(response["result"], "handled");
        assert_eq!(response["payload"]["status"], "ok");
        assert_eq!(response["payload"]["result"], "engine_info");
    }

    #[test]
    fn shutdown_is_daemon_control_command_without_v1_payload() {
        let root = TempDir::new().expect("temp root");
        let envelope: DaemonEnvelope = serde_json::from_value(serde_json::json!({
            "request_id": "stop-1",
            "payload": {"command": "shutdown"}
        }))
        .expect("daemon envelope");

        let response = serde_json::to_value(handle_envelope(root.path(), envelope)).expect("response json");

        assert_eq!(response["request_id"], "stop-1");
        assert_eq!(response["status"], "ok");
        assert_eq!(response["result"], "shutdown");
        assert_eq!(response.get("payload"), Some(&Value::Null));
    }

    #[test]
    fn request_root_must_match_daemon_root() {
        let daemon_root = TempDir::new().expect("daemon root");
        let other_root = TempDir::new().expect("other root");
        let envelope: DaemonEnvelope = serde_json::from_value(serde_json::json!({
            "request_id": "bad-root",
            "payload": {"command": "checkpoint_list", "root": other_root.path()}
        }))
        .expect("daemon envelope");

        let response = serde_json::to_value(handle_envelope(daemon_root.path(), envelope)).expect("response json");

        assert_eq!(response["request_id"], "bad-root");
        assert_eq!(response["status"], "error");
        assert_eq!(response["code"], "DAEMON_ROOT_MISMATCH");
    }

    #[test]
    fn project_scan_envelope_uses_daemon_root_validation() {
        let daemon_root = TempDir::new().expect("daemon root");
        let envelope: DaemonEnvelope = serde_json::from_value(serde_json::json!({
            "request_id": "scan-1",
            "payload": {
                "command": "project_scan",
                "root": daemon_root.path()
            }
        }))
        .expect("daemon envelope");

        let response = serde_json::to_value(handle_envelope(daemon_root.path(), envelope)).expect("response json");

        assert_eq!(response["request_id"], "scan-1");
        assert_eq!(response["status"], "ok");
        assert_eq!(response["result"], "handled");
        assert_eq!(response["payload"]["status"], "ok");
        assert_eq!(response["payload"]["result"], "project_scan");
    }

    #[test]
    fn line_handler_serializes_response_and_shutdown_signal() {
        let root = TempDir::new().expect("temp root");

        let (response, shutdown) = super::handle_line(
            root.path(),
            r#"{"request_id":"stop-2","payload":{"command":"shutdown"}}"#,
        );
        let response: Value = serde_json::from_str(&response).expect("response json");

        assert!(shutdown);
        assert_eq!(response["request_id"], "stop-2");
        assert_eq!(response["status"], "ok");
        assert_eq!(response["result"], "shutdown");
    }

    #[test]
    fn daemon_artifact_paths_live_under_vibelign_metadata() {
        let root = TempDir::new().expect("temp root");

        assert_eq!(socket_path(root.path()), root.path().join(".vibelign").join("engine.sock"));
        assert_eq!(pid_path(root.path()), root.path().join(".vibelign").join("engine.pid"));
    }

    #[cfg(unix)]
    #[test]
    fn stale_daemon_artifacts_are_removed_before_bind() {
        let root = TempDir::new().expect("temp root");
        let meta_dir = root.path().join(".vibelign");
        std::fs::create_dir_all(&meta_dir).expect("metadata dir");
        let socket = socket_path(root.path());
        let pid = pid_path(root.path());
        std::fs::write(&socket, "stale socket placeholder").expect("stale socket");
        std::fs::write(&pid, "12345\n").expect("stale pid");

        super::unix::prepare_daemon_artifacts(&socket, &pid).expect("stale cleanup");

        assert!(!socket.exists());
        assert!(!pid.exists());
    }

    #[cfg(unix)]
    #[test]
    fn idle_expiration_uses_configured_timeout_boundary() {
        let start = std::time::Instant::now();
        let timeout = std::time::Duration::from_millis(100);

        assert!(!super::unix::idle_expired(
            start,
            start + std::time::Duration::from_millis(99),
            timeout,
        ));
        assert!(super::unix::idle_expired(
            start,
            start + std::time::Duration::from_millis(100),
            timeout,
        ));
    }
}
// === ANCHOR: DAEMON_END ===
