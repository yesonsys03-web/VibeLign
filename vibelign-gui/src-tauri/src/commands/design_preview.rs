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
pub(crate) struct MotionTokens {
    pub duration: String,
    pub easing: String,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
pub(crate) struct MotionSpec {
    pub tokens: MotionTokens,
    pub recipe: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub(crate) struct StyleSpec {
    pub id: String,
    pub name: String,
    pub description: String,
    pub tokens: DesignTokens,
    pub recipe: String,
    #[serde(default)]
    pub motion: Option<MotionSpec>,
}

pub(crate) fn tokens_to_css_vars(t: &DesignTokens) -> String {
    format!(
        ":root{{--bg:{};--surface:{};--text:{};--primary:{};--accent:{};--border:{};--font:{};--radius:{};--shadow:{};}}",
        t.bg, t.surface, t.text, t.primary, t.accent, t.border, t.font_family, t.radius, t.shadow
    )
}

/// 색 토큰 :root 블록에 motion 토큰(--dur/--ease)을 합류. motion 없으면 색 토큰만.
pub(crate) fn style_to_css_vars(style: &StyleSpec) -> String {
    let mut s = tokens_to_css_vars(&style.tokens);
    if let Some(m) = &style.motion {
        if let Some(pos) = s.rfind('}') {
            s.insert_str(pos, &format!("--dur:{};--ease:{};", m.tokens.duration, m.tokens.easing));
        }
    }
    s
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
    out.push_str("중요: 파일을 저장하거나 Write/Edit/Bash 등 어떤 도구도 절대 사용하지 마세요. 완성된 HTML 문서 전체를 당신의 응답 본문(텍스트)으로만 출력하세요.\n\n");
    out.push_str("[기획안]\n");
    out.push_str(spec_md);
    out.push_str("\n\n[디자인 스타일]\n");
    out.push_str(&format!("{} — {}\n", style.name, style.description));
    out.push_str(&style.recipe);
    out.push_str("\n\n[고정 디자인 토큰 — 그대로 <style>에 포함하고, 색·폰트·모서리·그림자는 반드시 이 변수만 사용]\n");
    out.push_str(css_vars);
    out.push_str("\n\n[규칙]\n");
    out.push_str("- 응답은 <!doctype html>로 시작하는 단일 HTML 문서 하나뿐. 설명·인사·마크다운 펜스·도구 사용 금지.\n");
    out.push_str("- 위 :root 블록을 <style>에 그대로 넣고, 색/폰트/모서리/그림자는 var(--bg) 등 변수로만 참조.\n");
    out.push_str("- 외부 리소스(CDN·폰트·이미지 URL)·자바스크립트·인라인 이벤트 핸들러 금지. 인라인 CSS만.\n");
    out.push_str("- 기획안의 화면/구역을 실제 콘텐츠 예시로 채워 한 화면으로 배치.\n");
    out.push_str("\n[컴포넌트 커버리지 — 기획안에 맞는 것을 충실히 표현]\n");
    out.push_str("내비게이션·버튼(주/보조)·카드·입력/폼·뱃지·탭·모달 또는 시트·리스트/테이블·빈 상태(empty state) 중 ");
    out.push_str("기획안 화면에 어울리는 것들을 실제 콘텐츠 예시로 포함하세요. 기획안과 무관한 컴포넌트는 넣지 마세요.\n");
    if let Some(m) = &style.motion {
        out.push_str("\n[모션 — 이 스타일의 움직임 성격]\n");
        out.push_str(&m.recipe);
        out.push_str("\n- 목업에선 CSS 전환(transition)·@keyframes·:hover 로만 표현. 자바스크립트 금지.\n");
        out.push_str("- 지속·이징은 var(--dur)·var(--ease) 변수만 사용.\n");
        out.push_str("- @media (prefers-reduced-motion: reduce) 에서 모션을 비활성/축소.\n");
    }
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
    let css = style_to_css_vars(&style);
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
const MAX_TOKEN_LEN: usize = 200;
const MAX_RECIPE_LEN: usize = 2048;
const MAX_DESC_LEN: usize = 512;
const MAX_NAME_LEN: usize = 80;

/// CSS 토큰 값 안전성 — <style> 변수로 그대로 주입되므로 인젝션/이스케이프 토큰 거부.
/// 따옴표·쉼표·공백은 정상 값(border/shadow/fontFamily)이라 허용.
pub(crate) fn css_value_is_safe(v: &str) -> bool {
    let lower = v.to_ascii_lowercase();
    !v.trim().is_empty()
        && v.len() <= MAX_TOKEN_LEN
        && !v.contains([';', '{', '}', '<', '>'])
        && !lower.contains("url(")
        && !lower.contains("expression(")
        && !lower.contains("@import")
        && !lower.contains("javascript:")
        && !v.contains("/*")
        && !v.contains("*/")
        && !v.contains('\n')
        && !v.contains('\r')
}

/// 합성된 StyleSpec 검증. 토큰 안전성 + 길이 한도.
pub(crate) fn validate_style_spec(s: &StyleSpec) -> Result<(), String> {
    if s.name.trim().is_empty() || s.name.len() > MAX_NAME_LEN {
        return Err("스타일 이름이 비었거나 너무 깁니다".into());
    }
    if s.description.len() > MAX_DESC_LEN {
        return Err("스타일 설명이 너무 깁니다".into());
    }
    if s.recipe.trim().is_empty() || s.recipe.len() > MAX_RECIPE_LEN {
        return Err("스타일 recipe가 비었거나 너무 깁니다".into());
    }
    let t = &s.tokens;
    for v in [&t.bg, &t.surface, &t.text, &t.primary, &t.accent, &t.border, &t.font_family, &t.radius, &t.shadow] {
        if !css_value_is_safe(v) {
            return Err(format!("토큰 값이 안전하지 않습니다: {v}"));
        }
    }
    if let Some(m) = &s.motion {
        if !css_value_is_safe(&m.tokens.duration) || !css_value_is_safe(&m.tokens.easing) {
            return Err("모션 토큰 값이 안전하지 않습니다".into());
        }
        if m.recipe.len() > MAX_RECIPE_LEN {
            return Err("모션 recipe가 너무 깁니다".into());
        }
    }
    Ok(())
}

/// 시드(합성 프롬프트 등)에서 항상 `is_safe_style_id` 통과하는 id 생성.
pub(crate) fn safe_style_id_from(seed: &str) -> String {
    format!("custom-{}", &design_cache_key(seed)[..8])
}

/// 사용자 일상어 묘사(+선택적 기준 스타일) → 클로드가 StyleSpec JSON 을 내도록 하는 프롬프트.
pub(crate) fn build_synthesis_prompt(spec_md: &str, description: &str, base_style: Option<&StyleSpec>) -> String {
    let mut out = String::new();
    out.push_str("당신은 UI 디자인 시스템 전문가입니다. 사용자가 일상어로 묘사한 느낌을 하나의 디자인 스타일로 번역하세요.\n");
    out.push_str("중요: 파일 저장·Write/Edit/Bash 등 도구 사용 금지. 아래 스키마에 정확히 맞는 JSON 객체 하나만 응답 본문으로 출력(설명·마크다운 펜스 금지).\n\n");
    out.push_str("[JSON 스키마]\n");
    out.push_str("{\"id\":\"custom\",\"name\":\"<짧은 한국어 이름>\",\"description\":\"<한 줄 설명>\",\"tokens\":{\"bg\":\"#hex\",\"surface\":\"#hex 또는 rgba()\",\"text\":\"#hex\",\"primary\":\"#hex\",\"accent\":\"#hex\",\"border\":\"<예: 1px solid #ddd>\",\"fontFamily\":\"<예: 'Inter', system-ui, sans-serif>\",\"radius\":\"<예: 12px>\",\"shadow\":\"<예: 0 1px 3px rgba(0,0,0,0.1)>\"},\"recipe\":\"<시각 규칙 2~5문장>\",\"motion\":{\"tokens\":{\"duration\":\"<예: 200ms>\",\"easing\":\"<예: cubic-bezier(.4,0,.2,1)>\"},\"recipe\":\"<움직임 성격 1~2문장>\"}}\n\n");
    out.push_str("[제약]\n- 색은 #hex 또는 rgb()/rgba() 만. 토큰 값에 ; { } < > url( @import 금지.\n- 기획안 분위기와 사용자 묘사에 어울리는 조화로운 팔레트.\n\n");
    out.push_str("[기획안 맥락]\n");
    out.push_str(spec_md);
    if let Some(b) = base_style {
        out.push_str("\n\n[기준 스타일 — 아래를 출발점으로 변형]\n");
        out.push_str(&format!("{} — {}\n", b.name, b.description));
        out.push_str(&b.recipe);
        out.push_str(&format!("\n토큰: bg={} primary={} accent={} radius={} font={}\n",
            b.tokens.bg, b.tokens.primary, b.tokens.accent, b.tokens.radius, b.tokens.font_family));
    }
    out.push_str("\n\n[사용자 묘사 — 이 느낌으로]\n");
    out.push_str(description);
    out.push('\n');
    out
}

fn strip_json_fences(s: &str) -> String {
    let t = s.trim();
    let t = t.strip_prefix("```json").or_else(|| t.strip_prefix("```")).unwrap_or(t);
    let t = t.strip_suffix("```").unwrap_or(t);
    t.trim().to_string()
}

/// 클로드 원시 응답 → 검증된 StyleSpec. 펜스 제거 → JSON 파싱 → id 재발급 → 검증.
pub(crate) fn parse_synthesized_style(raw: &str, id_seed: &str) -> Result<StyleSpec, String> {
    let cleaned = strip_json_fences(raw);
    let mut spec: StyleSpec = serde_json::from_str(&cleaned)
        .map_err(|e| format!("스타일 JSON 파싱 실패: {e}"))?;
    spec.id = safe_style_id_from(id_seed);
    validate_style_spec(&spec)?;
    Ok(spec)
}

fn synth_cache_path(project_dir: &Path, key: &str) -> PathBuf {
    design_cache_dir(project_dir).join(format!("synth-{key}.json"))
}

#[tauri::command]
pub(crate) fn synthesize_style(
    project_dir: String,
    plan_path: String,
    description: String,
    base_style: Option<StyleSpec>,
) -> Result<StyleSpec, String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    if description.trim().is_empty() && base_style.is_none() {
        return Err("스타일 묘사를 입력해 주세요".into());
    }
    let spec_md = load_plan_markdown(dir, &plan_path)?;
    let prompt = build_synthesis_prompt(&spec_md, &description, base_style.as_ref());
    let key = design_cache_key(&prompt);
    if let Ok(cached) = std::fs::read_to_string(synth_cache_path(dir, &key)) {
        if let Ok(spec) = parse_synthesized_style(&cached, &prompt) {
            return Ok(spec);
        }
    }
    let raw = planning_persona::run_design_generation(dir, &prompt)
        .ok_or_else(|| "스타일 합성에 실패했습니다 (CLI 미설치/로그인/타임아웃)".to_string())?;
    let spec = parse_synthesized_style(&raw, &prompt)?;
    if let Some(p) = synth_cache_path(dir, &key).parent() {
        let _ = std::fs::create_dir_all(p);
    }
    let _ = std::fs::write(synth_cache_path(dir, &key), strip_json_fences(&raw));
    Ok(spec)
}

pub(crate) const MAX_CUSTOM_STYLES: usize = 50;

fn custom_styles_path(project_dir: &Path) -> PathBuf {
    design_cache_dir(project_dir).join("custom-styles.json")
}

/// 손상/없음 → 빈 목록 폴백(앱 안 깨지게).
pub(crate) fn load_custom_styles(project_dir: &Path) -> Vec<StyleSpec> {
    std::fs::read_to_string(custom_styles_path(project_dir))
        .ok()
        .and_then(|s| serde_json::from_str::<Vec<StyleSpec>>(&s).ok())
        .unwrap_or_default()
}

fn write_custom_styles(project_dir: &Path, list: &[StyleSpec]) -> Result<(), String> {
    let path = custom_styles_path(project_dir);
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(list).map_err(|e| e.to_string())?;
    std::fs::write(&path, json).map_err(|e| e.to_string())
}

/// 같은 id 면 교체, 아니면 추가(상한 초과 시 거부).
pub(crate) fn upsert_style(mut list: Vec<StyleSpec>, style: StyleSpec) -> Result<Vec<StyleSpec>, String> {
    if let Some(existing) = list.iter_mut().find(|s| s.id == style.id) {
        *existing = style;
        return Ok(list);
    }
    if list.len() >= MAX_CUSTOM_STYLES {
        return Err(format!("저장 가능한 커스텀 스타일은 최대 {MAX_CUSTOM_STYLES}개입니다"));
    }
    list.push(style);
    Ok(list)
}

#[tauri::command]
pub(crate) fn save_custom_style(project_dir: String, style: StyleSpec) -> Result<(), String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    if !is_safe_style_id(&style.id) {
        return Err("스타일 id 형식이 올바르지 않습니다".into());
    }
    validate_style_spec(&style)?;
    let list = upsert_style(load_custom_styles(dir), style)?;
    write_custom_styles(dir, &list)
}

#[tauri::command]
pub(crate) fn list_custom_styles(project_dir: String) -> Result<Vec<StyleSpec>, String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    Ok(load_custom_styles(dir))
}

#[tauri::command]
pub(crate) fn delete_custom_style(project_dir: String, style_id: String) -> Result<(), String> {
    let dir = Path::new(&project_dir);
    if !dir.is_absolute() {
        return Err("projectDir must be absolute".into());
    }
    let list: Vec<StyleSpec> = load_custom_styles(dir).into_iter().filter(|s| s.id != style_id).collect();
    write_custom_styles(dir, &list)
}

// ANCHOR: DESIGN_PREVIEW_END

#[cfg(test)]
mod custom_style_tests {
    use super::*;

    fn ok_tokens() -> DesignTokens {
        DesignTokens {
            bg: "#FFFFFF".into(), surface: "#F8FAFC".into(), text: "#0F172A".into(),
            primary: "#4F46E5".into(), accent: "#06B6D4".into(),
            border: "1px solid #E2E8F0".into(),
            font_family: "'Inter', system-ui, sans-serif".into(),
            radius: "12px".into(), shadow: "0 1px 3px rgba(15,23,42,0.08)".into(),
        }
    }
    fn ok_spec() -> StyleSpec {
        StyleSpec { id: "custom-x".into(), name: "테스트".into(), description: "설명".into(),
            tokens: ok_tokens(), recipe: "둥근 카드와 한 강조색.".into(), motion: None }
    }

    #[test]
    fn accepts_valid_spec() {
        assert!(validate_style_spec(&ok_spec()).is_ok());
    }
    #[test]
    fn rejects_css_injection_in_token() {
        let mut s = ok_spec();
        s.tokens.primary = "red;} body{display:none".into();
        assert!(validate_style_spec(&s).is_err());
    }
    #[test]
    fn rejects_url_and_import_and_expression() {
        for bad in ["url(http://x)", "@import 'x'", "expression(alert(1))", "<svg>"] {
            let mut s = ok_spec();
            s.tokens.bg = bad.into();
            assert!(validate_style_spec(&s).is_err(), "should reject {bad}");
        }
    }
    #[test]
    fn rejects_empty_name_or_recipe() {
        let mut s = ok_spec(); s.name = "  ".into();
        assert!(validate_style_spec(&s).is_err());
        let mut s2 = ok_spec(); s2.recipe = "".into();
        assert!(validate_style_spec(&s2).is_err());
    }
    #[test]
    fn safe_id_is_always_valid() {
        let id = safe_style_id_from("아무 시드 ABC !@#");
        assert!(is_safe_style_id(&id), "got {id}");
        assert!(id.starts_with("custom-"));
    }
    #[test]
    fn rejects_css_comment_injection() {
        for bad in ["red /*", "*/ }", "blue /* x */"] {
            let mut s = ok_spec();
            s.tokens.primary = bad.into();
            assert!(validate_style_spec(&s).is_err(), "should reject {bad}");
        }
    }
    #[test]
    fn rejects_newline_in_token() {
        let mut s = ok_spec();
        s.tokens.bg = "#fff\n--injected: blue".into();
        assert!(validate_style_spec(&s).is_err());
    }

    #[test]
    fn synthesis_prompt_has_schema_and_description() {
        let p = build_synthesis_prompt("기획안내용", "귀엽고 파스텔톤", None);
        assert!(p.contains("fontFamily"));      // JSON 스키마 안내 포함
        assert!(p.contains("기획안내용"));        // 기획 맥락 포함
        assert!(p.contains("귀엽고 파스텔톤"));    // 사용자 묘사 포함
        assert!(!p.contains("[기준 스타일"));     // base 없으면 변형 섹션 없음
    }
    #[test]
    fn synthesis_prompt_includes_base_style_when_given() {
        let base = ok_spec();
        let p = build_synthesis_prompt("기획", "더 밝게", Some(&base));
        assert!(p.contains("[기준 스타일"));
        assert!(p.contains(&base.name));
    }

    #[test]
    fn parses_fenced_json_and_reissues_id() {
        let raw = "```json\n{\"id\":\"x\",\"name\":\"파스텔\",\"description\":\"부드러운\",\"tokens\":{\"bg\":\"#FFF7FB\",\"surface\":\"#FFFFFF\",\"text\":\"#3A2E39\",\"primary\":\"#F7A8C4\",\"accent\":\"#A8D8F7\",\"border\":\"1px solid #F0D9E6\",\"fontFamily\":\"'Inter', sans-serif\",\"radius\":\"16px\",\"shadow\":\"0 2px 8px rgba(0,0,0,0.06)\"},\"recipe\":\"둥근 모서리와 파스텔 강조.\"}\n```";
        let spec = parse_synthesized_style(raw, "seed-1").expect("should parse");
        assert_eq!(spec.name, "파스텔");
        assert!(spec.id.starts_with("custom-"));
        assert!(is_safe_style_id(&spec.id));
    }
    #[test]
    fn rejects_unsafe_synthesized_tokens() {
        let raw = "{\"id\":\"x\",\"name\":\"나쁨\",\"description\":\"d\",\"tokens\":{\"bg\":\"#fff;}body{x\",\"surface\":\"#fff\",\"text\":\"#000\",\"primary\":\"#000\",\"accent\":\"#000\",\"border\":\"1px solid #000\",\"fontFamily\":\"sans-serif\",\"radius\":\"8px\",\"shadow\":\"none\"},\"recipe\":\"r\"}";
        assert!(parse_synthesized_style(raw, "seed").is_err());
    }
    #[test]
    fn rejects_non_json() {
        assert!(parse_synthesized_style("그냥 텍스트입니다", "seed").is_err());
    }

    #[test]
    fn upsert_replaces_same_id_and_caps() {
        let a = StyleSpec { id: "custom-a".into(), ..ok_spec() };
        let list = upsert_style(vec![], a.clone()).unwrap();
        assert_eq!(list.len(), 1);
        let a2 = StyleSpec { name: "교체".into(), ..a.clone() };
        let list = upsert_style(list, a2).unwrap();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].name, "교체");
    }
    #[test]
    fn upsert_rejects_over_cap() {
        let mut list = vec![];
        for i in 0..MAX_CUSTOM_STYLES {
            list = upsert_style(list, StyleSpec { id: format!("custom-{i}"), ..ok_spec() }).unwrap();
        }
        let over = upsert_style(list, StyleSpec { id: "custom-new".into(), ..ok_spec() });
        assert!(over.is_err());
    }
}
