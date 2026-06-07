// === ANCHOR: PLANNING_CHAT_STORE_START ===
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use super::planning_chat_readiness::ReadinessReport;

#[derive(Serialize, Deserialize)]
pub(crate) struct StoredPlanningChatSession {
    pub(crate) schema_version: u32,
    pub(crate) session_id: String,
    pub(crate) idea: String,
    pub(crate) mode: String,
    pub(crate) created_at: String,
    pub(crate) output_path: Option<String>,
    pub(crate) absolute_output_path: Option<String>,
    #[serde(default)]
    pub(crate) readiness: Option<ReadinessReport>,
}

pub(crate) fn planning_dir(project_dir: &Path) -> PathBuf {
    project_dir.join(".vibelign").join("planning")
}

pub(crate) fn latest_chat_session_file(project_dir: &Path) -> Option<PathBuf> {
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

pub(crate) fn write_json<T: Serialize>(path: PathBuf, value: &T) -> Result<(), String> {
    std::fs::write(
        path,
        serde_json::to_string_pretty(value).map_err(|error| error.to_string())? + "\n",
    )
    .map_err(|error| error.to_string())
}

pub(crate) fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let text = std::fs::read_to_string(path).map_err(|error| error.to_string())?;
    serde_json::from_str(&text).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::{latest_chat_session_file, StoredPlanningChatSession};

    #[test]
    fn stored_chat_session_accepts_missing_output_fields() {
        let session = serde_json::from_str::<StoredPlanningChatSession>(
            r#"{
              "schema_version": 1,
              "session_id": "chat_1",
              "idea": "예약 앱",
              "mode": "chat",
              "created_at": "1"
            }"#,
        )
        .expect("session");

        assert_eq!(session.output_path, None);
        assert_eq!(session.absolute_output_path, None);
        assert!(session.readiness.is_none());
    }

    #[test]
    fn latest_chat_session_requires_messages_file() {
        let root = tempfile::tempdir().expect("temp root");
        let session_dir = root.path().join(".vibelign/planning/chat_1");
        std::fs::create_dir_all(&session_dir).expect("mkdir");
        std::fs::write(session_dir.join("session.json"), "{}").expect("session");

        assert_eq!(latest_chat_session_file(root.path()), None);
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
// === ANCHOR: PLANNING_CHAT_STORE_END ===
