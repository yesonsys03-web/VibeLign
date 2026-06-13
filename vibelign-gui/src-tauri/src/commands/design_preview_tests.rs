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
    // 공백/탭/개행 구분자·이름과 = 사이 공백 우회 차단(FIX 4).
    assert!(validate_mockup_html("<!doctype html><div\tonclick=\"x\">").is_err());
    assert!(validate_mockup_html("<!doctype html><div onmouseover =\"x\">").is_err());
    assert!(validate_mockup_html("<!doctype html><div\nonload=\"x\">").is_err());
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
        motion: None,
    }
}

#[test]
fn style_css_vars_includes_motion_when_present() {
    let mut style = sample_style(); // 기존 헬퍼 (tokens=sample_tokens)
    style.motion = Some(MotionSpec {
        tokens: MotionTokens { duration: "80ms".into(), easing: "cubic-bezier(.2,0,0,1)".into() },
        recipe: "딱딱하게".into(),
    });
    let css = style_to_css_vars(&style);
    assert!(css.contains("--bg:#FFFDF5"));   // 색 토큰 유지
    assert!(css.contains("--dur:80ms"));     // 모션 토큰 추가
    assert!(css.contains("--ease:cubic-bezier(.2,0,0,1)"));
    assert!(css.trim_end().ends_with('}'));  // :root{} 블록 닫힘 유지
}

#[test]
fn style_css_vars_omits_motion_when_absent() {
    let style = sample_style(); // motion 없음
    let css = style_to_css_vars(&style);
    assert!(!css.contains("--dur"));
}

#[test]
fn style_spec_deserializes_without_motion_field() {
    let json = r##"{"id":"x","name":"X","description":"d",
      "tokens":{"bg":"#000","surface":"#000","text":"#000","primary":"#000","accent":"#000",
        "border":"1px","fontFamily":"sans","radius":"0","shadow":"none"},
      "recipe":"r"}"##;
    let s: StyleSpec = serde_json::from_str(json).expect("deserialize without motion");
    assert!(s.motion.is_none());
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
    // 에이전트 CLI 가 파일 저장 대신 HTML 을 텍스트로 출력하도록 강제하는 지시(2026-06-13 검증)
    assert!(p.contains("도구"));
}
#[test]
fn prompt_includes_feedback_and_previous() {
    let css = tokens_to_css_vars(&sample_tokens());
    let p = build_mockup_prompt("# 앱", &sample_style(), &css, Some("버튼 더 크게"), Some("<!doctype html><b>이전</b>"));
    assert!(p.contains("버튼 더 크게"));
    assert!(p.contains("이전")); // 직전 목업 포함
    assert!(p.contains("아래 현재 목업을 기준"));
}

#[test]
fn prompt_includes_motion_section_when_present() {
    let css = tokens_to_css_vars(&sample_tokens());
    let mut style = sample_style();
    style.motion = Some(MotionSpec {
        tokens: MotionTokens { duration: "80ms".into(), easing: "ease".into() },
        recipe: "딱딱하게 즉각".into(),
    });
    let p = build_mockup_prompt("# 앱", &style, &css, None, None);
    assert!(p.contains("딱딱하게 즉각"));               // recipe
    assert!(p.contains("CSS 전환"));                    // CSS-only 제약
    assert!(p.contains("자바스크립트 금지"));
    assert!(p.contains("prefers-reduced-motion"));      // 접근성
    assert!(p.contains("var(--dur)"));
}

#[test]
fn prompt_omits_motion_section_when_absent() {
    let css = tokens_to_css_vars(&sample_tokens());
    let p = build_mockup_prompt("# 앱", &sample_style(), &css, None, None); // motion None
    assert!(!p.contains("[모션 —"));
}

#[test]
fn validator_allows_css_motion() {
    // CSS 전환·@keyframes·:hover·@media 는 스크립트가 아니므로 통과해야 한다(회귀 가드).
    let html = "<!doctype html><style>@keyframes pop{from{transform:scale(.96)}to{transform:scale(1)}}\
.a{transition:transform var(--dur) var(--ease)}.b:hover{box-shadow:var(--shadow)}\
@media (prefers-reduced-motion: reduce){.a{transition:none}}</style><div class=\"a\"></div>";
    assert!(validate_mockup_html(html).is_ok());
}

#[test]
fn cache_key_stable_sha256() {
    let a = design_cache_key("p");
    assert_eq!(a, design_cache_key("p"));
    assert_ne!(a, design_cache_key("q"));
    assert_eq!(a.len(), 64);
}
#[test]
fn cache_roundtrip_and_prune_keeps_newest() {
    let root = tempfile::tempdir().expect("temp");
    for i in 0..5 {
        write_design_cache(root.path(), &design_cache_key(&format!("k{i}")), "<!doctype html>").expect("w");
    }
    prune_design_cache(root.path(), 3);
    let dir = root.path().join(".vibelign").join("design_preview");
    let count = std::fs::read_dir(&dir).unwrap().filter(|e| {
        e.as_ref().ok().map(|x| x.path().extension().map(|p| p == "html").unwrap_or(false)).unwrap_or(false)
    }).count();
    assert!(count <= 3);
}

#[test]
fn prune_preserves_saved_mockup_scaffolds() {
    // 확정 저장된 mockup-* 스캐폴드는 prune 이 절대 제거하지 않아야 한다(FIX 5).
    let root = tempfile::tempdir().expect("temp");
    // 확정 스캐폴드 몇 개 — save_mockup_file 이 만드는 이름 형태(mockup-<id>-<hash>.html).
    for i in 0..3 {
        save_mockup_file(root.path(), "neo", &format!("<!doctype html><b>{i}</b>")).expect("save");
    }
    // keep 보다 많은 <sha>.html 캐시 엔트리.
    for i in 0..5 {
        write_design_cache(root.path(), &design_cache_key(&format!("c{i}")), "<!doctype html>").expect("w");
    }
    prune_design_cache(root.path(), 2);
    let dir = root.path().join(".vibelign").join("design_preview");
    let mockups = std::fs::read_dir(&dir).unwrap().filter(|e| {
        e.as_ref().ok().and_then(|x| x.file_name().into_string().ok())
            .map(|n| n.starts_with("mockup-")).unwrap_or(false)
    }).count();
    assert_eq!(mockups, 3); // 모든 mockup-* 보존
}

#[test]
fn load_plan_reads_internal_relative_only() {
    let root = tempfile::tempdir().expect("temp");
    std::fs::create_dir_all(root.path().join("plans")).unwrap();
    std::fs::write(root.path().join("plans/x.md"), "# 본문").unwrap();
    assert!(load_plan_markdown(root.path(), "plans/x.md").unwrap().contains("본문"));
    assert!(load_plan_markdown(root.path(), "../x").is_err()); // 탈출 거부
}
#[test]
fn save_mockup_validates_and_returns_slash_path() {
    let root = tempfile::tempdir().expect("temp");
    let rel = save_mockup_file(root.path(), "neo-brutalism", "<!doctype html><b>m</b>").expect("save");
    assert!(rel.starts_with(".vibelign/design_preview/"));
    assert!(!rel.contains('\\')); // slash 정규화
    assert!(root.path().join(&rel).exists());
    assert!(save_mockup_file(root.path(), "../evil", "<!doctype html>").is_err()); // style_id 거부
    assert!(save_mockup_file(root.path(), "neo", "<script>").is_err());            // HTML 거부
}
#[test]
fn strip_code_fences_removes_html_fence() {
    assert_eq!(strip_code_fences("```html\n<!doctype html>\n```"), "<!doctype html>");
    assert_eq!(strip_code_fences("<!doctype html>"), "<!doctype html>");
}
