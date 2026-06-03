use super::{plan_slug, save_planning_markdown, synthesize_planning_markdown};
use crate::commands::planning_chat_store::StoredPlanningChatSession;
use crate::commands::planning_chat_types::PlanningChatMessage;

#[test]
fn plan_slug_keeps_korean_and_removes_forbidden_characters() {
    assert_eq!(plan_slug("예약 앱: MVP/초안?"), "예약-앱-mvp초안");
    assert_eq!(plan_slug("con"), "planning-chat");
}

#[test]
fn synthesized_markdown_includes_persona_conversation() {
    let session = test_session("예약 앱 만들고 싶어");
    let messages = vec![
        test_message("user", None, "예약 앱 만들고 싶어"),
        test_message("assistant", Some("chloe"), "핵심 플로우를 먼저 정리해요."),
    ];

    let markdown = synthesize_planning_markdown(&session, &messages);

    assert!(markdown.contains("# 예약 앱 만들고 싶어"));
    assert!(markdown.contains("## 기획방 대화 정리"));
    assert!(markdown.contains("### 클로이의 정리"));
    assert!(markdown.contains("> 핵심 플로우를 먼저 정리해요."));
}

#[test]
fn save_planning_markdown_writes_unique_plan_file() {
    let root = tempfile::tempdir().expect("temp root");
    let mut session = test_session("예약 앱 만들고 싶어");
    let messages = vec![test_message("user", None, "예약 앱 만들고 싶어")];

    let saved = save_planning_markdown(root.path(), &mut session, &messages).expect("save");

    assert_eq!(
        session.output_path.as_deref(),
        Some("plans/예약-앱-만들고-싶어.md")
    );
    assert!(root.path().join("plans/예약-앱-만들고-싶어.md").exists());
    assert!(saved.markdown.contains("# 예약 앱 만들고 싶어"));
}

fn test_session(idea: &str) -> StoredPlanningChatSession {
    StoredPlanningChatSession {
        schema_version: 1,
        session_id: "chat_1".to_string(),
        idea: idea.to_string(),
        mode: "chat".to_string(),
        created_at: "1".to_string(),
        output_path: None,
        absolute_output_path: None,
    }
}

fn test_message(role: &str, persona_id: Option<&str>, content: &str) -> PlanningChatMessage {
    PlanningChatMessage {
        id: "msg_1".to_string(),
        role: role.to_string(),
        persona_id: persona_id.map(str::to_string),
        content: content.to_string(),
        status: "ok".to_string(),
        created_at: "1".to_string(),
    }
}
