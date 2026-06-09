// === ANCHOR: PLANNING_CHAT_TYPES_START ===
use serde::{Deserialize, Serialize};

use super::planning_chat_cards::Card;
use super::planning_chat_readiness::ReadinessReport;
use super::planning_chat_store::StoredPlanningChatSession;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatePlanningChatSessionRequest {
    pub(crate) project_dir: String,
    pub(crate) prompt: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppendPlanningChatTurnRequest {
    pub(crate) project_dir: String,
    pub(crate) session_id: String,
    pub(crate) prompt: String,
    pub(crate) agents: Vec<String>,
    pub(crate) include_user_message: Option<bool>,
    pub(crate) extract_cards: Option<bool>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SavePlanningChatPlanRequest {
    pub(crate) project_dir: String,
    pub(crate) session_id: String,
    #[serde(default)]
    pub(crate) target_path: Option<String>,
    /// 저장 입구 출처 로깅용("button" | "slash"). 누락 시 카운트 안 함.
    #[serde(default)]
    pub(crate) source: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq, Clone)]
#[serde(rename_all = "camelCase")]
pub struct PlanningChatMessage {
    pub(crate) id: String,
    pub(crate) role: String,
    pub(crate) persona_id: Option<String>,
    pub(crate) content: String,
    pub(crate) status: String,
    pub(crate) created_at: String,
    #[serde(default)]
    pub(crate) provider_used: Option<String>,
    #[serde(default)]
    pub(crate) fallback_reason: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PlanningChatSessionResponse {
    ok: bool,
    session_id: Option<String>,
    prompt: Option<String>,
    messages: Vec<PlanningChatMessage>,
    output_path: Option<String>,
    absolute_output_path: Option<String>,
    markdown: Option<String>,
    error_code: Option<String>,
    message: Option<String>,
    details: Option<String>,
    readiness: Option<ReadinessReport>,
    cards: Vec<Card>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PlanningSessionSummary {
    pub(crate) session_id: String,
    pub(crate) title: String,
    pub(crate) output_path: Option<String>,
    pub(crate) saved: bool,
    pub(crate) created_at: String,
    pub(crate) message_count: usize,
    pub(crate) card_count: usize,
}

pub(crate) fn planning_chat_error(details: impl Into<String>) -> PlanningChatSessionResponse {
    PlanningChatSessionResponse {
        ok: false,
        session_id: None,
        prompt: None,
        messages: Vec::new(),
        output_path: None,
        absolute_output_path: None,
        markdown: None,
        error_code: Some("PLANNING_CHAT_FAILED".to_string()),
        message: Some("기획방 대화를 준비하지 못했어요.".to_string()),
        details: Some(details.into()),
        readiness: None,
        cards: Vec::new(),
    }
}

pub(crate) fn planning_chat_success(
    session: StoredPlanningChatSession,
    messages: Vec<PlanningChatMessage>,
    markdown: Option<String>,
    cards: Vec<Card>,
) -> PlanningChatSessionResponse {
    let readiness = session.readiness.clone();
    PlanningChatSessionResponse {
        ok: true,
        session_id: Some(session.session_id),
        prompt: Some(session.idea),
        messages,
        output_path: session.output_path,
        absolute_output_path: session.absolute_output_path,
        markdown,
        error_code: None,
        message: None,
        details: None,
        readiness,
        cards,
    }
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
            provider_used: Some("codex".to_string()),
            fallback_reason: Some("not_logged_in".to_string()),
        };

        let json = serde_json::to_string(&message).expect("json");

        assert!(json.contains("personaId"));
        assert!(json.contains("createdAt"));
        assert!(json.contains("providerUsed"));
        assert!(json.contains("fallbackReason"));
    }
}
// === ANCHOR: PLANNING_CHAT_TYPES_END ===
