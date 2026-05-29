use serde::Serialize;
use sha2::{Digest, Sha256};
use std::path::{Component, Path, PathBuf};

const MAX_CODE_READ_BYTES: u64 = 1_000_000;
// json/yaml/toml 같은 데이터 파일(project_map.json, lockfile 등)은 코드보다 훨씬 커서
// 1MB 코드 캡으로는 정당한 파일도 거부된다. 데이터 포맷에는 더 큰 캡을 따로 둔다.
const MAX_DATA_READ_BYTES: u64 = 5_000_000;
const DATA_READ_EXTENSIONS: &[&str] = &["json", "toml", "yaml", "yml"];
const WINDOWS_RESERVED_DEVICE_NAMES: &[&str] = &[
    "con", "prn", "aux", "nul", "conin$", "conout$",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
];
const CODE_READ_EXTENSIONS: &[&str] = &[
    "py", "js", "ts", "jsx", "tsx", "rs", "go", "java", "cs", "cpp", "c", "hpp", "h",
    "mjs", "cjs", "swift", "json", "toml", "yaml", "yml", "css", "html", "md",
];
// 사이드바 트리에 노출할 파일 확장자. 엔진의 SOURCE_FILE_EXTENSIONS(코드 전용)와
// 분리되어 있어 docs/*.md 같은 문서가 트리에 보이지만 anchor/patch_suggester 등의
// 코드 분석 파이프라인에는 영향이 가지 않는다.
const EXPLORER_FILE_EXTENSIONS: &[&str] = &[
    "py", "js", "ts", "jsx", "tsx", "rs", "go", "java", "cs", "cpp", "c", "hpp", "h",
    "mjs", "cjs", "swift", "md",
    // 설정/데이터 파일도 트리에 노출(읽기는 CODE_READ_EXTENSIONS 로 이미 지원).
    // 카테고리는 "data" 로 분류돼 사이드바에서 "other"(회색)로 표시된다.
    "toml", "yaml", "yml",
];
const CODE_READ_IGNORED_DIRS: &[&str] = &[
    ".git", ".vibelign", ".omc", ".sisyphus", ".venv", "venv", "env", "node_modules", "dist",
    "build", "target", "coverage", ".next", ".nuxt", ".turbo", ".cache", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".gradle", ".idea", ".vscode",
];

#[derive(Debug, Serialize)]
pub(crate) struct CodeFileReadResult {
    pub(crate) path: String,
    pub(crate) content: String,
    pub(crate) source_hash: String,
    pub(crate) size_bytes: u64,
    pub(crate) line_count: usize,
    pub(crate) language: String,
}

pub(crate) fn read_code_file_under(root: &Path, rel: &str) -> Result<CodeFileReadResult, String> {
    let root = root.canonicalize().map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let rel = normalize_relative_input(rel)?;
    reject_ignored_segments(&rel)?;
    let joined = root.join(&rel);
    let canonical = joined.canonicalize().map_err(|e| format!("코드 파일을 찾을 수 없어요: {e}"))?;
    let relative = canonical
        .strip_prefix(&root)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let relative_path = relative.to_string_lossy().replace('\\', "/");
    reject_ignored_segments(&relative_path)?;
    ensure_supported_extension(&canonical)?;
    let meta = std::fs::metadata(&canonical).map_err(|e| format!("파일 정보를 읽을 수 없어요: {e}"))?;
    if !meta.is_file() {
        return Err("일반 파일만 읽을 수 있어요".to_string());
    }
    let max_bytes = if is_data_extension(&canonical) { MAX_DATA_READ_BYTES } else { MAX_CODE_READ_BYTES };
    if meta.len() > max_bytes {
        return Err(format!("파일이 너무 커서 미리보기를 열 수 없어요 ({} bytes)", meta.len()));
    }
    let bytes = std::fs::read(&canonical).map_err(|e| format!("코드 파일을 읽을 수 없어요: {e}"))?;
    if bytes.contains(&0) {
        return Err("바이너리 파일은 코드 뷰어에서 열 수 없어요".to_string());
    }
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(&bytes);
    let content = std::str::from_utf8(bytes)
        .map_err(|_| "UTF-8 텍스트 코드 파일만 읽을 수 있어요".to_string())?
        .replace("\r\n", "\n")
        .replace('\r', "\n");
    let source_hash = hash_content(&content);
    let line_count = content.lines().count();
    // size_bytes는 뷰어가 표시하는 정규화된 content 기준으로 맞춘다.
    // (meta.len()은 BOM/CRLF 정규화 전 on-disk 크기라 표시 내용과 어긋난다.)
    let size_bytes = content.len() as u64;
    Ok(CodeFileReadResult {
        path: relative_path.clone(),
        content,
        source_hash,
        size_bytes,
        line_count,
        language: language_for_path(&relative_path).to_string(),
    })
}

fn is_data_extension(path: &Path) -> bool {
    let ext = path.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase();
    DATA_READ_EXTENSIONS.contains(&ext.as_str())
}

fn normalize_relative_input(rel: &str) -> Result<String, String> {
    let raw = rel.trim();
    // 절대경로/UNC/드라이브 차단은 정규화 *전* raw 기준으로 판정한다.
    // (replace('\\',"/")+trim_matches('/')를 먼저 하면 leading '/'·UNC '\\'가
    //  지워져서 Windows 절대경로 가드가 죽은 코드가 된다.)
    if raw.starts_with('/')                     // POSIX 절대경로
        || raw.starts_with('\\')                // Windows 절대경로 + UNC(\\server\share)
        || raw.as_bytes().get(1) == Some(&b':') // 드라이브: C:\ , C:/ , C:foo
    {
        return Err("허용되지 않은 경로입니다".to_string());
    }
    let trimmed = raw.replace('\\', "/").trim_matches('/').to_string();
    if trimmed.is_empty() {
        return Err("파일 경로가 비어 있어요".to_string());
    }
    let rel_path = PathBuf::from(&trimmed);
    if rel_path.components().any(|component| matches!(component, Component::ParentDir | Component::Prefix(_) | Component::RootDir)) {
        return Err("허용되지 않은 경로입니다".to_string());
    }
    Ok(trimmed)
}

fn reject_ignored_segments(rel: &str) -> Result<(), String> {
    for segment in rel.split('/') {
        if segment.is_empty() || segment == "." || segment == ".." {
            return Err("허용되지 않은 경로입니다".to_string());
        }
        let lower = segment.to_ascii_lowercase();
        let normalized_segment = lower.trim_end_matches(|ch| ch == ' ' || ch == '.');
        let stem = normalized_segment.split('.').next().unwrap_or("");
        if WINDOWS_RESERVED_DEVICE_NAMES.contains(&stem) {
            return Err("Windows 예약된 파일명은 열 수 없어요".to_string());
        }
        if CODE_READ_IGNORED_DIRS.contains(&lower.as_str()) || segment.starts_with('.') {
            return Err("읽을 수 없는 경로입니다".to_string());
        }
    }
    Ok(())
}

fn ensure_supported_extension(path: &Path) -> Result<(), String> {
    let ext = path.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase();
    if CODE_READ_EXTENSIONS.contains(&ext.as_str()) {
        Ok(())
    } else {
        Err("지원하지 않는 코드 파일 형식입니다".to_string())
    }
}

fn hash_content(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn language_for_path(path: &str) -> &'static str {
    match path.rsplit('.').next().unwrap_or("").to_ascii_lowercase().as_str() {
        "py" => "Python",
        "ts" | "tsx" => "TypeScript",
        "js" | "jsx" | "mjs" | "cjs" => "JavaScript",
        "rs" => "Rust",
        "go" => "Go",
        "java" => "Java",
        "cs" => "C#",
        "c" | "h" => "C",
        "cpp" | "hpp" => "C++",
        "swift" => "Swift",
        "json" => "JSON",
        "toml" => "TOML",
        "yaml" | "yml" => "YAML",
        "css" => "CSS",
        "html" => "HTML",
        "md" => "Markdown",
        _ => "Text",
    }
}

#[derive(Debug, Serialize)]
pub(crate) struct ExplorerFileEntry {
    pub(crate) path: String,
    pub(crate) category: String,
    pub(crate) imports: Vec<String>,
}

pub(crate) fn list_explorer_files_under(root: &Path) -> Result<Vec<ExplorerFileEntry>, String> {
    let root = root
        .canonicalize()
        .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let mut entries: Vec<ExplorerFileEntry> = Vec::new();
    walk_explorer(&root, &root, &mut entries);
    entries.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(entries)
}

fn walk_explorer(root: &Path, dir: &Path, out: &mut Vec<ExplorerFileEntry>) {
    let read_dir = match std::fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(_) => return,
    };
    for entry in read_dir.flatten() {
        let path = entry.path();
        let name = match path.file_name().and_then(|n| n.to_str()) {
            Some(n) => n.to_string(),
            None => continue,
        };
        // hidden entry(.git, .DS_Store, .vscode, ...)는 사이드바에 노출하지 않는다.
        if name.starts_with('.') {
            continue;
        }
        let name_lower = name.to_ascii_lowercase();
        let file_type = match entry.file_type() {
            Ok(ft) => ft,
            Err(_) => continue,
        };
        if file_type.is_dir() {
            if CODE_READ_IGNORED_DIRS.contains(&name_lower.as_str()) {
                continue;
            }
            walk_explorer(root, &path, out);
        } else if file_type.is_file() {
            let ext = path
                .extension()
                .and_then(|v| v.to_str())
                .unwrap_or("")
                .to_ascii_lowercase();
            if !EXPLORER_FILE_EXTENSIONS.contains(&ext.as_str()) {
                continue;
            }
            let rel = match path.strip_prefix(root) {
                Ok(r) => r.to_string_lossy().replace('\\', "/"),
                Err(_) => continue,
            };
            let category = match ext.as_str() {
                "md" => "docs",
                "toml" | "yaml" | "yml" => "data",
                _ => "code",
            }
            .to_string();
            out.push(ExplorerFileEntry {
                path: rel,
                category,
                imports: Vec::new(),
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write(root: &std::path::Path, rel: &str, content: &[u8]) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, content).expect("write");
    }

    #[test]
    fn reads_supported_source_file() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "src/main.ts", b"export const value = 1;\n");

        let result = read_code_file_under(root.path(), "src/main.ts").expect("read source");

        assert_eq!(result.path, "src/main.ts");
        assert_eq!(result.content, "export const value = 1;\n");
        assert_eq!(result.line_count, 1);
        assert_eq!(result.language, "TypeScript");
    }

    #[test]
    fn rejects_parent_escape() {
        let root = TempDir::new().expect("temp root");
        let err = read_code_file_under(root.path(), "../secret.ts").expect_err("escape rejected");
        assert!(err.contains("프로젝트 루트 밖") || err.contains("허용되지 않은 경로"));
    }

    #[test]
    fn rejects_windows_absolute_and_unc() {
        // raw 입력 기준 거부이므로 OS와 무관하게 모든 빌드에서 검증된다.
        let root = TempDir::new().expect("temp root");
        for input in ["C:\\Windows\\system.ini", "C:/Windows/system.ini", "\\\\server\\share\\x.ts", "/etc/passwd"] {
            let err = read_code_file_under(root.path(), input).expect_err("absolute/UNC rejected");
            assert!(err.contains("허용되지 않은 경로"), "input={input} err={err}");
        }
    }

    #[test]
    fn rejects_windows_reserved_device_names() {
        // Windows reserved device names are rejected at string level so every OS build verifies the guard.
        let root = TempDir::new().expect("temp root");
        for input in ["NUL", "NUL.ts", "NUL. ", "src/CON.js", "logs/PRN.ts", "serial/COM1.rs", "printer/LPT9.py", "AUX.json", "src/CONOUT$.ts"] {
            let err = read_code_file_under(root.path(), input).expect_err("reserved device name rejected");
            assert!(err.contains("예약된 파일명"), "input={input} err={err}");
        }
    }

    #[test]
    fn rejects_hidden_or_generated_directory() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "node_modules/pkg/index.ts", b"export {};\n");

        let err = read_code_file_under(root.path(), "node_modules/pkg/index.ts").expect_err("ignored dir rejected");

        assert!(err.contains("읽을 수 없는 경로"));
    }

    #[test]
    fn rejects_unsupported_extension() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "assets/logo.png", b"png");

        let err = read_code_file_under(root.path(), "assets/logo.png").expect_err("extension rejected");

        assert!(err.contains("지원하지 않는 코드 파일"));
    }

    #[test]
    fn rejects_binary_file() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "src/binary.ts", b"abc\0def");

        let err = read_code_file_under(root.path(), "src/binary.ts").expect_err("binary rejected");

        assert!(err.contains("바이너리"));
    }

    #[cfg(unix)]
    #[test]
    fn rejects_symlink_escaping_root() {
        let outside = TempDir::new().expect("outside root");
        write(outside.path(), "secret.ts", b"export const secret = 1;\n");
        let root = TempDir::new().expect("temp root");
        std::os::unix::fs::symlink(outside.path().join("secret.ts"), root.path().join("link.ts"))
            .expect("symlink");

        let err = read_code_file_under(root.path(), "link.ts").expect_err("symlink escape rejected");

        assert!(err.contains("프로젝트 루트 밖"));
    }

    #[test]
    fn explorer_lists_docs_and_md_files() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "src/main.ts", b"x");
        write(root.path(), "apps/native_helper_mac/Sources/App.swift", b"import Foundation\n");
        write(root.path(), "docs/index.md", b"# hi");
        write(root.path(), "docs/superpowers/specs/design.md", b"spec");
        write(root.path(), "README.md", b"readme");
        write(root.path(), "docs/_config.yml", b"title: x\n"); // .yml 도 트리에 노출(config)
        // 제외 대상: hidden, ignored dirs, 미지원 확장자
        write(root.path(), ".env", b"SECRET=1");
        write(root.path(), "node_modules/x.js", b"x");
        write(root.path(), "target/debug/x.rs", b"x");
        write(root.path(), "docs/.DS_Store", b"x");

        let mut entries = list_explorer_files_under(root.path()).expect("list");
        entries.sort_by(|a, b| a.path.cmp(&b.path));
        let paths: Vec<String> = entries.iter().map(|entry| entry.path.clone()).collect();

        assert_eq!(
            paths,
            vec![
                "README.md".to_string(),
                "apps/native_helper_mac/Sources/App.swift".to_string(),
                "docs/_config.yml".to_string(),
                "docs/index.md".to_string(),
                "docs/superpowers/specs/design.md".to_string(),
                "src/main.ts".to_string(),
            ]
        );
        let docs_entry = entries.iter().find(|entry| entry.path == "docs/index.md").expect("docs entry");
        assert_eq!(docs_entry.category, "docs");
        let code_entry = entries.iter().find(|entry| entry.path == "src/main.ts").expect("code entry");
        assert_eq!(code_entry.category, "code");
    }

    #[test]
    fn explorer_lists_toml_and_yaml_as_data() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "pyproject.toml", b"[project]\nname = \"x\"\n");
        write(root.path(), "config/app.yaml", b"key: value\n");
        write(root.path(), "src/main.rs", b"fn main() {}\n");

        let entries = list_explorer_files_under(root.path()).expect("list");
        let toml = entries.iter().find(|e| e.path == "pyproject.toml").expect("toml listed");
        assert_eq!(toml.category, "data");
        let yaml = entries.iter().find(|e| e.path == "config/app.yaml").expect("yaml listed");
        assert_eq!(yaml.category, "data");
        let code = entries.iter().find(|e| e.path == "src/main.rs").expect("code listed");
        assert_eq!(code.category, "code");
    }

    #[test]
    fn reads_swift_file_with_swift_language() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "apps/native_helper_mac/Sources/App.swift", b"import Foundation\n");

        let result = read_code_file_under(root.path(), "apps/native_helper_mac/Sources/App.swift")
            .expect("read swift");

        assert_eq!(result.path, "apps/native_helper_mac/Sources/App.swift");
        assert_eq!(result.language, "Swift");
        assert!(result.content.starts_with("import Foundation"));
    }

    #[test]
    fn reads_markdown_file_with_markdown_language() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "docs/index.md", b"# title\n\nbody\n");

        let result = read_code_file_under(root.path(), "docs/index.md").expect("read md");

        assert_eq!(result.path, "docs/index.md");
        assert_eq!(result.language, "Markdown");
        assert!(result.content.starts_with("# title"));
    }
}
