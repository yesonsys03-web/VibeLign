// === ANCHOR: PLANNING_CHAT_MARKDOWN_START ===
use super::planning_chat_store::StoredPlanningChatSession;
use super::planning_chat_types::PlanningChatMessage;

#[derive(Default)]
struct PlanningSections {
    features: Vec<String>,
    flows: Vec<String>,
    exclusions: Vec<String>,
    questions: Vec<String>,
}

pub(crate) fn synthesize_planning_markdown(
    session: &StoredPlanningChatSession,
    messages: &[PlanningChatMessage],
) -> String {
    let title = title_from_idea(&session.idea);
    let sections = PlanningSections::from_messages(messages);
    let mut markdown = String::new();
    push_section(&mut markdown, &format!("# {title}"));
    push_section(&mut markdown, "## 한 줄 목표");
    push_section(&mut markdown, session.idea.trim());
    push_section(&mut markdown, "## 대상 사용자");
    push_section(
        &mut markdown,
        "- 기획방 대화에서 대상 사용자를 구체화합니다.",
    );
    push_section(&mut markdown, "## 핵심 문제");
    push_section(
        &mut markdown,
        "- 사용자가 처음 말한 목표와 이후 페르소나 검토를 기준으로 확정합니다.",
    );
    push_section(&mut markdown, "## 핵심 기능");
    push_bullets_or_default(
        &mut markdown,
        &sections.features,
        "- 기획방 대화에서 합의된 기능을 구현 전에 우선순위로 정리합니다.",
    );
    push_section(&mut markdown, "## 사용자 흐름");
    push_bullets_or_default(
        &mut markdown,
        &sections.flows,
        "- 대화에서 정리된 화면 흐름과 저장 흐름을 기준으로 작성합니다.",
    );
    push_section(&mut markdown, "## 기획방 대화 정리");
    append_conversation(&mut markdown, messages);
    push_section(&mut markdown, "## 제외할 것");
    push_bullets_or_default(
        &mut markdown,
        &sections.exclusions,
        "- 아직 명시적으로 결정되지 않았습니다.",
    );
    push_section(&mut markdown, "## 아직 결정이 필요한 질문");
    push_bullets_or_default(
        &mut markdown,
        &sections.questions,
        "- 첫 구현 범위와 우선순위를 확정해야 합니다.\n- 화면 진입 후 저장/공유 흐름을 확정해야 합니다.",
    );
    push_section(&mut markdown, "## 구현 전에 AI가 알아야 할 맥락");
    push_section(
        &mut markdown,
        &format!(
            "- 이 문서는 기획방 대화를 기반으로 결정적으로 생성되었습니다.\n- 원본 대화는 `.vibelign/planning/{}/messages.json` 에 저장됩니다.",
            session.session_id
        ),
    );
    markdown
}

impl PlanningSections {
    fn from_messages(messages: &[PlanningChatMessage]) -> Self {
        let mut sections = Self::default();
        for message in messages {
            if message.role == "user" || message.status != "ok" {
                continue;
            }
            sections.collect_message(&message.content);
        }
        sections
    }

    fn collect_message(&mut self, content: &str) {
        for line in content.lines() {
            let Some((label, value)) = labeled_value(line) else {
                continue;
            };
            if matches_label(label, &["핵심 기능", "기능", "features", "feature"]) {
                push_unique(&mut self.features, value);
            } else if matches_label(label, &["사용자 흐름", "흐름", "flow", "user flow"]) {
                push_unique(&mut self.flows, value);
            } else if matches_label(
                label,
                &["제외할 것", "제외", "하지 않을 것", "out of scope"],
            ) {
                push_unique(&mut self.exclusions, value);
            } else if matches_label(
                label,
                &["질문", "결정", "결정 필요", "확인 필요", "question"],
            ) {
                push_unique(&mut self.questions, value);
            }
        }
    }
}

fn labeled_value(line: &str) -> Option<(&str, String)> {
    let trimmed = line.trim().trim_start_matches(['-', '*']).trim();
    let (label, value) = trimmed
        .split_once(':')
        .or_else(|| trimmed.split_once('：'))?;
    let value = value.trim();
    if label.trim().is_empty() || value.is_empty() {
        return None;
    }
    Some((label.trim(), value.to_string()))
}

fn matches_label(label: &str, candidates: &[&str]) -> bool {
    let normalized = label.trim().to_lowercase();
    candidates.iter().any(|candidate| normalized == *candidate)
}

fn push_unique(items: &mut Vec<String>, value: String) {
    if !items.iter().any(|item| item == &value) {
        items.push(value);
    }
}

fn push_bullets_or_default(markdown: &mut String, items: &[String], fallback: &str) {
    if items.is_empty() {
        push_section(markdown, fallback);
        return;
    }
    let bullets = items
        .iter()
        .map(|item| format!("- {}", item.trim()))
        .collect::<Vec<_>>()
        .join("\n");
    push_section(markdown, &bullets);
}

fn append_conversation(markdown: &mut String, messages: &[PlanningChatMessage]) {
    if messages.is_empty() {
        push_section(markdown, "- 아직 저장된 대화가 없습니다.");
        return;
    }
    for message in messages {
        let label = message_label(message);
        push_section(markdown, &format!("### {label}"));
        if message.status != "ok" {
            push_section(markdown, &format!("- 응답 상태: {}", message.status));
        }
        push_section(markdown, &quote_block(&message.content));
    }
}

fn title_from_idea(idea: &str) -> String {
    let trimmed = idea.trim();
    if trimmed.is_empty() {
        "기획안".to_string()
    } else {
        trimmed
            .lines()
            .next()
            .unwrap_or("기획안")
            .trim()
            .to_string()
    }
}

fn message_label(message: &PlanningChatMessage) -> String {
    if message.role == "user" {
        return "사용자".to_string();
    }
    match message.persona_id.as_deref() {
        Some("chloe") => "클로이의 정리".to_string(),
        Some("gio") => "지오의 검토".to_string(),
        Some("mina") => "미나의 탐색".to_string(),
        Some(persona_id) => format!("{persona_id}의 답변"),
        None => "AI 답변".to_string(),
    }
}

fn quote_block(content: &str) -> String {
    let trimmed = content.trim();
    if trimmed.is_empty() {
        return "> (내용 없음)".to_string();
    }
    trimmed
        .lines()
        .map(|line| {
            if line.trim().is_empty() {
                ">".to_string()
            } else {
                format!("> {}", line.trim_end())
            }
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn push_section(markdown: &mut String, section: &str) {
    markdown.push_str(section);
    markdown.push_str("\n\n");
}
// === ANCHOR: PLANNING_CHAT_MARKDOWN_END ===
