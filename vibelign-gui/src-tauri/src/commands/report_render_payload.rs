use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

fn payload_dir(canon_root: &Path) -> PathBuf {
    canon_root
        .join(".vibelign")
        .join("reports")
        .join("render-payloads")
}

fn validate_payload_path(canon_root: &Path, path: &Path) -> Result<PathBuf, String> {
    let canon_file = match std::fs::canonicalize(path) {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(path.to_path_buf()),
        Err(error) => return Err(format!("render payload 경로 정규화 실패: {error}")),
    };
    let allowed_dir = payload_dir(canon_root);
    if !canon_file.starts_with(&allowed_dir) {
        return Err("render payload 경로가 프로젝트 payload 디렉터리 밖입니다".into());
    }
    let file_name = canon_file
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or("render payload 파일명을 읽을 수 없습니다")?;
    if !file_name.starts_with("render-payload-") || !file_name.ends_with(".json") {
        return Err("render payload 파일명 형식이 잘못됐습니다".into());
    }
    Ok(canon_file)
}

#[tauri::command]
pub(crate) fn write_report_render_payload(root: String, payload_json: String) -> Result<String, String> {
    let canon_root = std::fs::canonicalize(&root)
        .map_err(|error| format!("프로젝트 루트 정규화 실패({root}): {error}"))?;
    let dir = payload_dir(&canon_root);
    std::fs::create_dir_all(&dir)
        .map_err(|error| format!("render payload 디렉터리 생성 실패: {error}"))?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("render payload 파일명 생성 실패: {error}"))?
        .as_nanos();
    let path = dir.join(format!("render-payload-{}-{stamp}.json", std::process::id()));
    std::fs::write(&path, payload_json)
        .map_err(|error| format!("render payload 쓰기 실패: {error}"))?;
    Ok(path.to_string_lossy().into_owned())
}

#[tauri::command]
pub(crate) fn remove_report_render_payload(root: String, path: String) -> Result<(), String> {
    let canon_root = std::fs::canonicalize(&root)
        .map_err(|error| format!("프로젝트 루트 정규화 실패({root}): {error}"))?;
    let payload_path = validate_payload_path(&canon_root, Path::new(&path))?;
    match std::fs::remove_file(&payload_path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(format!("render payload 삭제 실패: {error}")),
    }
}
