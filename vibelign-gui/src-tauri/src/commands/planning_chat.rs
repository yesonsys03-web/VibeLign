use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

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

#[derive(Serialize, Deserialize)]
struct StoredPlanningChatSession {
    schema_version: u32,
    session_id: String,
    idea: String,
    mode: String,
    created_at: String,
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

fn planning_dir(project_dir: &Path) -> PathBuf {
    project_dir.join(".vibelign").join("planning")
}

fn latest_chat_session_file(project_dir: &Path) -> Option<PathBuf> {
    let mut entries = std::fs::read_dir(planning_dir(project_dir))
        .ok()?
        .flatten()
        .filter_map(|entry| {
            let session_path = entry.path().join("session.json");
            let messages_path = entry.path().join("messages.json");
            let modified = messages_path.metadata().ok()?.modified().ok()?;
            if session_path.exists() && messages_path.exists() {
                Some((modified, session_path))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();
    entries.sort_by_key(|(modified, _path)| *modified);
    entries.pop().map(|(_modified, path)| path)
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
            content: prompt,
            status: "ok".to_string(),
            created_at: now.clone(),
        });
        for agent in request.agents {
            messages.push(PlanningChatMessage {
                id: format!("msg_{}_{}", agent, timestamp_ms()),
                role: "assistant".to_string(),
                persona_id: Some(agent),
                content: "다음 단계에서 실제 페르소나 응답을 연결합니다.".to_string(),
                status: "pending".to_string(),
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

fn write_json<T: Serialize>(path: PathBuf, value: &T) -> Result<(), String> {
    std::fs::write(
        path,
        serde_json::to_string_pretty(value).map_err(|error| error.to_string())? + "\n",
    )
    .map_err(|error| error.to_string())
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let text = std::fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&text).map_err(|error| error.to_string())
}

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}

#[cfg(test)]
mod tests {
    use super::{latest_chat_session_file, PlanningChatMessage};

    #[test]
    fn latest_chat_session_requires_messages_file() {
        let root = tempfile::tempdir().expect("temp root");
        let session_dir = root.path().join(".vibelign/planning/chat_1");
        std::fs::create_dir_all(&session_dir).expect("mkdir");
        std::fs::write(session_dir.join("session.json"), "{}").expect("session");

        assert_eq!(latest_chat_session_file(root.path()), None);
    }

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

    #[test]
    fn latest_chat_session_picks_session_with_messages() {
        let root = tempfile::tempdir().expect("temp root");
        let session_dir = root.path().join(".vibelign/planning/chat_2");
        std::fs::create_dir_all(&session_dir).expect("mkdir");
        std::fs::write(session_dir.join("session.json"), "{}").expect("session");
        std::fs::write(session_dir.join("messages.json"), "[]").expect("messages");

        assert_eq!(
            latest_chat_session_file(root.path()),
            Some(session_dir.join("session.json"))
        );
    }
}
