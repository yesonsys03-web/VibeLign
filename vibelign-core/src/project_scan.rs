// === ANCHOR: PROJECT_SCAN_START ===
use serde::Serialize;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

#[derive(Debug, Serialize)]
pub struct ProjectScanReport {
    pub files: Vec<ProjectScanFile>,
}

#[derive(Debug, Serialize)]
pub struct ProjectScanFile {
    pub path: String,
    pub category: String,
    pub imports: Vec<String>,
}

const IGNORED_DIRS: &[&str] = &[
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".pnpm-store",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".sisyphus",
    ".trash",
    "library",
    "cloudstorage",
    "docs",
    "tests",
    ".github",
    ".vibelign",
];

const SOURCE_EXTENSIONS: &[&str] = &[
    "py", "js", "ts", "jsx", "tsx", "rs", "go", "java", "cs", "cpp", "c", "hpp", "h",
];

const CORE_ENTRY_FILES: &[&str] = &[
    "main.py",
    "app.py",
    "cli.py",
    "server.py",
    "index.js",
    "app.js",
    "main.js",
    "main.ts",
    "index.ts",
    "main.rs",
    "main.go",
    "main.cpp",
    "Program.cs",
    "vib_cli.py",
    "mcp_server.py",
];

const UI_TOKENS: &[&str] = &["ui", "view", "views", "window", "dialog", "widget", "screen"];
const SERVICE_TOKENS: &[&str] = &[
    "service", "services", "api", "client", "server", "worker", "job", "task", "queue", "auth", "data",
];
const CORE_TOKENS: &[&str] = &["core", "engine", "patch", "anchor", "guard"];

pub fn scan(root: &Path) -> Result<ProjectScanReport, String> {
    let mut files = Vec::new();
    for entry in walkdir::WalkDir::new(root).into_iter().filter_entry(|entry| !is_ignored(entry.path())) {
        let entry = entry.map_err(|error| error.to_string())?;
        if !entry.file_type().is_file() || !is_source_file(entry.path()) {
            continue;
        }
        let path = relpath(root, entry.path());
        files.push(ProjectScanFile {
            category: classify_file(entry.path(), &path),
            imports: extract_imports(entry.path()),
            path,
        });
    }
    files.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(ProjectScanReport { files })
}

fn is_ignored(path: &Path) -> bool {
    path.components().any(|component| {
        let part = component.as_os_str().to_string_lossy().to_lowercase();
        IGNORED_DIRS.contains(&part.as_str())
    })
}

fn is_source_file(path: &Path) -> bool {
    path.extension()
        .and_then(|extension| extension.to_str())
        .map(|extension| SOURCE_EXTENSIONS.contains(&extension.to_lowercase().as_str()))
        .unwrap_or(false)
}

fn relpath(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn classify_file(path: &Path, rel: &str) -> String {
    let file_name = path.file_name().and_then(|name| name.to_str()).unwrap_or("");
    if CORE_ENTRY_FILES.contains(&file_name) {
        return "entry".to_string();
    }
    let parts: Vec<&str> = rel.split('/').collect();
    let dir_low = parts[..parts.len().saturating_sub(1)].join("/").to_lowercase();
    if !dir_low.is_empty() {
        if contains_any(&dir_low, CORE_TOKENS) {
            return "core".to_string();
        }
        if contains_any(&dir_low, UI_TOKENS) {
            return "ui".to_string();
        }
        if contains_any(&dir_low, SERVICE_TOKENS) {
            return "service".to_string();
        }
    }
    let low = rel.to_lowercase();
    if contains_any(&low, UI_TOKENS) {
        return "ui".to_string();
    }
    if contains_any(&low, SERVICE_TOKENS) {
        return "service".to_string();
    }
    if contains_any(&low, CORE_TOKENS) {
        return "core".to_string();
    }
    "other".to_string()
}

fn contains_any(value: &str, tokens: &[&str]) -> bool {
    tokens.iter().any(|token| value.contains(token))
}

fn extract_imports(path: &Path) -> Vec<String> {
    let text = std::fs::read_to_string(path).unwrap_or_default();
    match path.extension().and_then(|extension| extension.to_str()).unwrap_or("").to_lowercase().as_str() {
        "py" => extract_python_imports(&text),
        "js" | "jsx" | "ts" | "tsx" | "mjs" | "cjs" => extract_js_imports(&text),
        _ => Vec::new(),
    }
}

fn extract_python_imports(text: &str) -> Vec<String> {
    let mut imports = BTreeSet::new();
    let mut ordered = Vec::new();
    for line in text.lines() {
        let trimmed = line.trim_start();
        let candidate = if let Some(rest) = trimmed.strip_prefix("from ") {
            rest.split_whitespace().next()
        } else if let Some(rest) = trimmed.strip_prefix("import ") {
            rest.split_whitespace().next()
        } else {
            None
        };
        if let Some(module) = candidate {
            let module = module.trim_end_matches(',');
            if !module.is_empty() && imports.insert(module.to_string()) {
                ordered.push(module.to_string());
            }
        }
    }
    ordered
}

fn extract_js_imports(text: &str) -> Vec<String> {
    let mut seen = BTreeSet::new();
    let mut ordered = Vec::new();
    for line in text.lines() {
        for quote in ['\'', '"'] {
            let Some(start) = line.find(quote) else { continue };
            let rest = &line[start + 1..];
            let Some(end) = rest.find(quote) else { continue };
            let module = &rest[..end];
            if !module.is_empty()
                && (line.trim_start().starts_with("import ") || line.contains("require("))
                && seen.insert(module.to_string())
            {
                ordered.push(module.to_string());
            }
            break;
        }
    }
    ordered
}
// === ANCHOR: PROJECT_SCAN_END ===
