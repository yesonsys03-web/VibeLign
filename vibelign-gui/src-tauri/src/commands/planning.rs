// === ANCHOR: PLANNING_START ===
use std::collections::HashMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::vib_path;

use super::platform::{augmented_vib_path, hide_console};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatePlanningTemplateRequest {
    project_dir: String,
    prompt: String,
    language: String,
    cli: Option<String>,
    agents: Option<Vec<String>>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppendPlanningAgentsRequest {
    project_dir: String,
    output_path: String,
    prompt: String,
    cli: Option<String>,
    agents: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct CreatePlanningTemplateResponse {
    ok: bool,
    output_path: Option<String>,
    absolute_output_path: Option<String>,
    markdown: Option<String>,
    fallback_reason: Option<String>,
    session_id: Option<String>,
    prompt: Option<String>,
    adapter: Option<String>,
    persona_id: Option<String>,
    llm_status: Option<String>,
    agents_requested: Vec<String>,
    agents_used: Vec<String>,
    agent_statuses: HashMap<String, String>,
    error_code: Option<String>,
    message: Option<String>,
    details: Option<String>,
}

#[derive(Deserialize)]
struct VibPlanJson {
    ok: bool,
    output_path: String,
    absolute_output_path: String,
    markdown: String,
    fallback_reason: Option<String>,
    session_id: String,
    adapter: Option<String>,
    persona_id: Option<String>,
    llm_status: Option<String>,
    #[serde(default)]
    agents_requested: Vec<String>,
    #[serde(default)]
    agents_used: Vec<String>,
    #[serde(default)]
    agent_statuses: HashMap<String, String>,
}

#[derive(Deserialize)]
struct StoredPlanningSession {
    session_id: String,
    idea: String,
    output_path: String,
    fallback_reason: Option<String>,
}

fn planning_error(details: impl Into<String>) -> CreatePlanningTemplateResponse {
    CreatePlanningTemplateResponse {
        ok: false,
        output_path: None,
        absolute_output_path: None,
        markdown: None,
        fallback_reason: None,
        session_id: None,
        prompt: None,
        adapter: None,
        persona_id: None,
        llm_status: None,
        agents_requested: Vec::new(),
        agents_used: Vec::new(),
        agent_statuses: HashMap::new(),
        error_code: Some("PLANNING_TEMPLATE_FAILED".to_string()),
        message: Some("기획안을 만들지 못했어요.".to_string()),
        details: Some(details.into()),
    }
}

fn planning_success(payload: VibPlanJson) -> CreatePlanningTemplateResponse {
    if !payload.ok {
        return planning_error("vib plan returned ok=false");
    }
    CreatePlanningTemplateResponse {
        ok: true,
        output_path: Some(payload.output_path),
        absolute_output_path: Some(payload.absolute_output_path),
        markdown: Some(payload.markdown),
        fallback_reason: payload.fallback_reason,
        session_id: Some(payload.session_id),
        prompt: None,
        adapter: payload.adapter,
        persona_id: payload.persona_id,
        llm_status: payload.llm_status,
        agents_requested: payload.agents_requested,
        agents_used: payload.agents_used,
        agent_statuses: payload.agent_statuses,
        error_code: None,
        message: None,
        details: None,
    }
}

fn parse_plan_stdout(stdout: &str) -> Result<CreatePlanningTemplateResponse, String> {
    let line = stdout
        .lines()
        .rev()
        .find(|line| line.trim_start().starts_with('{'))
        .ok_or_else(|| "vib plan JSON output not found".to_string())?;
    serde_json::from_str::<VibPlanJson>(line)
        .map(planning_success)
        .map_err(|error| error.to_string())
}

fn apply_planning_command_env(cmd: &mut std::process::Command) {
    cmd.env("PATH", augmented_vib_path());
    cmd.env("NO_COLOR", "1");
    cmd.env("PYTHONUTF8", "1");
    cmd.env("PYTHONIOENCODING", "utf-8");
    #[cfg(debug_assertions)]
    if let Some(repo_root) = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(std::path::Path::parent)
    {
        cmd.env("PYTHONPATH", repo_root);
    }
}

fn latest_session_file(project_dir: &std::path::Path) -> Option<PathBuf> {
    let planning_dir = project_dir.join(".vibelign").join("planning");
    let mut entries = std::fs::read_dir(planning_dir)
        .ok()?
        .flatten()
        .filter_map(|entry| {
            let session_path = entry.path().join("session.json");
            let modified = session_path.metadata().ok()?.modified().ok()?;
            Some((modified, session_path))
        })
        .collect::<Vec<_>>();
    entries.sort_by_key(|(modified, _path)| *modified);
    entries.pop().map(|(_modified, path)| path)
}

fn relative_markdown_path(root: &std::path::Path, output_path: &str) -> Result<PathBuf, String> {
    let relative = PathBuf::from(output_path);
    if relative.is_absolute()
        || relative
            .components()
            .any(|part| matches!(part, std::path::Component::ParentDir))
    {
        return Err("invalid planning output path".to_string());
    }
    let absolute = root.join(&relative);
    let canonical_root = root.canonicalize().map_err(|error| error.to_string())?;
    let canonical_file = absolute.canonicalize().map_err(|error| error.to_string())?;
    if !canonical_file.starts_with(canonical_root) {
        return Err("planning output escapes project root".to_string());
    }
    Ok(relative)
}

#[tauri::command]
pub(crate) async fn create_planning_template(
    request: CreatePlanningTemplateRequest,
) -> CreatePlanningTemplateResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_error("prompt is required");
    }

    let vib = match vib_path::find_runtime_vib() {
        Some(path) => path,
        None => return planning_error("vib executable not found"),
    };

    tauri::async_runtime::spawn_blocking(move || {
        let mut cmd = std::process::Command::new(vib);
        cmd.args([
            "plan",
            &prompt,
            "--template-only",
            "--json",
            "--language",
            &request.language,
        ]);
        if let Some(cli) = request.cli.as_deref() {
            cmd.args(["--cli", cli]);
        }
        if let Some(agents) = request.agents.as_ref().filter(|items| !items.is_empty()) {
            cmd.args(["--agents", &agents.join(",")]);
        }
        cmd.current_dir(&project_dir);
        cmd.stdin(std::process::Stdio::null());
        apply_planning_command_env(&mut cmd);
        hide_console(&mut cmd);

        match cmd.output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                parse_plan_stdout(&stdout).unwrap_or_else(planning_error)
            }
            Ok(output) => planning_error(String::from_utf8_lossy(&output.stderr).into_owned()),
            Err(error) => planning_error(error.to_string()),
        }
    })
    .await
    .unwrap_or_else(|error| planning_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn append_planning_with_agents(
    request: AppendPlanningAgentsRequest,
) -> CreatePlanningTemplateResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_error("prompt is required");
    }
    if request.output_path.trim().is_empty() {
        return planning_error("outputPath is required");
    }

    let vib = match vib_path::find_runtime_vib() {
        Some(path) => path,
        None => return planning_error("vib executable not found"),
    };

    tauri::async_runtime::spawn_blocking(move || {
        let mut cmd = std::process::Command::new(vib);
        cmd.args([
            "plan",
            &prompt,
            "--append-to",
            &request.output_path,
            "--json",
            "--llm-timeout-seconds",
            "300",
        ]);
        if let Some(cli) = request.cli.as_deref() {
            cmd.args(["--cli", cli]);
        }
        if !request.agents.is_empty() {
            cmd.args(["--agents", &request.agents.join(",")]);
        }
        cmd.current_dir(&project_dir);
        cmd.stdin(std::process::Stdio::null());
        apply_planning_command_env(&mut cmd);
        hide_console(&mut cmd);

        match cmd.output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                parse_plan_stdout(&stdout).unwrap_or_else(planning_error)
            }
            Ok(output) => planning_error(String::from_utf8_lossy(&output.stderr).into_owned()),
            Err(error) => planning_error(error.to_string()),
        }
    })
    .await
    .unwrap_or_else(|error| planning_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn load_latest_planning_session(
    project_dir: String,
) -> CreatePlanningTemplateResponse {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return planning_error("projectDir must be absolute");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let Some(session_path) = latest_session_file(&project_dir) else {
            return planning_error("planning session not found");
        };
        let session_text = match std::fs::read_to_string(&session_path) {
            Ok(text) => text,
            Err(error) => return planning_error(error.to_string()),
        };
        let session = match serde_json::from_str::<StoredPlanningSession>(&session_text) {
            Ok(parsed) => parsed,
            Err(error) => return planning_error(error.to_string()),
        };
        let relative = match relative_markdown_path(&project_dir, &session.output_path) {
            Ok(path) => path,
            Err(error) => return planning_error(error),
        };
        let absolute = project_dir.join(&relative);
        let markdown = match std::fs::read_to_string(&absolute) {
            Ok(text) => text,
            Err(error) => return planning_error(error.to_string()),
        };

        CreatePlanningTemplateResponse {
            ok: true,
            output_path: Some(relative.to_string_lossy().replace('\\', "/")),
            absolute_output_path: Some(absolute.to_string_lossy().to_string()),
            markdown: Some(markdown),
            fallback_reason: session.fallback_reason,
            session_id: Some(session.session_id),
            prompt: Some(session.idea),
            adapter: None,
            persona_id: None,
            llm_status: None,
            agents_requested: Vec::new(),
            agents_used: Vec::new(),
            agent_statuses: HashMap::new(),
            error_code: None,
            message: None,
            details: None,
        }
    })
    .await
    .unwrap_or_else(|error| planning_error(error.to_string()))
}

#[cfg(test)]
mod tests {
    use std::fs;

    use super::{latest_session_file, parse_plan_stdout, planning_error, relative_markdown_path};

    #[test]
    fn parses_success_json_from_stdout() {
        let response = parse_plan_stdout(
            r##"{"ok":true,"output_path":"plans/app.md","absolute_output_path":"/tmp/app/plans/app.md","markdown":"# App","fallback_reason":"cli_unavailable_template_only","session_id":"plan_1","adapter":"codex","persona_id":"gio","llm_status":"not_installed","agents_requested":["gio"],"agents_used":[],"agent_statuses":{"gio":"not_installed"}}"##,
        )
        .expect("parse");

        assert!(response.ok);
        assert_eq!(response.output_path.as_deref(), Some("plans/app.md"));
        assert_eq!(
            response.fallback_reason.as_deref(),
            Some("cli_unavailable_template_only")
        );
        assert_eq!(response.adapter.as_deref(), Some("codex"));
        assert_eq!(response.persona_id.as_deref(), Some("gio"));
        assert_eq!(response.llm_status.as_deref(), Some("not_installed"));
        assert_eq!(response.agents_requested, vec!["gio".to_string()]);
        assert_eq!(response.agents_used, Vec::<String>::new());
        assert_eq!(
            response.agent_statuses.get("gio").map(String::as_str),
            Some("not_installed")
        );
    }

    #[test]
    fn parses_llm_success_with_null_fallback_reason() {
        let response = parse_plan_stdout(
            r##"{"ok":true,"output_path":"plans/app.md","absolute_output_path":"/tmp/app/plans/app.md","markdown":"# App\n\n## 지오의 검토\n좋아요.","fallback_reason":null,"session_id":"plan_1","adapter":"codex","persona_id":"gio","llm_status":"ok"}"##,
        )
        .expect("parse");

        assert!(response.ok);
        assert_eq!(response.fallback_reason, None);
        assert_eq!(response.llm_status.as_deref(), Some("ok"));
    }

    #[test]
    fn error_response_uses_pr3_contract() {
        let response = planning_error("boom");

        assert!(!response.ok);
        assert_eq!(
            response.error_code.as_deref(),
            Some("PLANNING_TEMPLATE_FAILED")
        );
        assert_eq!(
            response.message.as_deref(),
            Some("기획안을 만들지 못했어요.")
        );
        assert_eq!(response.details.as_deref(), Some("boom"));
    }

    #[test]
    fn finds_latest_planning_session_file() {
        let root = tempfile::tempdir().expect("temp root");
        let first = root.path().join(".vibelign/planning/plan_1/session.json");
        let second = root.path().join(".vibelign/planning/plan_2/session.json");
        fs::create_dir_all(first.parent().expect("first parent")).expect("first mkdir");
        fs::write(&first, "{}").expect("first write");
        std::thread::sleep(std::time::Duration::from_millis(5));
        fs::create_dir_all(second.parent().expect("second parent")).expect("second mkdir");
        fs::write(&second, "{}").expect("second write");

        let latest = latest_session_file(root.path()).expect("latest session");

        assert_eq!(latest, second);
    }

    #[test]
    fn validates_relative_markdown_path() {
        let root = tempfile::tempdir().expect("temp root");
        let markdown = root.path().join("plans/app.md");
        fs::create_dir_all(markdown.parent().expect("markdown parent")).expect("mkdir");
        fs::write(&markdown, "# App\n").expect("write");

        let relative = relative_markdown_path(root.path(), "plans/app.md").expect("relative");

        assert_eq!(relative, std::path::PathBuf::from("plans/app.md"));
        assert!(relative_markdown_path(root.path(), "../outside.md").is_err());
    }
}
// === ANCHOR: PLANNING_END ===
