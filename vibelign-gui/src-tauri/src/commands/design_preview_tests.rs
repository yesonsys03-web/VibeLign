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

fn sample_tokens() -> DesignTokens {
    DesignTokens {
        bg: "#FFFDF5".into(), surface: "#FFFFFF".into(), text: "#111111".into(),
        primary: "#FFD400".into(), accent: "#FF4D4D".into(), border: "3px solid #111111".into(),
        font_family: "Archivo, sans-serif".into(), radius: "0px".into(), shadow: "6px 6px 0 #111111".into(),
    }
}
#[test]
fn css_vars_deterministic_and_complete() {
    let css = tokens_to_css_vars(&sample_tokens());
    assert!(css.starts_with(":root{"));
    assert!(css.contains("--bg:#FFFDF5"));
    assert!(css.contains("--primary:#FFD400"));
    assert!(css.contains("--shadow:6px 6px 0 #111111"));
    assert_eq!(tokens_to_css_vars(&sample_tokens()), css);
}

fn sample_style() -> StyleSpec {
    StyleSpec {
        id: "neo-brutalism".into(), name: "네오브루탈리즘".into(),
        description: "두꺼운 테두리".into(), tokens: sample_tokens(),
        recipe: "버튼은 굵은 테두리.".into(),
    }
}
#[test]
fn prompt_embeds_spec_css_recipe_constraints() {
    let css = tokens_to_css_vars(&sample_tokens());
    let p = build_mockup_prompt("# 예약 앱\n핵심: 캘린더", &sample_style(), &css, None, None);
    assert!(p.contains("예약 앱"));
    assert!(p.contains(":root{"));
    assert!(p.contains("버튼은 굵은 테두리"));
    assert!(p.contains("<!doctype html"));
    assert!(p.contains("var(--"));
}
#[test]
fn prompt_includes_feedback_and_previous() {
    let css = tokens_to_css_vars(&sample_tokens());
    let p = build_mockup_prompt("# 앱", &sample_style(), &css, Some("버튼 더 크게"), Some("<!doctype html><b>이전</b>"));
    assert!(p.contains("버튼 더 크게"));
    assert!(p.contains("이전")); // 직전 목업 포함
    assert!(p.contains("아래 현재 목업을 기준"));
}
