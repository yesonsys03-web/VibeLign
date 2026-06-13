use super::design_preview::*;

#[test]
fn style_id_allowlist() {
    assert!(is_safe_style_id("neo-brutalism"));
    assert!(!is_safe_style_id("../etc"));
    assert!(!is_safe_style_id("Neo_Brutalism"));
    assert!(!is_safe_style_id(""));
}

#[test]
fn plan_path_rejects_escape() {
    assert!(validate_plan_path("plans/x.md").is_ok());
    assert!(validate_plan_path("../secret").is_err());
    assert!(validate_plan_path("/etc/passwd").is_err());
}

#[test]
fn html_validator_blocks_unsafe() {
    assert!(validate_mockup_html("<!doctype html><body>ok</body>").is_ok());
    assert!(validate_mockup_html("<body>no doctype</body>").is_err());
    assert!(validate_mockup_html("<!doctype html><script>x</script>").is_err());
    assert!(validate_mockup_html("<!doctype html><a href=\"https://x\">").is_err()); // 외부 href
    assert!(validate_mockup_html("<!doctype html><img src=\"//cdn/x.png\">").is_err()); // protocol-relative src
    assert!(validate_mockup_html("<!doctype html><style>@import 'x';</style>").is_err());
    assert!(validate_mockup_html("<!doctype html><button onclick=\"x\">").is_err());
}
#[test]
fn html_validator_allows_inline_svg_namespace() {
    // xmlns 의 http URL 은 리소스 로드가 아니라 통과해야 한다(인라인 SVG 아이콘).
    assert!(validate_mockup_html(
        "<!doctype html><svg xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M0 0\"/></svg>"
    ).is_ok());
}
