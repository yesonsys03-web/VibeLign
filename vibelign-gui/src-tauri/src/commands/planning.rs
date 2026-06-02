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
    adapter: Option<String>,
    persona_id: Option<String>,
    llm_status: Option<String>,
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
    fallback_reason: String,
    session_id: String,
    adapter: Option<String>,
    persona_id: Option<String>,
    llm_status: Option<String>,
}

fn planning_error(details: impl Into<String>) -> CreatePlanningTemplateResponse {
    CreatePlanningTemplateResponse {
        ok: false,
        output_path: None,
        absolute_output_path: None,
        markdown: None,
        fallback_reason: None,
        session_id: None,
        adapter: None,
        persona_id: None,
        llm_status: None,
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
        fallback_reason: Some(payload.fallback_reason),
        session_id: Some(payload.session_id),
        adapter: payload.adapter,
        persona_id: payload.persona_id,
        llm_status: payload.llm_status,
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
        cmd.args(["plan", &prompt, "--json", "--language", &request.language]);
        if let Some(cli) = request.cli.as_deref() {
            cmd.args(["--cli", cli]);
        }
        cmd.current_dir(&project_dir);
        cmd.stdin(std::process::Stdio::null());
        cmd.env("PATH", augmented_vib_path());
        cmd.env("NO_COLOR", "1");
        cmd.env("PYTHONUTF8", "1");
        cmd.env("PYTHONIOENCODING", "utf-8");
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

#[cfg(test)]
mod tests {
    use super::{parse_plan_stdout, planning_error};

    #[test]
    fn parses_success_json_from_stdout() {
        let response = parse_plan_stdout(
            r##"{"ok":true,"output_path":"plans/app.md","absolute_output_path":"/tmp/app/plans/app.md","markdown":"# App","fallback_reason":"cli_unavailable_template_only","session_id":"plan_1","adapter":"codex","persona_id":"gio","llm_status":"not_installed"}"##,
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
}
