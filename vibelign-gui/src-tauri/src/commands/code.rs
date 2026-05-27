use std::path::PathBuf;

use crate::code_access::{read_code_file_under, CodeFileReadResult};

#[tauri::command]
pub(crate) fn read_code_file(root: String, path: String) -> Result<CodeFileReadResult, String> {
    let root_path = PathBuf::from(root);
    read_code_file_under(&root_path, &path)
}
