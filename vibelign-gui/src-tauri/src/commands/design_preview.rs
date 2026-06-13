// ANCHOR: DESIGN_PREVIEW_START
use std::path::Path;

const MAX_MOCKUP_BYTES: usize = 512 * 1024;

/// style_id 화이트리스트: 소문자·숫자·하이픈만, 1~64자.
pub(crate) fn is_safe_style_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
}

/// plan_path 는 프로젝트 내부 상대경로만 허용(절대·상위참조·루트시작 거부).
pub(crate) fn validate_plan_path(plan_path: &str) -> Result<(), String> {
    let p = Path::new(plan_path);
    if p.is_absolute() {
        return Err("기획안 경로는 프로젝트 내부 상대경로여야 합니다".into());
    }
    use std::path::Component;
    for c in p.components() {
        match c {
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                return Err("기획안 경로에 상위 참조('..')는 허용되지 않습니다".into());
            }
            _ => {}
        }
    }
    Ok(())
}

/// 확정·캐시 전 HTML 안전 검증. JS·외부 리소스 로드·인라인 핸들러·과대 크기 거부.
/// 주의: 외부 "리소스 로드"(src/href/url()/@import → http(s)/protocol-relative)만 막고,
/// SVG 네임스페이스(xmlns="http://www.w3.org/2000/svg")처럼 로드가 아닌 URL 속성은 허용한다.
pub(crate) fn validate_mockup_html(html: &str) -> Result<(), String> {
    if html.len() > MAX_MOCKUP_BYTES {
        return Err("목업 HTML이 너무 큽니다".into());
    }
    let lower = html.to_ascii_lowercase();
    if !lower.trim_start().starts_with("<!doctype html") {
        return Err("HTML 문서(<!doctype html>)가 아닙니다".into());
    }
    // 스크립트·iframe·자바스크립트 URL 차단
    for bad in ["<script", "<iframe", "javascript:"] {
        if lower.contains(bad) {
            return Err(format!("허용되지 않는 내용 포함: {bad}"));
        }
    }
    // 외부 리소스 로드 차단(src/href/css url/@import 가 외부 http(s)/protocol-relative 일 때만).
    // xmlns 같은 비-로드 URL 속성은 통과.
    for bad in [
        "src=\"http", "src='http", "src=\"//", "src='//",
        "href=\"http", "href='http", "href=\"//", "href='//",
        "url(http", "url(\"http", "url('http", "url(//", "@import",
    ] {
        if lower.contains(bad) {
            return Err(format!("외부 리소스 로드는 허용되지 않습니다: {bad}"));
        }
    }
    if has_inline_event_handler(&lower) {
        return Err("인라인 이벤트 핸들러(on*=)는 허용되지 않습니다".into());
    }
    Ok(())
}

/// ` on<letters>=` 패턴(onclick= 등)을 정규식 없이 스캔.
fn has_inline_event_handler(lower: &str) -> bool {
    let bytes = lower.as_bytes();
    let mut i = 0;
    while i + 3 < bytes.len() {
        let delim = matches!(bytes[i], b' ' | b'\t' | b'\n' | b'\r' | b'/');
        if delim && bytes[i + 1] == b'o' && bytes[i + 2] == b'n' {
            let mut j = i + 3;
            while j < bytes.len() && bytes[j].is_ascii_lowercase() { j += 1; }
            let name_len = j - (i + 3);
            while j < bytes.len() && matches!(bytes[j], b' ' | b'\t' | b'\n' | b'\r') { j += 1; }
            if name_len > 0 && j < bytes.len() && bytes[j] == b'=' {
                return true;
            }
        }
        i += 1;
    }
    false
}

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub(crate) struct DesignTokens {
    pub bg: String,
    pub surface: String,
    pub text: String,
    pub primary: String,
    pub accent: String,
    pub border: String,
    #[serde(rename = "fontFamily")]
    pub font_family: String,
    pub radius: String,
    pub shadow: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub(crate) struct StyleSpec {
    pub id: String,
    pub name: String,
    pub description: String,
    pub tokens: DesignTokens,
    pub recipe: String,
}

pub(crate) fn tokens_to_css_vars(t: &DesignTokens) -> String {
    format!(
        ":root{{--bg:{};--surface:{};--text:{};--primary:{};--accent:{};--border:{};--font:{};--radius:{};--shadow:{};}}",
        t.bg, t.surface, t.text, t.primary, t.accent, t.border, t.font_family, t.radius, t.shadow
    )
}

pub(crate) fn build_mockup_prompt(
    spec_md: &str,
    style: &StyleSpec,
    css_vars: &str,
    feedback: Option<&str>,
    previous_html: Option<&str>,
) -> String {
    let mut out = String::new();
    out.push_str("당신은 웹 UI 디자이너입니다. 아래 기획안을 단 하나의 자기완결 HTML 문서로 된 고충실 컬러 목업으로 만드세요.\n\n");
    out.push_str("[기획안]\n");
    out.push_str(spec_md);
    out.push_str("\n\n[디자인 스타일]\n");
    out.push_str(&format!("{} — {}\n", style.name, style.description));
    out.push_str(&style.recipe);
    out.push_str("\n\n[고정 디자인 토큰 — 그대로 <style>에 포함하고, 색·폰트·모서리·그림자는 반드시 이 변수만 사용]\n");
    out.push_str(css_vars);
    out.push_str("\n\n[규칙]\n");
    out.push_str("- 출력은 <!doctype html>로 시작하는 단일 HTML 문서 하나. 설명·마크다운 펜스 금지.\n");
    out.push_str("- 위 :root 블록을 <style>에 그대로 넣고, 색/폰트/모서리/그림자는 var(--bg) 등 변수로만 참조.\n");
    out.push_str("- 외부 리소스(CDN·폰트·이미지 URL)·자바스크립트·인라인 이벤트 핸들러 금지. 인라인 CSS만.\n");
    out.push_str("- 기획안의 화면/구역을 실제 콘텐츠 예시로 채워 한 화면으로 배치.\n");
    if let Some(prev) = previous_html {
        out.push_str("\n[아래 현재 목업을 기준으로, 다음 수정 요청만 반영해 전체 HTML을 다시 출력]\n");
        out.push_str(prev);
        out.push('\n');
    }
    if let Some(fb) = feedback {
        out.push_str("\n[수정 요청 — 우선 반영]\n");
        out.push_str(fb);
        out.push('\n');
    }
    out
}

use sha2::{Digest, Sha256};
use std::path::PathBuf;

pub(crate) fn design_cache_key(prompt: &str) -> String {
    let mut h = Sha256::new();
    h.update(prompt.as_bytes());
    format!("{:x}", h.finalize())
}
fn design_cache_dir(project_dir: &Path) -> PathBuf {
    project_dir.join(".vibelign").join("design_preview")
}
fn design_cache_path(project_dir: &Path, key: &str) -> PathBuf {
    design_cache_dir(project_dir).join(format!("{key}.html"))
}
pub(crate) fn read_design_cache(project_dir: &Path, key: &str) -> Option<String> {
    std::fs::read_to_string(design_cache_path(project_dir, key)).ok()
}
pub(crate) fn write_design_cache(project_dir: &Path, key: &str, html: &str) -> Result<(), String> {
    let path = design_cache_path(project_dir, key);
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&path, html).map_err(|e| e.to_string())
}
/// 최근 keep 개만 남기고 오래된 .html 캐시를 제거(mtime 기준).
pub(crate) fn prune_design_cache(project_dir: &Path, keep: usize) {
    let dir = design_cache_dir(project_dir);
    let mut files: Vec<(std::time::SystemTime, PathBuf)> = match std::fs::read_dir(&dir) {
        Ok(rd) => rd
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.extension().map(|x| x == "html").unwrap_or(false))
            // 확정 저장된 스캐폴드(mockup-<id>-<hash>.html)는 prune 대상에서 제외 — <sha>.html 캐시만 sweep.
            .filter(|p| {
                !p.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.starts_with("mockup-"))
                    .unwrap_or(false)
            })
            .filter_map(|p| std::fs::metadata(&p).and_then(|m| m.modified()).ok().map(|t| (t, p)))
            .collect(),
        Err(_) => return,
    };
    if files.len() <= keep {
        return;
    }
    files.sort_by(|a, b| b.0.cmp(&a.0)); // 최신 먼저
    for (_, path) in files.into_iter().skip(keep) {
        let _ = std::fs::remove_file(path);
    }
}

use crate::commands::planning_persona;

pub(crate) fn strip_code_fences(s: &str) -> String {
    let t = s.trim();
    let t = t.strip_prefix("```html").or_else(|| t.strip_prefix("```")).unwrap_or(t);
    let t = t.strip_suffix("```").unwrap_or(t);
    t.trim().to_string()
}

pub(crate) fn load_plan_markdown(project_dir: &Path, plan_path: &str) -> Result<String, String> {
    validate_plan_path(plan_path)?;
    let full = project_dir.join(plan_path);
    // 심볼릭/조작 경로 방어: 정규화 후 프로젝트 내부 확인
    let canon_root = std::fs::canonicalize(project_dir).map_err(|e| e.to_string())?;
    let canon_full = std::fs::canonicalize(&full).map_err(|e| format!("기획안 읽기 실패({plan_path}): {e}"))?;
    if !canon_full.starts_with(&canon_root) {
        return Err("기획안 경로가 프로젝트 밖을 가리킵니다".into());
    }
    std::fs::read_to_string(&canon_full).map_err(|e| format!("기획안 읽기 실패({plan_path}): {e}"))
}

pub(crate) fn save_mockup_file(project_dir: &Path, style_id: &str, html: &str) -> Result<String, String> {
    if !is_safe_style_id(style_id) {
        return Err("스타일 id 형식이 올바르지 않습니다".into());
    }
    validate_mockup_html(html)?;
    let key = design_cache_key(&format!("{style_id}:{html}"));
    let rel = format!(".vibelign/design_preview/mockup-{style_id}-{}.html", &key[..12]);
    let full = project_dir.join(&rel);
    if let Some(parent) = full.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&full, html).map_err(|e| e.to_string())?;
    Ok(rel) // 이미 슬래시 리터럴로 구성됨
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct DesignMockupResult {
    pub html: String,
    pub cached: bool,
}

#[tauri::command]
pub(crate) fn generate_design_mockup(
    project_dir: String,
    plan_path: String,
    style: StyleSpec,
    feedback: Option<String>,
    previous_html: Option<String>,
) -> Result<DesignMockupResult, String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    if !is_safe_style_id(&style.id) {
        return Err("스타일 id 형식이 올바르지 않습니다".into());
    }
    let spec_md = load_plan_markdown(dir, &plan_path)?;
    let css = tokens_to_css_vars(&style.tokens);
    let prompt = build_mockup_prompt(&spec_md, &style, &css, feedback.as_deref(), previous_html.as_deref());
    let key = design_cache_key(&prompt);
    if let Some(html) = read_design_cache(dir, &key) {
        return Ok(DesignMockupResult { html, cached: true });
    }
    let raw = planning_persona::run_design_generation(dir, &prompt)
        .ok_or_else(|| "디자인 목업 생성에 실패했습니다 (CLI 미설치/로그인/타임아웃)".to_string())?;
    let html = strip_code_fences(&raw);
    validate_mockup_html(&html)?; // 저장 전 검증
    write_design_cache(dir, &key, &html)?;
    prune_design_cache(dir, 50);
    Ok(DesignMockupResult { html, cached: false })
}

#[tauri::command]
pub(crate) fn save_design_mockup(
    project_dir: String,
    style_id: String,
    html: String,
) -> Result<String, String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    save_mockup_file(dir, &style_id, &html)
}
// ANCHOR: DESIGN_PREVIEW_END
