// === ANCHOR: PLANNING_CHAT_TRASH_START ===
//! 기획 세션 휴지통: 소프트 삭제(.trash 로 이동)·복구·목록·비우기·자동 정리.
//! `.trash` 는 planning_dir 안에 있지만 세션 나열기는 session.json 유무로 거르므로
//! 휴지통 항목(.trash/{id}/...)은 일반 세션 목록에 절대 섞이지 않는다.
use std::path::{Component, Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};

use super::planning_chat_store::{planning_dir, read_json, write_json, StoredPlanningChatSession};

/// 이 기간보다 오래된 휴지통 항목은 자동 정리한다(수동 비우기와 병행).
const TRASH_MAX_AGE_MS: u128 = 30 * 24 * 60 * 60 * 1000;
const TRASH_DIR_NAME: &str = ".trash";
const TRASH_META_NAME: &str = "__trash__.json";
const TRASH_PLAN_MD_NAME: &str = "__trashed_plan.md";

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TrashMeta {
    deleted_at_ms: u128,
    has_md: bool,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct TrashedSessionSummary {
    pub(crate) session_id: String,
    pub(crate) title: String,
    pub(crate) output_path: Option<String>,
    pub(crate) deleted_at_ms: u128,
}

fn now_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}

fn trash_root(project_dir: &Path) -> PathBuf {
    planning_dir(project_dir).join(TRASH_DIR_NAME)
}

/// session_id 는 단일 디렉터리 이름이어야 한다(경로 traversal 차단).
pub(crate) fn valid_session_id(session_id: &str) -> bool {
    !session_id.is_empty()
        && !session_id.contains('/')
        && !session_id.contains('\\')
        && !session_id.contains('\0')
        && !session_id.contains("..")
}

/// output_path 가 프로젝트 안 상대경로인지(.. / 절대경로 거부).
fn safe_relative(output_path: &str) -> bool {
    let path = Path::new(output_path);
    !path.is_absolute()
        && !path
            .components()
            .any(|component| matches!(component, Component::ParentDir))
}

fn title_from_idea(idea: &str) -> String {
    idea.lines().next().unwrap_or("").trim().chars().take(60).collect()
}

/// 세션을 휴지통으로 이동(소프트 삭제). 세션 디렉터리 + 저장된 md 를 .trash/{id}/ 로 옮긴다.
pub(crate) fn soft_delete(project_dir: &Path, session_id: &str) -> Result<(), String> {
    if !valid_session_id(session_id) {
        return Err("invalid sessionId".to_string());
    }
    let session_dir = planning_dir(project_dir).join(session_id);
    if !session_dir.is_dir() {
        return Err("session not found".to_string());
    }
    let session: StoredPlanningChatSession = read_json(&session_dir.join("session.json"))
        .map_err(|_| "session metadata unreadable".to_string())?;

    let dest = trash_root(project_dir).join(session_id);
    if dest.exists() {
        let _ = std::fs::remove_dir_all(&dest);
    }
    if let Some(parent) = dest.parent() {
        std::fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    std::fs::rename(&session_dir, &dest).map_err(|error| error.to_string())?;

    // 저장된 md 도 휴지통으로(프로젝트 내부 실제 파일일 때만).
    let mut has_md = false;
    if let Some(output_path) = session.output_path.as_ref() {
        let candidate = project_dir.join(output_path);
        if let (Ok(resolved), Ok(root)) = (candidate.canonicalize(), project_dir.canonicalize()) {
            if resolved.starts_with(&root)
                && resolved.is_file()
                && std::fs::rename(&resolved, dest.join(TRASH_PLAN_MD_NAME)).is_ok()
            {
                has_md = true;
            }
        }
    }
    let meta = TrashMeta {
        deleted_at_ms: now_ms(),
        has_md,
    };
    write_json(dest.join(TRASH_META_NAME), &meta).map_err(|error| error.to_string())?;
    purge_expired(project_dir);
    Ok(())
}

/// 휴지통에서 복구: 세션 디렉터리 + md 를 원위치로 되돌린다.
pub(crate) fn restore(project_dir: &Path, session_id: &str) -> Result<(), String> {
    if !valid_session_id(session_id) {
        return Err("invalid sessionId".to_string());
    }
    let trash_dir = trash_root(project_dir).join(session_id);
    if !trash_dir.is_dir() {
        return Err("trashed session not found".to_string());
    }
    let session: StoredPlanningChatSession = read_json(&trash_dir.join("session.json"))
        .map_err(|_| "session metadata unreadable".to_string())?;
    let meta: TrashMeta = read_json(&trash_dir.join(TRASH_META_NAME)).unwrap_or(TrashMeta {
        deleted_at_ms: 0,
        has_md: false,
    });

    let dest = planning_dir(project_dir).join(session_id);
    if dest.exists() {
        return Err("a session with this id already exists".to_string());
    }
    // md 원위치(프로젝트 안 상대경로일 때만).
    if meta.has_md {
        if let Some(output_path) = session.output_path.as_ref() {
            if safe_relative(output_path) {
                let target = project_dir.join(output_path);
                if let Some(parent) = target.parent() {
                    let _ = std::fs::create_dir_all(parent);
                }
                let _ = std::fs::rename(trash_dir.join(TRASH_PLAN_MD_NAME), &target);
            }
        }
    }
    // 휴지통 부속 파일 제거 후 세션 디렉터리 복귀.
    let _ = std::fs::remove_file(trash_dir.join(TRASH_META_NAME));
    let _ = std::fs::remove_file(trash_dir.join(TRASH_PLAN_MD_NAME));
    std::fs::rename(&trash_dir, &dest).map_err(|error| error.to_string())?;
    Ok(())
}

/// 휴지통 전체 비우기(영구).
pub(crate) fn empty_trash(project_dir: &Path) -> Result<(), String> {
    let root = trash_root(project_dir);
    if root.is_dir() {
        std::fs::remove_dir_all(&root).map_err(|error| error.to_string())?;
    }
    Ok(())
}

/// TRASH_MAX_AGE_MS 보다 오래된 항목 자동 제거. best-effort(실패 무시).
fn purge_expired(project_dir: &Path) {
    let Ok(entries) = std::fs::read_dir(trash_root(project_dir)) else {
        return;
    };
    let now = now_ms();
    for entry in entries.flatten() {
        let dir = entry.path();
        if !dir.is_dir() {
            continue;
        }
        let Ok(meta) = read_json::<TrashMeta>(&dir.join(TRASH_META_NAME)) else {
            continue;
        };
        if now.saturating_sub(meta.deleted_at_ms) > TRASH_MAX_AGE_MS {
            let _ = std::fs::remove_dir_all(&dir);
        }
    }
}

pub(crate) fn list_trashed(project_dir: &Path) -> Vec<TrashedSessionSummary> {
    purge_expired(project_dir);
    let Ok(entries) = std::fs::read_dir(trash_root(project_dir)) else {
        return Vec::new();
    };
    let mut rows: Vec<TrashedSessionSummary> = Vec::new();
    for entry in entries.flatten() {
        let dir = entry.path();
        if !dir.is_dir() {
            continue;
        }
        let Some(session_id) = dir.file_name().and_then(|name| name.to_str()).map(str::to_string)
        else {
            continue;
        };
        let Ok(session) = read_json::<StoredPlanningChatSession>(&dir.join("session.json")) else {
            continue;
        };
        let meta = read_json::<TrashMeta>(&dir.join(TRASH_META_NAME)).unwrap_or(TrashMeta {
            deleted_at_ms: 0,
            has_md: false,
        });
        rows.push(TrashedSessionSummary {
            session_id,
            title: title_from_idea(&session.idea),
            output_path: session.output_path.clone(),
            deleted_at_ms: meta.deleted_at_ms,
        });
    }
    rows.sort_by(|a, b| b.deleted_at_ms.cmp(&a.deleted_at_ms));
    rows
}

#[tauri::command]
pub(crate) async fn restore_planning_chat_session(
    project_dir: String,
    session_id: String,
) -> Result<(), String> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Err("projectDir must be absolute".to_string());
    }
    tauri::async_runtime::spawn_blocking(move || restore(&project_dir, &session_id))
        .await
        .map_err(|error| error.to_string())?
}

#[tauri::command]
pub(crate) async fn list_trashed_planning_sessions(project_dir: String) -> Vec<TrashedSessionSummary> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Vec::new();
    }
    tauri::async_runtime::spawn_blocking(move || list_trashed(&project_dir))
        .await
        .unwrap_or_default()
}

#[tauri::command]
pub(crate) async fn empty_planning_trash(project_dir: String) -> Result<(), String> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Err("projectDir must be absolute".to_string());
    }
    tauri::async_runtime::spawn_blocking(move || empty_trash(&project_dir))
        .await
        .map_err(|error| error.to_string())?
}
// === ANCHOR: PLANNING_CHAT_TRASH_END ===
