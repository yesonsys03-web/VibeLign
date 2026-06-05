// === ANCHOR: PLANNING_CHAT_SYNTHESIS_START ===
use std::path::{Component, Path, PathBuf};

use super::planning_chat_markdown::synthesize_planning_markdown;
use super::planning_chat_store::StoredPlanningChatSession;
use super::planning_chat_types::PlanningChatMessage;

pub(crate) struct SavedPlanningMarkdown {
    pub(crate) markdown: String,
}

pub(crate) fn save_planning_markdown(
    project_dir: &Path,
    session: &mut StoredPlanningChatSession,
    messages: &[PlanningChatMessage],
    target_path: Option<&str>,
) -> Result<SavedPlanningMarkdown, String> {
    let markdown = synthesize_planning_markdown(session, messages);
    let explicit_target = target_path.filter(|rel| !rel.trim().is_empty());
    let (output_path, absolute_path) = match explicit_target {
        Some(rel) => {
            let rel = safe_relative_target(rel)?;
            let absolute = project_dir.join(&rel);
            (rel.to_string_lossy().into_owned(), absolute)
        }
        None => match &session.output_path {
            Some(existing) => {
                let absolute = project_dir.join(existing);
                (existing.clone(), absolute)
            }
            None => unique_plan_path(project_dir, &session.idea)?,
        },
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

fn safe_relative_target(rel: &str) -> Result<PathBuf, String> {
    let path = PathBuf::from(rel);
    if path.is_absolute() {
        return Err("targetPath must be relative".to_string());
    }
    if path
        .components()
        .any(|component| matches!(component, Component::ParentDir))
    {
        return Err("targetPath must not contain ..".to_string());
    }
    Ok(path)
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

#[cfg(test)]
#[path = "planning_chat_synthesis_tests.rs"]
mod tests;
// === ANCHOR: PLANNING_CHAT_SYNTHESIS_END ===
