// === ANCHOR: PLANNING_CHAT_SYNTHESIS_TESTS_START ===
use super::{plan_slug, safe_relative_target, save_planning_markdown, synthesize_planning_markdown};
use crate::commands::planning_chat_cards::{Card, CardState};
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

    let markdown = synthesize_planning_markdown(&session, &messages, &[], None);

    assert!(markdown.contains("# 예약 앱 만들고 싶어"));
    assert!(markdown.contains("## 기획방 대화 정리"));
    assert!(markdown.contains("### 클로이의 정리"));
    assert!(markdown.contains("> 핵심 플로우를 먼저 정리해요."));
}

#[test]
fn synthesized_markdown_distributes_persona_sections() {
    let session = test_session("예약 앱 만들고 싶어");
    let messages = vec![
        test_message("user", None, "예약 앱 만들고 싶어"),
        test_message(
            "assistant",
            Some("chloe"),
            "핵심 기능: 예약 생성, 일정 변경\n사용자 흐름: 날짜 선택 후 예약 확정",
        ),
        test_message(
            "assistant",
            Some("gio"),
            "제외할 것: 결제 연동은 MVP에서 제외\n질문: 관리자 승인 방식 결정 필요",
        ),
    ];

    let markdown = synthesize_planning_markdown(&session, &messages, &[], None);

    assert_section_contains(&markdown, "## 핵심 기능", "- 예약 생성, 일정 변경");
    assert_section_contains(&markdown, "## 사용자 흐름", "- 날짜 선택 후 예약 확정");
    assert_section_contains(&markdown, "## 제외할 것", "- 결제 연동은 MVP에서 제외");
    assert_section_contains(
        &markdown,
        "## 아직 결정이 필요한 질문",
        "- 관리자 승인 방식 결정 필요",
    );
    assert_section_contains(
        &markdown,
        "## 기획방 대화 정리",
        "> 핵심 기능: 예약 생성, 일정 변경",
    );
}

#[test]
fn synthesized_markdown_includes_confirmed_cards_only() {
    let session = test_session("예약 앱 만들고 싶어");
    let messages = vec![test_message("user", None, "예약 앱 만들고 싶어")];
    let cards = vec![
        test_card("card_1", "결정 카드는 버튼으로 확정", "확정 흐름", CardState::Confirmed),
        test_card("card_2", "초안 카드는 안 나와야 함", "초안", CardState::Draft),
    ];

    let markdown = synthesize_planning_markdown(&session, &messages, &cards, None);

    assert_section_contains(
        &markdown,
        "## 확정된 결정",
        "- **결정 카드는 버튼으로 확정** — 확정 흐름",
    );
    assert!(!markdown.contains("초안 카드는 안 나와야 함"));
}

#[test]
fn synthesized_markdown_notes_when_no_confirmed_cards() {
    let session = test_session("예약 앱 만들고 싶어");
    let messages = vec![test_message("user", None, "예약 앱 만들고 싶어")];

    let markdown = synthesize_planning_markdown(&session, &messages, &[], None);

    assert_section_contains(&markdown, "## 확정된 결정", "- 아직 버튼으로 확정한 결정이 없습니다.");
}

#[test]
fn save_planning_markdown_writes_unique_plan_file() {
    let root = tempfile::tempdir().expect("temp root");
    let mut session = test_session("예약 앱 만들고 싶어");
    let messages = vec![test_message("user", None, "예약 앱 만들고 싶어")];

    let saved = save_planning_markdown(root.path(), &mut session, &messages, &[], None, None).expect("save");

    assert_eq!(
        session.output_path.as_deref(),
        Some("plans/예약-앱-만들고-싶어.md")
    );
    assert!(root.path().join("plans/예약-앱-만들고-싶어.md").exists());
    assert!(saved.markdown.contains("# 예약 앱 만들고 싶어"));
}

#[test]
fn save_planning_markdown_writes_explicit_target_path() {
    let root = tempfile::tempdir().expect("temp root");
    let mut session = test_session("예약 앱 만들고 싶어");
    let messages = vec![test_message("user", None, "예약 앱 만들고 싶어")];

    let saved = save_planning_markdown(
        root.path(),
        &mut session,
        &messages,
        &[],
        None,
        Some("docs/spec-foo-review.md"),
    )
    .expect("save");

    assert_eq!(session.output_path.as_deref(), Some("docs/spec-foo-review.md"));
    assert!(root.path().join("docs/spec-foo-review.md").exists());
    assert!(saved.markdown.contains("# 예약 앱 만들고 싶어"));
}

#[test]
fn safe_relative_target_rejects_unsafe_paths() {
    assert!(safe_relative_target("../outside.md").is_err());
    assert!(safe_relative_target("/etc/passwd").is_err());
    assert_eq!(
        safe_relative_target("docs/spec-foo-review.md").expect("ok"),
        std::path::PathBuf::from("docs/spec-foo-review.md")
    );
}

fn assert_section_contains(markdown: &str, heading: &str, expected: &str) {
    let start = markdown.find(heading).expect("heading");
    let rest = &markdown[start + heading.len()..];
    let end = rest.find("\n## ").unwrap_or(rest.len());
    assert!(
        rest[..end].contains(expected),
        "section {heading} did not contain {expected}"
    );
}

#[test]
fn save_planning_markdown_resets_doc_stale() {
    let root = tempfile::tempdir().expect("temp root");
    let mut session = test_session("예약 앱");
    session.output_path = Some("plans/a.md".to_string());
    session.doc_stale = true;

    save_planning_markdown(root.path(), &mut session, &[], &[], None, None).expect("save");

    assert!(!session.doc_stale); // 저장 직후엔 문서가 대화와 동기화 상태
    assert_eq!(session.output_path.as_deref(), Some("plans/a.md"));
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
        doc_stale: false,
        readiness: None,
    }
}

fn test_card(id: &str, title: &str, summary: &str, state: CardState) -> Card {
    Card {
        id: id.to_string(),
        title: title.to_string(),
        summary: summary.to_string(),
        reason: String::new(),
        state,
        created_at: "1".to_string(),
        updated_at: "1".to_string(),
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
        provider_used: None,
        fallback_reason: None,
    }
}
// === ANCHOR: PLANNING_CHAT_SYNTHESIS_TESTS_END ===
