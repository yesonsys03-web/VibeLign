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
    PlanningSessionSummary, SavePlanningChatPlanRequest,
};
use super::planning_chat_cards::{extract_and_apply, read_cards};
use super::planning_persona::{is_persona_enabled, run_persona_response, PlanningChatLine};

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
            provider_used: None,
            fallback_reason: None,
        }];
        if let Err(error) = write_json(session_dir.join("session.json"), &session) {
            return planning_chat_error(error);
        }
        if let Err(error) = write_json(session_dir.join("messages.json"), &messages) {
            return planning_chat_error(error);
        }
        planning_chat_success(session, messages, None, Vec::new())
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

fn load_session_from_dir(
    project_dir: &std::path::Path,
    session_dir: &std::path::Path,
) -> PlanningChatSessionResponse {
    let session = match read_json::<StoredPlanningChatSession>(&session_dir.join("session.json")) {
        Ok(parsed) => parsed,
        Err(error) => return planning_chat_error(error),
    };
    let messages = match read_json::<Vec<PlanningChatMessage>>(&session_dir.join("messages.json")) {
        Ok(parsed) => parsed,
        Err(error) => return planning_chat_error(error),
    };
    let markdown = read_saved_markdown(project_dir, &session);
    let cards = super::planning_chat_cards::read_cards(session_dir);
    planning_chat_success(session, messages, markdown, cards)
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
        let session_dir = session_path
            .parent()
            .map(|path| path.to_path_buf())
            .unwrap_or_else(|| project_dir.clone());
        load_session_from_dir(&project_dir, &session_dir)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn load_planning_chat_session(
    project_dir: String,
    session_id: String,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }
    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&session_id);
        if !session_dir.join("session.json").exists() {
            return planning_chat_error("planning chat session not found");
        }
        load_session_from_dir(&project_dir, &session_dir)
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
        let turn_start = messages.len();
        if request.include_user_message.unwrap_or(true) {
            messages.push(PlanningChatMessage {
                id: format!("msg_{}", timestamp_ms()),
                role: "user".to_string(),
                persona_id: None,
                content: prompt.clone(),
                status: "ok".to_string(),
                created_at: now.clone(),
                provider_used: None,
                fallback_reason: None,
            });
        }
        for agent in request.agents {
            if !is_persona_enabled(&agent) {
                continue;
            }
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
                provider_used: persona_run.provider_used,
                fallback_reason: persona_run.fallback_reason,
            });
        }
        let now = timestamp_ms().to_string();
        let turn = messages[turn_start..].to_vec();
        let cards = extract_and_apply(&project_dir, &session_dir, &messages, &turn, &now);
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
        planning_chat_success(session, messages, None, cards)
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
        session.readiness =
            Some(super::planning_chat_readiness::judge_readiness(&project_dir, &messages));
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
        let cards = read_cards(&session_dir);
        planning_chat_success(session, messages, Some(saved.markdown), cards)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

fn summary_title(idea: &str) -> String {
    idea.lines().next().unwrap_or("").trim().chars().take(60).collect()
}

fn list_sessions(project_dir: &std::path::Path) -> Vec<PlanningSessionSummary> {
    let dir = planning_dir(project_dir);
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return Vec::new();
    };
    let mut rows: Vec<(std::time::SystemTime, PlanningSessionSummary)> = Vec::new();
    for entry in entries.flatten() {
        let session_dir = entry.path();
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        if !session_path.exists() || !messages_path.exists() {
            continue;
        }
        let Ok(session) = read_json::<StoredPlanningChatSession>(&session_path) else {
            continue;
        };
        let messages = read_json::<Vec<PlanningChatMessage>>(&messages_path).unwrap_or_default();
        let cards = super::planning_chat_cards::read_cards(&session_dir);
        let modified = messages_path
            .metadata()
            .and_then(|meta| meta.modified())
            .unwrap_or(UNIX_EPOCH);
        rows.push((
            modified,
            PlanningSessionSummary {
                title: summary_title(&session.idea),
                saved: session.output_path.is_some(),
                output_path: session.output_path.clone(),
                created_at: session.created_at.clone(),
                message_count: messages.len(),
                card_count: cards.len(),
                session_id: session.session_id,
            },
        ));
    }
    rows.sort_by(|a, b| b.0.cmp(&a.0));
    rows.into_iter().map(|(_, summary)| summary).collect()
}

#[tauri::command]
pub(crate) async fn list_planning_chat_sessions(project_dir: String) -> Vec<PlanningSessionSummary> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Vec::new();
    }
    tauri::async_runtime::spawn_blocking(move || list_sessions(&project_dir))
        .await
        .unwrap_or_default()
}

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_session(root: &std::path::Path, id: &str, idea: &str, output: Option<&str>, msgs: usize, cards: usize) {
        let dir = root.join(".vibelign/planning").join(id);
        std::fs::create_dir_all(&dir).expect("mkdir");
        let output_json = match output {
            Some(p) => format!("\"{p}\""),
            None => "null".to_string(),
        };
        std::fs::write(
            dir.join("session.json"),
            format!(
                "{{\"schema_version\":1,\"session_id\":\"{id}\",\"idea\":\"{idea}\",\"mode\":\"chat\",\"created_at\":\"1\",\"output_path\":{output_json}}}"
            ),
        )
        .expect("session");
        let msg = "{\"id\":\"m\",\"role\":\"user\",\"personaId\":null,\"content\":\"hi\",\"status\":\"ok\",\"createdAt\":\"1\"}";
        let arr = vec![msg; msgs].join(",");
        std::fs::write(dir.join("messages.json"), format!("[{arr}]")).expect("messages");
        let card = "{\"id\":\"c\",\"title\":\"t\",\"summary\":\"\",\"reason\":\"\",\"state\":\"draft\",\"createdAt\":\"1\",\"updatedAt\":\"1\"}";
        let carr = vec![card; cards].join(",");
        std::fs::write(dir.join("cards.json"), format!("{{\"cards\":[{carr}]}}")).expect("cards");
    }

    #[test]
    fn list_sessions_returns_summaries_with_saved_flag_and_counts() {
        let root = tempfile::tempdir().expect("root");
        write_session(root.path(), "chat_1", "예약 앱", None, 2, 1);
        write_session(root.path(), "chat_2", "카드 흐름", Some("plans/a.md"), 4, 3);

        let summaries = list_sessions(root.path());

        assert_eq!(summaries.len(), 2);
        let saved = summaries.iter().find(|s| s.session_id == "chat_2").expect("chat_2");
        assert!(saved.saved);
        assert_eq!(saved.output_path.as_deref(), Some("plans/a.md"));
        assert_eq!(saved.title, "카드 흐름");
        assert_eq!(saved.message_count, 4);
        assert_eq!(saved.card_count, 3);
        let draft = summaries.iter().find(|s| s.session_id == "chat_1").expect("chat_1");
        assert!(!draft.saved);
        assert_eq!(draft.message_count, 2);
    }

    #[test]
    fn list_sessions_skips_dirs_without_messages() {
        let root = tempfile::tempdir().expect("root");
        let dir = root.path().join(".vibelign/planning/chat_x");
        std::fs::create_dir_all(&dir).expect("mkdir");
        std::fs::write(dir.join("session.json"), "{}").expect("session");
        assert!(list_sessions(root.path()).is_empty());
    }

    #[test]
    fn load_session_from_dir_reads_messages_and_cards() {
        let root = tempfile::tempdir().expect("root");
        write_session(root.path(), "chat_9", "복원 테스트", Some("plans/x.md"), 3, 2);
        let session_dir = root.path().join(".vibelign/planning/chat_9");

        let response = load_session_from_dir(root.path(), &session_dir);

        let json = serde_json::to_value(&response).expect("json");
        assert_eq!(json["ok"], true);
        assert_eq!(json["sessionId"], "chat_9");
        assert_eq!(json["messages"].as_array().expect("messages").len(), 3);
        assert_eq!(json["cards"].as_array().expect("cards").len(), 2);
        assert_eq!(json["outputPath"], "plans/x.md");
    }
}
// === ANCHOR: PLANNING_CHAT_END ===
