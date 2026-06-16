// === ANCHOR: REPORT_PDF_TESTS_START ===
use super::report_pdf::{file_url_for, validate_html_path, validate_out_pdf};
use std::path::Path;

// ── out_pdf 검증 ────────────────────────────────────────────────────────────

#[test]
fn out_pdf_rejects_non_pdf_extension() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    assert!(validate_out_pdf(&root, &root.join("report.txt").to_string_lossy()).is_err());
    assert!(validate_out_pdf(&root, &root.join("report").to_string_lossy()).is_err());
}

#[test]
fn out_pdf_accepts_pdf_and_creates_parent() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    let out = root.join("nested").join("report.pdf");
    let res = validate_out_pdf(&root, &out.to_string_lossy()).expect("valid .pdf path");
    assert_eq!(res, out);
    // 부모 디렉터리가 생성되었는지 확인.
    assert!(out.parent().unwrap().is_dir());
}

#[test]
fn out_pdf_accepts_uppercase_extension() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    let out = root.join("report.PDF");
    assert!(validate_out_pdf(&root, &out.to_string_lossy()).is_ok());
}

#[test]
fn out_pdf_rejects_parent_traversal() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    // `..` 컴포넌트를 포함한 경로 → FS 사이드이펙트 없이 거부.
    let bad = root.join("sub").join("..").join("..").join("escape.pdf");
    assert!(validate_out_pdf(&root, &bad.to_string_lossy()).is_err());
}

#[test]
fn out_pdf_rejects_escape_outside_root() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    // 루트 밖의 절대 경로(tempdir 는 /tmp 하위이므로 /tmp/escape.pdf 는 루트 밖).
    let outside = Path::new("/tmp/vibelign_pdf_escape_test.pdf");
    // 루트가 /tmp 하위 디렉터리이면 /tmp 자체는 루트 밖이다.
    // (루트가 우연히 /tmp 와 같아지는 경우는 tempfile::tempdir 이 보장하는 구조상 없다.)
    if !outside.starts_with(&root) {
        assert!(validate_out_pdf(&root, &outside.to_string_lossy()).is_err());
    }
}

// ── html_path 검증 ──────────────────────────────────────────────────────────

#[test]
fn html_path_missing_is_error() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    assert!(validate_html_path(&root, "/no/such/report.html").is_err());
}

#[test]
fn html_path_existing_is_ok() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    let html = root.join("report.html");
    std::fs::write(&html, "<html></html>").unwrap();
    let res = validate_html_path(&root, &html.to_string_lossy()).expect("existing html");
    // 반환값은 정규화 경로여야 한다.
    assert_eq!(res, html.canonicalize().unwrap());
}

#[test]
fn html_path_rejects_outside_root() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path().canonicalize().unwrap();
    // 루트 밖의 실제로 존재하는 파일을 가리켜도 거부해야 한다.
    // /etc/hosts 는 macOS/Linux 에서 항상 존재.
    let outside = "/etc/hosts";
    assert!(validate_html_path(&root, outside).is_err());
}

// ── file_url_for ────────────────────────────────────────────────────────────

#[test]
fn file_url_has_scheme() {
    let url = file_url_for(Path::new("/tmp/x.html")).expect("valid abs path");
    assert!(url.starts_with("file:///tmp/x.html"), "got: {url}");
}

#[test]
fn file_url_percent_encodes_special_chars() {
    // 한글·공백·# 이 퍼센트 인코딩되어야 한다.
    let path = Path::new("/tmp/기획 보고서 #1.html");
    let url = file_url_for(path).expect("valid abs path");
    assert!(url.starts_with("file://"), "scheme missing: {url}");
    // 원시 한글 바이트나 공백·# 이 그대로 있으면 안 된다.
    assert!(!url.contains(' '), "raw space in URL: {url}");
    assert!(!url.contains('#'), "raw # in URL: {url}");
    // 공백은 %20, # 는 %23 으로 인코딩.
    assert!(url.contains("%20"), "space not encoded: {url}");
    assert!(url.contains("%23"), "# not encoded: {url}");
}
// === ANCHOR: REPORT_PDF_TESTS_END ===
