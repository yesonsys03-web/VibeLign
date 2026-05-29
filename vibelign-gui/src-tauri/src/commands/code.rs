use std::path::PathBuf;

use crate::code_access::{
    list_explorer_files_under, read_code_file_under, CodeFileReadResult, ExplorerFileEntry,
};

// Code Explorer 커맨드는 모두 async + spawn_blocking 으로 둔다.
// 동기 `#[tauri::command] fn` 은 Tauri 메인 스레드에서 실행돼 서로 직렬화되며,
// git status(--untracked-files=all)·git show 의 프로세스 spawn 비용이 큰 Windows 에서
// 빠른 read_code_file 까지 막아 UI 가 멈춘다. blocking 풀로 빼면 메인 스레드를 막지 않고
// 4개가 실제로 병렬 실행된다. (error_logs / gui_error / vib_bridge 와 동일한 패턴.)
const SPAWN_FAIL: &str = "작업 실행에 실패했어요";

#[tauri::command]
pub(crate) async fn read_code_file(root: String, path: String) -> Result<CodeFileReadResult, String> {
    let root_path = PathBuf::from(root);
    tauri::async_runtime::spawn_blocking(move || read_code_file_under(&root_path, &path))
        .await
        .map_err(|_| SPAWN_FAIL.to_string())?
}

#[tauri::command]
pub(crate) async fn list_code_files(root: String) -> Result<Vec<ExplorerFileEntry>, String> {
    let root_path = PathBuf::from(root);
    tauri::async_runtime::spawn_blocking(move || list_explorer_files_under(&root_path))
        .await
        .map_err(|_| SPAWN_FAIL.to_string())?
}

use crate::code_diff::{build_file_diff, CodeFileDiffResult};
use crate::git_status::{list_changed_paths, ChangedEntry};

#[tauri::command]
pub(crate) async fn read_code_file_diff(root: String, path: String) -> Result<CodeFileDiffResult, String> {
    let root_path = PathBuf::from(root);
    tauri::async_runtime::spawn_blocking(move || build_file_diff(&root_path, &path))
        .await
        .map_err(|_| SPAWN_FAIL.to_string())?
}

#[tauri::command]
pub(crate) async fn list_changed_files(root: String) -> Result<Vec<ChangedEntry>, String> {
    let root_path = PathBuf::from(root);
    tauri::async_runtime::spawn_blocking(move || list_changed_paths(&root_path))
        .await
        .map_err(|_| SPAWN_FAIL.to_string())?
}
