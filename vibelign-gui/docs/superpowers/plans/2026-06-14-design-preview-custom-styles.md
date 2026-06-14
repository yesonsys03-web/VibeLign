# 디자인 미리보기 — 클로드 스타일 합성(커스텀 디자인) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 일상어 묘사 또는 프리셋 변형으로 새 디자인을 만들면 클로드가 `StyleSpec`을 합성해 기존 엔진으로 렌더하고, 만든 스타일을 저장·재사용하게 한다.

**Architecture:** 신규는 "스타일 합성"(의도→StyleSpec JSON) 1단계뿐. 합성 결과를 기존 `generate_design_mockup`에 그대로 넘겨 HTML 생성·sandbox·확정·토큰바인딩을 재사용한다. 커스텀 스타일은 `.vibelign/design_preview/custom-styles.json`에 영속해 프리셋과 함께 표시한다.

**Tech Stack:** Tauri(Rust) 백엔드 + React 19/TS 프론트. 테스트: Rust 인라인 `#[cfg(test)]`(`cargo test`), Vitest 4 + @testing-library/react(`npm test`).

**Spec:** `docs/superpowers/specs/2026-06-14-design-preview-custom-styles-design.md`

---

## File Structure

- **Modify** `src-tauri/src/commands/design_preview.rs` — `validate_style_spec`, `safe_style_id_from`, `build_synthesis_prompt`, `parse_synthesized_style`, custom-style store helpers, 4개 `#[tauri::command]`, 인라인 테스트 모듈.
- **Modify** `src-tauri/src/lib.rs` — 신규 커맨드 4개 등록.
- **Modify** `src/lib/vib/design.ts` — invoke 래퍼 4종.
- **Modify** `src/pages/DesignPreview.tsx` — 자유입력·예시칩·합성결과카드·자동렌더·커스텀 병합·저장·삭제·변형.
- **Create** `src/lib/design-preview/customStyles.ts` — 순수 헬퍼(목록 병합) + 예시 칩 상수(테스트 가능 경계).
- **Create** `src/lib/design-preview/__tests__/customStyles.test.ts`.

기존 `generate_design_mockup`·`save_design_mockup`·`build_mockup_prompt`·`validate_mockup_html`·`StyleSpec`/`DesignTokens` 구조체는 무변경.

---

## Task 1: `validate_style_spec` + 안전 id 재발급 (Rust, TDD)

**Files:** Modify `src-tauri/src/commands/design_preview.rs` (`ANCHOR: DESIGN_PREVIEW_END` 직전에 추가; 테스트는 파일 끝 `#[cfg(test)] mod tests`)

- [ ] **Step 1: 실패 테스트 추가**

파일 끝(`// ANCHOR: DESIGN_PREVIEW_END` 다음 줄)에 테스트 모듈 추가:

```rust
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
}
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -20`
Expected: 컴파일 에러(`validate_style_spec`/`safe_style_id_from` 미정의).

- [ ] **Step 3: 구현 추가** (`// ANCHOR: DESIGN_PREVIEW_END` 직전)

```rust
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -20`
Expected: `test result: ok. 5 passed`.

- [ ] **Step 5: 커밋**

```bash
git add src-tauri/src/commands/design_preview.rs
git commit -m "feat(design-preview): validate_style_spec + 안전 id 재발급 (스타일 합성 안전장치)"
```

---

## Task 2: `build_synthesis_prompt` (Rust, TDD)

**Files:** Modify `src-tauri/src/commands/design_preview.rs`

- [ ] **Step 1: 실패 테스트 추가** (`custom_style_tests` 모듈 안에)

```rust
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15`
Expected: 컴파일 에러(`build_synthesis_prompt` 미정의).

- [ ] **Step 3: 구현 추가**

```rust
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
```

- [ ] **Step 4: 통과 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15`
Expected: `test result: ok. 7 passed`.

- [ ] **Step 5: 커밋**

```bash
git add src-tauri/src/commands/design_preview.rs
git commit -m "feat(design-preview): build_synthesis_prompt — 일상어→StyleSpec JSON 합성 프롬프트"
```

---

## Task 3: `parse_synthesized_style` + `synthesize_style` 커맨드 (Rust)

**Files:** Modify `src-tauri/src/commands/design_preview.rs`, `src-tauri/src/lib.rs`

- [ ] **Step 1: 실패 테스트 추가** (`custom_style_tests` 모듈)

```rust
    #[test]
    fn parses_fenced_json_and_reissues_id() {
        let raw = "```json\n{\"id\":\"x\",\"name\":\"파스텔\",\"description\":\"부드러운\",\"tokens\":{\"bg\":\"#FFF7FB\",\"surface\":\"#FFFFFF\",\"text\":\"#3A2E39\",\"primary\":\"#F7A8C4\",\"accent\":\"#A8D8F7\",\"border\":\"1px solid #F0D9E6\",\"fontFamily\":\"'Inter', sans-serif\",\"radius\":\"16px\",\"shadow\":\"0 2px 8px rgba(0,0,0,0.06)\"},\"recipe\":\"둥근 모서리와 파스텔 강조.\"}\n```";
        let spec = parse_synthesized_style(raw, "seed-1").expect("should parse");
        assert_eq!(spec.name, "파스텔");
        assert!(spec.id.starts_with("custom-"));   // id 재발급
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15`
Expected: 컴파일 에러(`parse_synthesized_style` 미정의).

- [ ] **Step 3: 구현 추가** (helper + command; helper는 `// ANCHOR: DESIGN_PREVIEW_END` 직전, command도 동일 영역)

```rust
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
    // 캐시 히트: 저장된 JSON 재파싱(검증 포함)
    if let Ok(cached) = std::fs::read_to_string(synth_cache_path(dir, &key)) {
        if let Ok(spec) = parse_synthesized_style(&cached, &prompt) {
            return Ok(spec);
        }
    }
    let raw = planning_persona::run_design_generation(dir, &prompt)
        .ok_or_else(|| "스타일 합성에 실패했습니다 (CLI 미설치/로그인/타임아웃)".to_string())?;
    let spec = parse_synthesized_style(&raw, &prompt)?;
    // 캐시 저장(실패 무시)
    if let Some(p) = synth_cache_path(dir, &key).parent() {
        let _ = std::fs::create_dir_all(p);
    }
    let _ = std::fs::write(synth_cache_path(dir, &key), strip_json_fences(&raw));
    Ok(spec)
}
```

- [ ] **Step 4: lib.rs 등록**

`src-tauri/src/lib.rs` 의 `commands::design_preview::save_design_mockup,` 다음 줄에 추가:

```rust
            commands::design_preview::synthesize_style,
```

- [ ] **Step 5: 통과 확인 + 빌드**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15 && cargo build 2>&1 | tail -3`
Expected: `test result: ok. 10 passed`, 빌드 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add src-tauri/src/commands/design_preview.rs src-tauri/src/lib.rs
git commit -m "feat(design-preview): synthesize_style 커맨드 — 의도→StyleSpec 합성+캐시"
```

---

## Task 4: 커스텀 스타일 저장소 + 커맨드 (Rust)

**Files:** Modify `src-tauri/src/commands/design_preview.rs`, `src-tauri/src/lib.rs`

- [ ] **Step 1: 실패 테스트 추가** (`custom_style_tests` 모듈)

```rust
    #[test]
    fn upsert_replaces_same_id_and_caps() {
        let a = StyleSpec { id: "custom-a".into(), ..ok_spec() };
        let list = upsert_style(vec![], a.clone()).unwrap();
        assert_eq!(list.len(), 1);
        // 같은 id 교체
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
```

- [ ] **Step 2: 실패 확인**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15`
Expected: 컴파일 에러(`upsert_style`/`MAX_CUSTOM_STYLES` 미정의).

- [ ] **Step 3: 구현 추가**

```rust
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
```

- [ ] **Step 4: lib.rs 등록**

`commands::design_preview::synthesize_style,` 다음에 3줄 추가:

```rust
            commands::design_preview::save_custom_style,
            commands::design_preview::list_custom_styles,
            commands::design_preview::delete_custom_style,
```

- [ ] **Step 5: 통과 + 빌드**

Run: `cd src-tauri && cargo test custom_style_tests 2>&1 | tail -15 && cargo build 2>&1 | tail -3`
Expected: `test result: ok. 12 passed`, 빌드 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add src-tauri/src/commands/design_preview.rs src-tauri/src/lib.rs
git commit -m "feat(design-preview): 커스텀 스타일 저장소(save/list/delete) + 상한"
```

---

## Task 5: 프론트 invoke 래퍼 + 순수 헬퍼 (TS, TDD)

**Files:** Modify `src/lib/vib/design.ts`; Create `src/lib/design-preview/customStyles.ts`, `src/lib/design-preview/__tests__/customStyles.test.ts`

- [ ] **Step 1: 실패 테스트 작성** `src/lib/design-preview/__tests__/customStyles.test.ts`

```ts
import { describe, expect, test } from "vitest";
import { mergeStyleLists, EXAMPLE_CHIPS } from "../customStyles";
import type { StyleSpec } from "../styles";

const mk = (id: string, name: string): StyleSpec => ({
  id, name, description: "d",
  tokens: { bg: "#fff", surface: "#fff", text: "#000", primary: "#000", accent: "#000",
    border: "1px solid #000", fontFamily: "sans-serif", radius: "8px", shadow: "none" },
  recipe: "r",
});

describe("customStyles", () => {
  test("mergeStyleLists: 내장 뒤에 커스텀을 붙인다", () => {
    const merged = mergeStyleLists([mk("a", "A")], [mk("custom-1", "C")]);
    expect(merged.map((s) => s.id)).toEqual(["a", "custom-1"]);
  });
  test("mergeStyleLists: 같은 id 커스텀은 내장을 가리지 않고 한 번만(커스텀 우선)", () => {
    const merged = mergeStyleLists([mk("a", "A")], [mk("a", "A-custom")]);
    expect(merged).toHaveLength(1);
    expect(merged[0].name).toBe("A-custom");
  });
  test("EXAMPLE_CHIPS: 비어있지 않은 일상어 시드", () => {
    expect(EXAMPLE_CHIPS.length).toBeGreaterThanOrEqual(4);
    expect(EXAMPLE_CHIPS.every((c) => c.trim().length > 0)).toBe(true);
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `npx vitest run src/lib/design-preview/__tests__/customStyles.test.ts`
Expected: FAIL — `../customStyles` 모듈 없음.

- [ ] **Step 3: 헬퍼 구현** `src/lib/design-preview/customStyles.ts`

```ts
import type { StyleSpec } from "./styles";

/** 빈 입력 막막함 해소용 일상어 예시 칩(클릭 시 입력칸에 채움). */
export const EXAMPLE_CHIPS: readonly string[] = [
  "귀엽고 파스텔톤으로",
  "신뢰감 있는 업무용",
  "게임처럼 화려하고 네온",
  "단아하고 여백 많은 일본풍",
  "따뜻한 종이 질감 레트로",
];

/** 내장 + 커스텀 병합. 같은 id 는 커스텀 우선(중복 제거). 내장 순서 유지 후 신규 커스텀 추가. */
export function mergeStyleLists(builtin: readonly StyleSpec[], custom: readonly StyleSpec[]): StyleSpec[] {
  const customById = new Map(custom.map((s) => [s.id, s]));
  const result: StyleSpec[] = builtin.map((b) => customById.get(b.id) ?? b);
  const builtinIds = new Set(builtin.map((b) => b.id));
  for (const c of custom) {
    if (!builtinIds.has(c.id)) result.push(c);
  }
  return result;
}
```

- [ ] **Step 4: invoke 래퍼 추가** `src/lib/vib/design.ts` (파일 끝, 기존 export 다음)

```ts
export function synthesizeStyle(req: {
  projectDir: string; planPath: string; description: string; baseStyle?: StyleSpec;
}): Promise<StyleSpec> {
  return invoke<StyleSpec>("synthesize_style", {
    projectDir: req.projectDir, planPath: req.planPath,
    description: req.description, baseStyle: req.baseStyle ?? null,
  });
}
export function saveCustomStyle(req: { projectDir: string; style: StyleSpec }): Promise<void> {
  return invoke<void>("save_custom_style", { projectDir: req.projectDir, style: req.style });
}
export function listCustomStyles(projectDir: string): Promise<StyleSpec[]> {
  return invoke<StyleSpec[]>("list_custom_styles", { projectDir });
}
export function deleteCustomStyle(req: { projectDir: string; styleId: string }): Promise<void> {
  return invoke<void>("delete_custom_style", { projectDir: req.projectDir, styleId: req.styleId });
}
```

- [ ] **Step 5: 통과 + 타입체크**

Run: `npx vitest run src/lib/design-preview/__tests__/customStyles.test.ts && npx tsc --noEmit`
Expected: 3 passed, tsc 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add src/lib/vib/design.ts src/lib/design-preview/customStyles.ts src/lib/design-preview/__tests__/customStyles.test.ts
git commit -m "feat(design-preview): 합성/커스텀 invoke 래퍼 + mergeStyleLists·예시칩 헬퍼"
```

---

## Task 6: DesignPreview — 자유입력·예시칩·합성결과카드·자동렌더

**Files:** Modify `src/pages/DesignPreview.tsx`

> 기존 파일 구조: `selectedId/html/feedback/loading/error` state, `generate()`, `confirm()`, `.page-content` 렌더(뒤로/h2/경고/프리셋 그리드/그려보기/iframe/피드백). 아래는 그 위에 합성 흐름을 얹는다. 정확 위치는 문자열로 식별.

- [ ] **Step 1: import + state + 합성 핸들러 추가**

`DesignPreview.tsx` 상단 import 에 추가:

```ts
import { generateDesignMockup, saveDesignMockup, synthesizeStyle } from "../lib/vib/design";
import { EXAMPLE_CHIPS } from "../lib/design-preview/customStyles";
```
(기존 `import { generateDesignMockup, saveDesignMockup } from "../lib/vib/design";` 줄을 위 첫 줄로 교체.)

컴포넌트 본문 state 영역(`const selected = ...` 위)에 추가:

```ts
  const [describe, setDescribe] = useState("");
  const [synth, setSynth] = useState<StyleSpec | null>(null);
```

`async function generate` 위에 합성 핸들러 추가:

```ts
  async function createFromDescription(baseStyle?: StyleSpec) {
    const desc = describe.trim();
    if (!desc && !baseStyle) return;
    setLoading(true);
    setError(null);
    try {
      const spec = await synthesizeStyle({ projectDir, planPath, description: desc, baseStyle });
      setSynth(spec);
      // 합성된 스타일로 곧장 목업 렌더
      const res = await generateDesignMockup({ projectDir, planPath, style: spec });
      setHtml(res.html);
      setSelectedId(spec.id);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }
```

`confirm()` 은 `selected`(프리셋) 기반인데 합성 스타일도 확정 가능해야 하므로, 확정에 쓸 스타일을 합성 우선으로 고르도록 `confirm()` 의 `if (!selected || !html) return;` 와 저장 호출을 아래로 교체:

```ts
  async function confirm() {
    const style = synth ?? selected;
    if (!style || !html) return;
    try {
      const mockupPath = await saveDesignMockup({ projectDir, styleId: style.id, html });
      onConfirm({ mockupPath, tokens: style.tokens, motion: style.motion });
    } catch (e) {
      setError(String(e));
    }
  }
```

- [ ] **Step 2: 자유입력 + 예시 칩 UI 추가**

프리셋 그리드 `</div>`(`{DESIGN_STYLES.map(...)}` 를 감싼 div) **다음**, "이 스타일로 그려보기" 버튼 **앞**에 삽입:

```tsx
      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A", display: "grid", gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 900 }}>✏️ 직접 만들기 — 원하는 느낌을 그냥 말로 적어보세요</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {EXAMPLE_CHIPS.map((chip) => (
            <button key={chip} type="button" onClick={() => setDescribe(chip)}
              style={{ fontSize: 12, padding: "4px 10px", border: "2px solid #1A1A1A", background: "#fff", borderRadius: 999 }}>
              {chip}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input aria-label="디자인 묘사" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder="예: 귀엽고 파스텔톤으로"
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || loading} onClick={() => void createFromDescription()}
            style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
            {loading ? "클로드가 그리는 중…" : "✦ 클로드에게 그려달라기"}
          </button>
        </div>
      </div>
```

- [ ] **Step 3: 합성 결과 카드("이런 스타일을 만들었어요")**

`{html && (` 블록 안, `<iframe ...>` **앞**에 삽입:

```tsx
          {synth && (
            <div style={{ border: "2px solid #1A1A1A", padding: "10px 12px", marginBottom: 8, background: "#F5F1E3", display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 900 }}>✦ 이런 스타일을 만들었어요 — {synth.name}</div>
              <div style={{ fontSize: 12, color: "#444" }}>{synth.description}</div>
              <div style={{ display: "flex", gap: 6 }}>
                {[synth.tokens.bg, synth.tokens.surface, synth.tokens.primary, synth.tokens.accent, synth.tokens.text].map((c, i) => (
                  <span key={i} title={c} style={{ width: 28, height: 28, background: c, border: "1px solid #1A1A1A", borderRadius: 4 }} />
                ))}
              </div>
              {synth.motion && <div style={{ fontSize: 11, color: "#666" }}>모션: {synth.motion.recipe}</div>}
            </div>
          )}
```

- [ ] **Step 4: 타입체크 + 빌드**

Run: `npx tsc --noEmit && npm run build 2>&1 | grep -E "built in|error" | head -3`
Expected: tsc 에러 없음, `built in`.

- [ ] **Step 5: 커밋**

```bash
git add src/pages/DesignPreview.tsx
git commit -m "feat(design-preview): 일상어 자유입력+예시칩, 합성 결과 카드, 합성→목업 자동 렌더"
```

---

## Task 7: DesignPreview — 커스텀 저장/목록 병합/삭제 + 프리셋 변형

**Files:** Modify `src/pages/DesignPreview.tsx`

- [ ] **Step 1: import + 커스텀 목록 state + 마운트 로드**

import 추가:

```ts
import { listCustomStyles, saveCustomStyle, deleteCustomStyle } from "../lib/vib/design";
import { mergeStyleLists } from "../lib/design-preview/customStyles";
import { useEffect } from "react";
```
(기존 `import { useState } from "react";` 를 `import { useEffect, useState } from "react";` 로.)

state + 로드 effect 추가:

```ts
  const [custom, setCustom] = useState<StyleSpec[]>([]);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  useEffect(() => {
    listCustomStyles(projectDir).then(setCustom).catch(() => setCustom([]));
  }, [projectDir]);
  const allStyles = mergeStyleLists(DESIGN_STYLES, custom);
  const customIds = new Set(custom.map((s) => s.id));
```

- [ ] **Step 2: 그리드를 병합 목록으로 + 커스텀 삭제 버튼**

프리셋 그리드의 `{DESIGN_STYLES.map((s) => (` 를 `{allStyles.map((s) => (` 로 바꾸고, 각 스타일 버튼 `<strong>{s.name}</strong>` 아래(설명 div 다음)에 커스텀 삭제 표시 추가:

```tsx
            {customIds.has(s.id) && (
              <span
                role="button"
                aria-label={`${s.name} 삭제`}
                onClick={(e) => {
                  e.stopPropagation();
                  void deleteCustomStyle({ projectDir, styleId: s.id }).then(() =>
                    listCustomStyles(projectDir).then(setCustom),
                  );
                }}
                style={{ fontSize: 11, color: "#b42318", fontWeight: 800, cursor: "pointer" }}
              >
                ✕ 삭제
              </span>
            )}
```

- [ ] **Step 3: "이 스타일 저장하기" 버튼 (합성 결과에 한해)**

Task 6 의 피드백 컨트롤 div(다시 그리기/이 디자인으로 만들기) 안, "이 디자인으로 만들기" 버튼 다음에 추가:

```tsx
            {synth && (
              <button className="btn" disabled={loading} onClick={() => {
                void saveCustomStyle({ projectDir, style: synth })
                  .then(() => listCustomStyles(projectDir).then(setCustom))
                  .then(() => setSavedMsg("스타일을 저장했어요 — 목록에서 다시 쓸 수 있어요"))
                  .catch((e) => setError(String(e)));
              }}>
                ＋ 이 스타일 저장하기
              </button>
            )}
            {savedMsg && <span style={{ fontSize: 12, fontWeight: 800, color: "#166534", alignSelf: "center" }}>{savedMsg}</span>}
```

- [ ] **Step 4: 프리셋 변형 입력 (프리셋 선택 시)**

"이 스타일로 그려보기" 버튼 다음(또는 그 근처)에, 프리셋이 선택됐고 합성 결과 카드는 없을 때 변형 입력 노출:

```tsx
      {selected && !synth && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input aria-label="스타일 변형" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder={`예: "${selected.name}" 에서 더 밝게 / 더 미니멀하게`}
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || loading} onClick={() => void createFromDescription(selected)}>
            ✦ 이 스타일 변형하기
          </button>
        </div>
      )}
```

- [ ] **Step 5: 타입체크 + 테스트 + 빌드**

Run: `npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests " | tail -2 && npm run build 2>&1 | grep -E "built in|error" | head -2`
Expected: tsc 에러 없음, 전체 테스트 통과, `built in`.

- [ ] **Step 6: 커밋**

```bash
git add src/pages/DesignPreview.tsx
git commit -m "feat(design-preview): 커스텀 스타일 저장/목록병합/삭제 + 프리셋 변형 입력"
```

---

## Task 8: 전체 검증 + 수동 통합

**Files:** (검증만)

- [ ] **Step 1: Rust 전체 테스트 + 빌드**

Run: `cd src-tauri && cargo test 2>&1 | tail -5`
Expected: 전부 ok(신규 12 포함), 회귀 없음.

- [ ] **Step 2: 프론트 전체 + 빌드**

Run: `npx tsc --noEmit && npm test 2>&1 | grep -E "Test Files|Tests " && npm run build 2>&1 | grep -E "built in|error"`
Expected: tsc 클린, 신규 3 포함 전부 통과, `built in`.

- [ ] **Step 3: 수동 통합 (dev 앱)** — 작업방 에이전트와 안 겹치는 시점에:
  1. `npm run tauri dev` → 알람앱 등 프로젝트에서 기획안 확정 후 디자인 미리보기 진입.
  2. 예시 칩 클릭 → 입력칸 채워짐 확인.
  3. "클로드에게 그려달라기" → **합성 결과 카드(이름·팔레트 스와치)** + 목업 렌더 확인.
  4. "이 스타일 저장하기" → 그리드에 커스텀 배지로 추가, 재진입(탭 이동 후 복귀)해도 남아있는지.
  5. 프리셋 선택 → "이 스타일 변형하기" → 변형 합성/렌더 확인.
  6. 커스텀 "✕ 삭제" → 목록에서 제거.
  7. "이 디자인으로 만들기"(합성 스타일) → 작업방 바인딩까지 정상.

- [ ] **Step 4: 검증 보고** (커밋 없음) — 위 결과 기록.

---

## Self-Review (작성자 점검 완료)

- **스펙 커버리지**: §3-3 synthesize/save/list/delete→Task 3·4, validate_style_spec→Task 1, build_synthesis_prompt→Task 2, §3-4 프론트 UX→Task 5·6·7(자유입력·칩·결과카드·병합·저장·삭제·변형), §3-5 결과노출→Task 6 Step3, §4 검증→Task 1·3, §7 테스트→각 Task TDD + Task 8. 전 항목 매핑.
- **플레이스홀더 없음**: 모든 코드/명령/기대출력 구체.
- **타입 일관성**: `StyleSpec`(id·name·description·tokens·recipe·motion), `DesignTokens`(camelCase `fontFamily`) 백엔드 serde와 프론트 타입 일치. `synthesizeStyle({baseStyle})`→백엔드 `base_style` 매핑, `validate_style_spec`/`safe_style_id_from`/`upsert_style`/`parse_synthesized_style`/`mergeStyleLists`/`EXAMPLE_CHIPS` 시그니처가 정의(Task 1·2·3·4·5)와 사용처(Task 3·4·6·7) 일치.
- **재사용**: 생성·sandbox·확정·바인딩 엔진 무변경, 합성 단계만 추가.
