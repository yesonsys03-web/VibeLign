use std::path::PathBuf;

use crate::code_access::{
    list_explorer_files_under, read_code_file_under, CodeFileReadResult, ExplorerFileEntry,
};

#[tauri::command]
pub(crate) fn read_code_file(root: String, path: String) -> Result<CodeFileReadResult, String> {
    let root_path = PathBuf::from(root);
    read_code_file_under(&root_path, &path)
}

#[tauri::command]
pub(crate) fn list_code_files(root: String) -> Result<Vec<ExplorerFileEntry>, String> {
    let root_path = PathBuf::from(root);
    list_explorer_files_under(&root_path)
}

use crate::code_diff::{build_file_diff, CodeFileDiffResult};
use crate::git_status::{list_changed_paths, ChangedEntry};

#[tauri::command]
pub(crate) fn read_code_file_diff(root: String, path: String) -> Result<CodeFileDiffResult, String> {
    let root_path = PathBuf::from(root);
    build_file_diff(&root_path, &path)
}

#[tauri::command]
pub(crate) fn list_changed_files(root: String) -> Result<Vec<ChangedEntry>, String> {
    let root_path = PathBuf::from(root);
    list_changed_paths(&root_path)
}
