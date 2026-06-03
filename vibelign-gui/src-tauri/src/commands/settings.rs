// === ANCHOR: SETTINGS_START ===
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;

use crate::vib_path;

const DISABLED_KEYS_FIELD: &str = "__disabled_keys";

/// 플랫폼별 api_keys.json 경로.
/// macOS/Linux: ~/.config/vibelign/api_keys.json
/// Windows:     %APPDATA%\vibelign\api_keys.json
fn keys_file_path() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let config_root = std::env::var("APPDATA")
            .map(PathBuf::from)
            .or_else(|_| {
                std::env::var("USERPROFILE")
                    .map(|home| PathBuf::from(home).join("AppData").join("Roaming"))
            })
            .ok()?;
        let dir = config_root.join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        return Some(dir.join("api_keys.json"));
    }
    #[cfg(not(target_os = "windows"))]
    {
        let xdg_config = std::env::var("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                let home = std::env::var("HOME")
                    .or_else(|_| std::env::var("USERPROFILE"))
                    .unwrap_or_default();
                PathBuf::from(home).join(".config")
            });
        let dir = xdg_config.join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        Some(dir.join("api_keys.json"))
    }
}

pub(crate) fn read_keys_file() -> HashMap<String, String> {
    let path = match keys_file_path() {
        Some(p) => p,
        None => return HashMap::new(),
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return HashMap::new(),
    };
    let val: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return HashMap::new(),
    };
    let mut out = HashMap::new();
    if let Some(obj) = val.as_object() {
        for (k, v) in obj {
            if k == DISABLED_KEYS_FIELD {
                continue;
            }
            if let Some(s) = v.as_str() {
                if !s.is_empty() {
                    out.insert(k.clone(), s.to_string());
                }
            }
        }
    }
    out
}

fn read_disabled_keys_file() -> HashSet<String> {
    let path = match keys_file_path() {
        Some(p) => p,
        None => return HashSet::new(),
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return HashSet::new(),
    };
    let val: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return HashSet::new(),
    };
    val.get(DISABLED_KEYS_FIELD)
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default()
}

fn write_keys_file(keys: &HashMap<String, String>) -> Result<(), String> {
    write_keys_state(keys, &read_disabled_keys_file())
}

fn write_keys_state(
    keys: &HashMap<String, String>,
    disabled: &HashSet<String>,
) -> Result<(), String> {
    let path = keys_file_path().ok_or("keys 파일 경로를 찾을 수 없습니다")?;
    let mut val = serde_json::Map::new();
    for (key, value) in keys {
        if !value.is_empty() {
            val.insert(key.clone(), serde_json::Value::String(value.clone()));
        }
    }
    if !disabled.is_empty() {
        let mut disabled_keys: Vec<String> = disabled.iter().cloned().collect();
        disabled_keys.sort();
        val.insert(
            DISABLED_KEYS_FIELD.to_string(),
            serde_json::Value::Array(
                disabled_keys
                    .into_iter()
                    .map(serde_json::Value::String)
                    .collect(),
            ),
        );
    }
    let val =
        serde_json::to_string_pretty(&serde_json::Value::Object(val)).map_err(|e| e.to_string())?;
    std::fs::write(&path, val + "\n").map_err(|e| e.to_string())?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
    }
    Ok(())
}

fn provider_to_env_key(provider: &str) -> &'static str {
    match provider {
        "ANTHROPIC" => "ANTHROPIC_API_KEY",
        "OPENAI" => "OPENAI_API_KEY",
        "GEMINI" => "GEMINI_API_KEY",
        "GLM" => "GLM_API_KEY",
        "MOONSHOT" => "MOONSHOT_API_KEY",
        _ => "",
    }
}

pub(crate) fn migrate_legacy_keys() {
    let new_path = match keys_file_path() {
        Some(p) => p,
        None => return,
    };
    if new_path.exists() {
        return;
    }
    let mut legacy = read_gui_config();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC", "ANTHROPIC_API_KEY"),
        ("OPENAI", "OPENAI_API_KEY"),
        ("GEMINI", "GEMINI_API_KEY"),
        ("GLM", "GLM_API_KEY"),
        ("MOONSHOT", "MOONSHOT_API_KEY"),
    ];
    let mut migrated: HashMap<String, String> = HashMap::new();
    if let Some(obj) = legacy.get("provider_api_keys").and_then(|v| v.as_object()) {
        for (short, env_name) in pairs {
            if let Some(v) = obj.get(*short).and_then(|v| v.as_str()) {
                if !v.is_empty() {
                    migrated.insert(env_name.to_string(), v.to_string());
                }
            }
        }
    }
    if let Some(s) = legacy.get("anthropic_api_key").and_then(|v| v.as_str()) {
        if !s.is_empty() {
            migrated
                .entry("ANTHROPIC_API_KEY".into())
                .or_insert_with(|| s.to_string());
        }
    }
    if !migrated.is_empty() && write_keys_file(&migrated).is_ok() {
        if let Some(obj) = legacy.as_object_mut() {
            obj.remove("provider_api_keys");
            obj.remove("anthropic_api_key");
            let _ = write_gui_config(&legacy);
        }
    }
}

fn config_path() -> Option<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .ok()?;
    let dir = PathBuf::from(home).join(".vibelign");
    std::fs::create_dir_all(&dir).ok()?;
    Some(dir.join("gui_config.json"))
}

#[tauri::command]
pub(crate) fn save_recent_projects(dirs: Vec<String>) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    let existing = std::fs::read_to_string(&path)
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .unwrap_or(serde_json::json!({}));
    let mut data = existing;
    data["recent_projects"] =
        serde_json::Value::Array(dirs.into_iter().map(serde_json::Value::String).collect());
    // 임시 파일에 쓰고 rename 으로 원자 교체한다.
    // Why: API 키가 같은 파일에 저장되므로 중간 크래시 시 파일이 절단되면
    // 키를 잃는다. 동일 디렉터리 내 rename 은 POSIX / Windows 에서 원자적이다.
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, data.to_string()).map_err(|e| e.to_string())?;
    std::fs::rename(&tmp, &path).map_err(|e| e.to_string())
}

#[tauri::command]
pub(crate) fn load_recent_projects() -> Vec<String> {
    let path = match config_path() {
        Some(p) => p,
        None => return vec![],
    };
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return vec![],
    };
    let data: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => return vec![],
    };
    data["recent_projects"]
        .as_array()
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
}

fn read_gui_config() -> serde_json::Value {
    let path = match config_path() {
        Some(p) => p,
        None => return serde_json::json!({}),
    };
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    match serde_json::from_str::<serde_json::Value>(&text) {
        Ok(v) if v.is_object() => v,
        _ => serde_json::json!({}),
    }
}

fn write_gui_config(data: &serde_json::Value) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

/// 현재 GUI 버전이 이미 CLI 를 PATH 에 설치했는지 확인한다.
/// Why: `install_cli_to_path` 가 앱 시작마다 호출되면서 사용자가 `uv tool install`/`pipx`
/// 등으로 직접 관리하던 `~/.local/bin/vib` 를 매번 덮어쓰는 문제를 차단한다.
pub(crate) fn cli_installed_for_current_version() -> bool {
    let cfg = read_gui_config();
    cfg.get("cli_path_installed_version")
        .and_then(|v| v.as_str())
        .map(|s| s == env!("CARGO_PKG_VERSION"))
        .unwrap_or(false)
}

pub(crate) fn mark_cli_installed_for_current_version() {
    let mut cfg = read_gui_config();
    if !cfg.is_object() {
        cfg = serde_json::json!({});
    }
    cfg["cli_path_installed_version"] =
        serde_json::Value::String(env!("CARGO_PKG_VERSION").to_string());
    let _ = write_gui_config(&cfg);
}

#[tauri::command]
pub(crate) fn save_api_key(key: String) -> Result<(), String> {
    save_provider_api_key("ANTHROPIC".to_string(), key)
}

#[tauri::command]
pub(crate) fn load_api_key() -> Option<String> {
    load_provider_api_keys().get("ANTHROPIC").cloned()
}

#[tauri::command]
pub(crate) fn delete_api_key() -> Result<(), String> {
    delete_provider_api_key("ANTHROPIC".to_string())?;
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    if !path.exists() {
        return Ok(());
    }
    let mut data = read_gui_config();
    if let Some(obj) = data.as_object_mut() {
        obj.remove("anthropic_api_key");
    }
    if let Some(obj) = data
        .get_mut("provider_api_keys")
        .and_then(|v| v.as_object_mut())
    {
        obj.remove("ANTHROPIC");
    }
    write_gui_config(&data)
}

#[tauri::command]
pub(crate) fn save_provider_api_key(provider: String, key: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let key = key.trim().to_string();
    if key.is_empty() {
        return Err("키가 비어 있습니다".into());
    }
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Err(format!("알 수 없는 provider: {provider}"));
    }
    let mut keys = read_keys_file();
    let mut disabled = read_disabled_keys_file();
    keys.insert(env_key.to_string(), key);
    disabled.remove(env_key);
    write_keys_state(&keys, &disabled)
}

#[tauri::command]
pub(crate) fn delete_provider_api_key(provider: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Ok(());
    }
    let mut keys = read_keys_file();
    let mut disabled = read_disabled_keys_file();
    keys.remove(env_key);
    disabled.insert(env_key.to_string());
    write_keys_state(&keys, &disabled)
}

#[tauri::command]
pub(crate) fn load_provider_api_keys() -> HashMap<String, String> {
    let raw = read_keys_file();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC_API_KEY", "ANTHROPIC"),
        ("OPENAI_API_KEY", "OPENAI"),
        ("GEMINI_API_KEY", "GEMINI"),
        ("GLM_API_KEY", "GLM"),
        ("MOONSHOT_API_KEY", "MOONSHOT"),
    ];
    let mut out = HashMap::new();
    for (env_name, short_name) in pairs {
        if let Some(v) = raw.get(*env_name) {
            out.insert(short_name.to_string(), v.clone());
        }
    }
    out
}

#[tauri::command]
pub(crate) fn get_env_key_status() -> HashMap<String, bool> {
    let keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GLM_API_KEY",
        "MOONSHOT_API_KEY",
    ];
    let disabled = read_disabled_keys_file();
    keys.iter()
        .map(|k| {
            let from_env =
                !disabled.contains(*k) && !std::env::var(k).unwrap_or_default().is_empty();
            (k.to_string(), from_env)
        })
        .collect()
}

#[tauri::command]
pub(crate) fn setup_cli_path() -> Result<String, String> {
    vib_path::install_cli_to_path()
}
// === ANCHOR: SETTINGS_END ===
