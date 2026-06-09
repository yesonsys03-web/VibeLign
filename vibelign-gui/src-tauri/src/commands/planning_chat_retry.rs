// === ANCHOR: PLANNING_CHAT_RETRY_START ===
use std::path::PathBuf;

use serde::Deserialize;

use super::planning_chat_cards::read_cards;
use super::planning_chat_store::{planning_dir, read_json, write_json, StoredPlanningChatSession};
use super::planning_chat_types::{
    planning_chat_error, planning_chat_success, PlanningChatMessage, PlanningChatSessionResponse,
};
use super::planning_persona::{run_persona_response, PlanningChatLine};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RetryPersonaRequest {
    pub(crate) project_dir: String,
    pub(crate) session_id: String,
    pub(crate) message_id: String,
}

/// 실패(또는 임의)한 페르소나 답변 1건을 그 자리에서 다시 생성해 교체한다.
/// 그 메시지 직전까지의 정상 대화만 맥락으로 쓰므로(자기 실패문구·이후 메시지 제외),
/// 대화 흐름을 깨지 않고 한 페르소나의 응답만 갱신한다. 카드 추출은 하지 않는다.
#[tauri::command]
pub(crate) async fn retry_planning_persona(
    request: RetryPersonaRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }
    if request.message_id.trim().is_empty() {
        return planning_chat_error("messageId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session = match read_json::<StoredPlanningChatSession>(&session_dir.join("session.json")) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let messages_path = session_dir.join("messages.json");
        let mut messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let Some(pos) = messages.iter().position(|m| m.id == request.message_id) else {
            return planning_chat_error("message not found");
        };
        let Some(persona_id) = messages[pos].persona_id.clone() else {
            return planning_chat_error("retry target is not a persona message");
        };
        // lines 의 불변 차용을 먼저 끝낸 뒤 messages 를 수정한다.
        let run = {
            let lines = messages[..pos]
                .iter()
                .filter(|m| m.status == "ok")
                .map(|m| PlanningChatLine {
                    role: &m.role,
                    persona_id: m.persona_id.as_deref(),
                    content: &m.content,
                })
                .collect::<Vec<_>>();
            run_persona_response(&project_dir, &persona_id, &lines)
        };
        messages[pos] = PlanningChatMessage {
            id: messages[pos].id.clone(),
            role: "assistant".to_string(),
            persona_id: Some(persona_id),
            content: run.content,
            status: run.status,
            created_at: messages[pos].created_at.clone(),
            provider_used: run.provider_used,
            fallback_reason: run.fallback_reason,
        };
        if let Err(error) = write_json(messages_path, &messages) {
            return planning_chat_error(error);
        }
        let cards = read_cards(&session_dir);
        planning_chat_success(session, messages, None, cards)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}
// === ANCHOR: PLANNING_CHAT_RETRY_END ===
