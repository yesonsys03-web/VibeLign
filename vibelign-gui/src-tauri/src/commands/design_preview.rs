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
        if bytes[i] == b' ' && bytes[i + 1] == b'o' && bytes[i + 2] == b'n' {
            let mut j = i + 3;
            while j < bytes.len() && bytes[j].is_ascii_lowercase() {
                j += 1;
            }
            if j > i + 3 && j < bytes.len() && bytes[j] == b'=' {
                return true;
            }
        }
        i += 1;
    }
    false
}
// ANCHOR: DESIGN_PREVIEW_END
