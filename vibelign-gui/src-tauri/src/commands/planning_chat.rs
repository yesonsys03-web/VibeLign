use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

use super::planning_chat_store::{
    latest_chat_session_file, planning_dir, read_json, write_json, StoredPlanningChatSession,
};
use super::planning_persona::{run_persona_response, PlanningChatLine};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatePlanningChatSessionRequest {
    project_dir: String,
    prompt: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppendPlanningChatTurnRequest {
    project_dir: String,
    session_id: String,
    prompt: String,
    agents: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq, Clone)]
#[serde(rename_all = "camelCase")]
pub struct PlanningChatMessage {
    id: String,
    role: String,
    persona_id: Option<String>,
    content: String,
    status: String,
    created_at: String,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PlanningChatSessionResponse {
    ok: bool,
    session_id: Option<String>,
    prompt: Option<String>,
    messages: Vec<PlanningChatMessage>,
    error_code: Option<String>,
    message: Option<String>,
    details: Option<String>,
}

fn planning_chat_error(details: impl Into<String>) -> PlanningChatSessionResponse {
    PlanningChatSessionResponse {
        ok: false,
        session_id: None,
        prompt: None,
        messages: Vec::new(),
        error_code: Some("PLANNING_CHAT_FAILED".to_string()),
        message: Some("기획방 대화를 준비하지 못했어요.".to_string()),
        details: Some(details.into()),
    }
}

#[tauri::command]
pub(crate) async fn create_planning_chat_session(
    request: CreatePlanningChatSessionRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_chat_error("prompt is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let now = timestamp_ms().to_string();
        let session_id = format!("chat_{}_{}", now, std::process::id());
        let session_dir = planning_dir(&project_dir).join(&session_id);
        if let Err(error) = std::fs::create_dir_all(&session_dir) {
            return planning_chat_error(error.to_string());
        }
        let session = StoredPlanningChatSession {
            schema_version: 1,
            session_id: session_id.clone(),
            idea: prompt.clone(),
            mode: "chat".to_string(),
            created_at: now.clone(),
        };
        let messages = vec![PlanningChatMessage {
            id: format!("msg_{}", timestamp_ms()),
            role: "user".to_string(),
            persona_id: None,
            content: prompt.clone(),
            status: "ok".to_string(),
            created_at: now,
        }];
        if let Err(error) = write_json(session_dir.join("session.json"), &session) {
            return planning_chat_error(error);
        }
        if let Err(error) = write_json(session_dir.join("messages.json"), &messages) {
            return planning_chat_error(error);
        }
        PlanningChatSessionResponse {
            ok: true,
            session_id: Some(session_id),
            prompt: Some(prompt),
            messages,
            error_code: None,
            message: None,
            details: None,
        }
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn load_latest_planning_chat_session(
    project_dir: String,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let Some(session_path) = latest_chat_session_file(&project_dir) else {
            return planning_chat_error("planning chat session not found");
        };
        let session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let messages_path = session_path
            .parent()
            .map(|path| path.join("messages.json"))
            .unwrap_or_else(|| PathBuf::from("messages.json"));
        let messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        PlanningChatSessionResponse {
            ok: true,
            session_id: Some(session.session_id),
            prompt: Some(session.idea),
            messages,
            error_code: None,
            message: None,
            details: None,
        }
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn append_planning_chat_turn(
    request: AppendPlanningChatTurnRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_chat_error("prompt is required");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        let session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let mut messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let now = timestamp_ms().to_string();
        messages.push(PlanningChatMessage {
            id: format!("msg_{}", timestamp_ms()),
            role: "user".to_string(),
            persona_id: None,
            content: prompt.clone(),
            status: "ok".to_string(),
            created_at: now.clone(),
        });
        for agent in request.agents {
            let lines = messages
                .iter()
                .map(|message| PlanningChatLine {
                    role: &message.role,
                    persona_id: message.persona_id.as_deref(),
                    content: &message.content,
                })
                .collect::<Vec<_>>();
            let persona_run = run_persona_response(&project_dir, &agent, &lines);
            messages.push(PlanningChatMessage {
                id: format!("msg_{}_{}", agent, timestamp_ms()),
                role: "assistant".to_string(),
                persona_id: Some(agent),
                content: persona_run.content,
                status: persona_run.status,
                created_at: now.clone(),
            });
        }
        if let Err(error) = write_json(messages_path, &messages) {
            return planning_chat_error(error);
        }
        PlanningChatSessionResponse {
            ok: true,
            session_id: Some(session.session_id),
            prompt: Some(session.idea),
            messages,
            error_code: None,
            message: None,
            details: None,
        }
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}

#[cfg(test)]
mod tests {
    use super::PlanningChatMessage;

    #[test]
    fn planning_chat_message_serializes_camel_case() {
        let message = PlanningChatMessage {
            id: "msg_1".to_string(),
            role: "assistant".to_string(),
            persona_id: Some("chloe".to_string()),
            content: "좋아요.".to_string(),
            status: "ok".to_string(),
            created_at: "2026-06-02T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&message).expect("json");

        assert!(json.contains("personaId"));
        assert!(json.contains("createdAt"));
    }
}
