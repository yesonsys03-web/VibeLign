// === ANCHOR: PLANNING_CHAT_START ===
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use super::planning_chat_store::{
    latest_chat_session_file, planning_dir, read_json, write_json, StoredPlanningChatSession,
};
use super::planning_chat_synthesis::{read_saved_markdown, save_planning_markdown};
use super::planning_chat_types::{
    planning_chat_error, planning_chat_success, AppendPlanningChatTurnRequest,
    CreatePlanningChatSessionRequest, PlanningChatMessage, PlanningChatSessionResponse,
    SavePlanningChatPlanRequest,
};
use super::planning_persona::{run_persona_response, PlanningChatLine};

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
            output_path: None,
            absolute_output_path: None,
            readiness: None,
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
        planning_chat_success(session, messages, None)
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
        let markdown = read_saved_markdown(&project_dir, &session);
        planning_chat_success(session, messages, markdown)
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
        let mut session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let mut messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let now = timestamp_ms().to_string();
        if request.include_user_message.unwrap_or(true) {
            messages.push(PlanningChatMessage {
                id: format!("msg_{}", timestamp_ms()),
                role: "user".to_string(),
                persona_id: None,
                content: prompt.clone(),
                status: "ok".to_string(),
                created_at: now.clone(),
            });
        }
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
        if session.output_path.is_some() || session.absolute_output_path.is_some() {
            session.output_path = None;
            session.absolute_output_path = None;
            if let Err(error) = write_json(session_path, &session) {
                return planning_chat_error(error);
            }
        }
        planning_chat_success(session, messages, None)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn save_planning_chat_as_markdown(
    request: SavePlanningChatPlanRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        let mut session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let saved = match save_planning_markdown(
            &project_dir,
            &mut session,
            &messages,
            request.target_path.as_deref(),
        ) {
            Ok(saved) => saved,
            Err(error) => return planning_chat_error(error),
        };
        if let Err(error) = write_json(session_path, &session) {
            return planning_chat_error(error);
        }
        planning_chat_success(session, messages, Some(saved.markdown))
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}
// === ANCHOR: PLANNING_CHAT_END ===
