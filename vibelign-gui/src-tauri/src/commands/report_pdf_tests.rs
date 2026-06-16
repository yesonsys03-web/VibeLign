// === ANCHOR: REPORT_PDF_TESTS_START ===
use super::report_pdf::{file_url_for, validate_html_path, validate_out_pdf};
use std::path::Path;

#[test]
fn out_pdf_rejects_non_pdf_extension() {
    assert!(validate_out_pdf("/tmp/report.txt").is_err());
    assert!(validate_out_pdf("/tmp/report").is_err());
}

#[test]
fn out_pdf_accepts_pdf_and_creates_parent() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("nested").join("report.pdf");
    let out_str = out.to_string_lossy().into_owned();
    let res = validate_out_pdf(&out_str).expect("valid .pdf path");
    assert_eq!(res, out);
    // 부모 디렉터리가 생성되었는지 확인.
    assert!(out.parent().unwrap().is_dir());
}

#[test]
fn out_pdf_accepts_uppercase_extension() {
    let dir = tempfile::tempdir().unwrap();
    let out = dir.path().join("report.PDF");
    assert!(validate_out_pdf(&out.to_string_lossy()).is_ok());
}

#[test]
fn html_path_missing_is_error() {
    assert!(validate_html_path("/no/such/report.html").is_err());
}

#[test]
fn html_path_existing_is_ok() {
    let dir = tempfile::tempdir().unwrap();
    let html = dir.path().join("report.html");
    std::fs::write(&html, "<html></html>").unwrap();
    let res = validate_html_path(&html.to_string_lossy()).expect("existing html");
    assert_eq!(res, html);
}

#[test]
fn file_url_has_scheme() {
    let url = file_url_for(Path::new("/tmp/x.html"));
    assert!(url.starts_with("file:///tmp/x.html"));
}
// === ANCHOR: REPORT_PDF_TESTS_END ===
