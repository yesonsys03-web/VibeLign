use std::path::{Path, PathBuf};

use super::planning_chat_store::StoredPlanningChatSession;
use super::planning_chat_types::PlanningChatMessage;

pub(crate) struct SavedPlanningMarkdown {
    pub(crate) markdown: String,
}

pub(crate) fn save_planning_markdown(
    project_dir: &Path,
    session: &mut StoredPlanningChatSession,
    messages: &[PlanningChatMessage],
) -> Result<SavedPlanningMarkdown, String> {
    let markdown = synthesize_planning_markdown(session, messages);
    let (output_path, absolute_path) = match &session.output_path {
        Some(existing) => {
            let absolute = project_dir.join(existing);
            (existing.clone(), absolute)
        }
        None => unique_plan_path(project_dir, &session.idea)?,
    };
    if let Some(parent) = absolute_path.parent() {
        std::fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    std::fs::write(&absolute_path, &markdown).map_err(|error| error.to_string())?;
    let absolute_output_path = absolute_path.to_string_lossy().into_owned();
    session.output_path = Some(output_path.clone());
    session.absolute_output_path = Some(absolute_output_path.clone());
    Ok(SavedPlanningMarkdown { markdown })
}

pub(crate) fn read_saved_markdown(
    project_dir: &Path,
    session: &StoredPlanningChatSession,
) -> Option<String> {
    let output_path = session.output_path.as_ref()?;
    std::fs::read_to_string(project_dir.join(output_path)).ok()
}

fn synthesize_planning_markdown(
    session: &StoredPlanningChatSession,
    messages: &[PlanningChatMessage],
) -> String {
    let title = title_from_idea(&session.idea);
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
    push_section(
        &mut markdown,
        "- 기획방 대화에서 합의된 기능을 구현 전에 우선순위로 정리합니다.",
    );
    push_section(&mut markdown, "## 사용자 흐름");
    push_section(
        &mut markdown,
        "- 대화에서 정리된 화면 흐름과 저장 흐름을 기준으로 작성합니다.",
    );
    push_section(&mut markdown, "## 기획방 대화 정리");
    append_conversation(&mut markdown, messages);
    push_section(&mut markdown, "## 제외할 것");
    push_section(&mut markdown, "- 아직 명시적으로 결정되지 않았습니다.");
    push_section(&mut markdown, "## 아직 결정이 필요한 질문");
    push_section(
        &mut markdown,
        "- 첫 구현 범위와 우선순위를 확정해야 합니다.",
    );
    push_section(
        &mut markdown,
        "- 화면 진입 후 저장/공유 흐름을 확정해야 합니다.",
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

fn unique_plan_path(project_dir: &Path, idea: &str) -> Result<(String, PathBuf), String> {
    let plans_dir = project_dir.join("plans");
    std::fs::create_dir_all(&plans_dir).map_err(|error| error.to_string())?;
    let slug = plan_slug(idea);
    for index in 1..=999 {
        let file_name = if index == 1 {
            format!("{slug}.md")
        } else {
            format!("{slug}-{index}.md")
        };
        let relative = PathBuf::from("plans").join(&file_name);
        let absolute = project_dir.join(&relative);
        if !absolute.exists() {
            return Ok((relative.to_string_lossy().into_owned(), absolute));
        }
    }
    Err("available planning file name not found".to_string())
}

fn plan_slug(raw: &str) -> String {
    let mut slug = String::new();
    let mut previous_dash = false;
    for ch in raw.trim().chars().take(64) {
        if ch.is_whitespace() || ch == '_' || ch == '-' {
            push_dash(&mut slug, &mut previous_dash);
        } else if is_forbidden_file_char(ch) || ch.is_control() {
            continue;
        } else {
            previous_dash = false;
            for lowered in ch.to_lowercase() {
                slug.push(lowered);
            }
        }
    }
    let slug = slug.trim_matches(['-', '.']).to_string();
    if slug.is_empty() || is_windows_reserved_name(&slug) {
        "planning-chat".to_string()
    } else {
        slug
    }
}

fn push_dash(slug: &mut String, previous_dash: &mut bool) {
    if !*previous_dash && !slug.is_empty() {
        slug.push('-');
        *previous_dash = true;
    }
}

fn is_forbidden_file_char(ch: char) -> bool {
    matches!(ch, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*')
}

fn is_windows_reserved_name(slug: &str) -> bool {
    matches!(
        slug,
        "con"
            | "prn"
            | "aux"
            | "nul"
            | "com1"
            | "com2"
            | "com3"
            | "com4"
            | "com5"
            | "com6"
            | "com7"
            | "com8"
            | "com9"
            | "lpt1"
            | "lpt2"
            | "lpt3"
            | "lpt4"
            | "lpt5"
            | "lpt6"
            | "lpt7"
            | "lpt8"
            | "lpt9"
    )
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

#[cfg(test)]
#[path = "planning_chat_synthesis_tests.rs"]
mod tests;
