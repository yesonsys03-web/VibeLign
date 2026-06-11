// === ANCHOR: PLANNING_CHAT_CONTRACT_START ===
// 작업 계약 — 기획안 확정 시 페르소나로 추출하는 목표·손댈 범위·금지·완료 기준.
// 근거: plans/2026-06-11-계약트랙-design.md. readiness(판정)·cards(결정) 추출 패턴과 동일 계열.
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use super::planning_chat_readiness::extract_json;

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub(crate) enum ScopeKind {
    File,
    Dir,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ScopeEntry {
    pub(crate) path: String,
    pub(crate) kind: ScopeKind,
    /// 초보자 노출 텍스트 — 한국어, 영문 용어 금지(루브릭에서 강제).
    pub(crate) reason: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PlanningContract {
    pub(crate) version: u32,
    /// epoch ms 문자열 — 메시지 createdAt 등 기존 타임스탬프 관례와 동일.
    pub(crate) extracted_at: String,
    pub(crate) goal: String,
    pub(crate) scope: Vec<ScopeEntry>,
    pub(crate) exclusions: Vec<String>,
    pub(crate) done_criteria: Vec<String>,
}

fn string_list(value: &serde_json::Value, key: &str) -> Vec<String> {
    value
        .get(key)
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| item.as_str())
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

/// CLI 출력 텍스트 → 계약. goal이 비면 계약 전체를 실패로 본다(빈 계약은 무가치).
/// scope의 kind가 "file"/"dir"가 아니면 그 entry만 버린다(불확실하면 통과시키지 않는다 — readiness와 동일 보수성).
pub(crate) fn parse_contract(text: &str, now: &str) -> Option<PlanningContract> {
    let json = extract_json(text)?;
    let value = serde_json::from_str::<serde_json::Value>(json).ok()?;
    let goal = value.get("goal").and_then(|v| v.as_str()).map(str::trim).unwrap_or("");
    if goal.is_empty() {
        return None;
    }
    let scope = value
        .get("scope")
        .and_then(|v| v.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|item| {
                    let path = item.get("path")?.as_str()?.trim().to_string();
                    if path.is_empty() {
                        return None;
                    }
                    let kind = match item.get("kind").and_then(|v| v.as_str()).map(str::trim) {
                        Some("file") => ScopeKind::File,
                        Some("dir") => ScopeKind::Dir,
                        _ => return None,
                    };
                    let reason = item
                        .get("reason")
                        .and_then(|v| v.as_str())
                        .map(|s| s.trim().to_string())
                        .unwrap_or_default();
                    Some(ScopeEntry { path, kind, reason })
                })
                .collect()
        })
        .unwrap_or_default();
    Some(PlanningContract {
        version: 1,
        extracted_at: now.to_string(),
        goal: goal.to_string(),
        scope,
        exclusions: string_list(&value, "exclusions"),
        done_criteria: string_list(&value, "doneCriteria"),
    })
}

/// 페르소나 프롬프트에 넣을 project_map 요약 상한. core 카테고리 우선.
const PROJECT_MAP_SUMMARY_LIMIT: usize = 200;

/// `.vibelign/project_map.json` → "path (category)" 줄 목록 + 잘림 여부.
/// 파일이 없거나 깨졌으면 빈 목록(루브릭이 "목록에 있는 경로만"이라 scope가 비게 됨 — 안전한 강등).
pub(crate) fn project_map_summary(project_dir: &Path) -> (Vec<String>, bool) {
    let raw = match std::fs::read_to_string(project_dir.join(".vibelign/project_map.json")) {
        Ok(raw) => raw,
        Err(_) => return (Vec::new(), false),
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&raw) else {
        return (Vec::new(), false);
    };
    let Some(files) = value.get("files").and_then(|v| v.as_object()) else {
        return (Vec::new(), false);
    };
    let mut rows: Vec<(bool, String)> = files
        .iter()
        .map(|(path, meta)| {
            let category = meta.get("category").and_then(|v| v.as_str()).unwrap_or("other");
            (category == "core", format!("{path} ({category})"))
        })
        .collect();
    // core 우선, 같은 우선순위 안에서는 경로순(결정적 출력 — 테스트 가능성).
    rows.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    let truncated = rows.len() > PROJECT_MAP_SUMMARY_LIMIT;
    rows.truncate(PROJECT_MAP_SUMMARY_LIMIT);
    (rows.into_iter().map(|(_, line)| line).collect(), truncated)
}

/// 환각 경로 2차 차단(1차는 루브릭): project_map 또는 디스크에 실존하는 경로만 통과.
/// dir entry는 끝 '/'를 보장해 prefix 매칭(scopeReport)의 모호성을 없앤다.
pub(crate) fn validate_scope(project_dir: &Path, scope: Vec<ScopeEntry>) -> Vec<ScopeEntry> {
    scope
        .into_iter()
        .filter_map(|mut entry| {
            let normalized = entry.path.replace('\\', "/");
            entry.path = normalized.trim_start_matches("./").to_string();
            match entry.kind {
                ScopeKind::File => {
                    if project_dir.join(&entry.path).is_file() {
                        Some(entry)
                    } else {
                        None
                    }
                }
                ScopeKind::Dir => {
                    let trimmed = entry.path.trim_end_matches('/').to_string();
                    if trimmed.is_empty() {
                        return None; // 루트 전체를 scope로 잡는 건 무의미 — 버림
                    }
                    if project_dir.join(&trimmed).is_dir() {
                        entry.path = format!("{trimmed}/");
                        Some(entry)
                    } else {
                        None
                    }
                }
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn entry(path: &str, kind: ScopeKind) -> ScopeEntry {
        ScopeEntry { path: path.to_string(), kind, reason: String::new() }
    }

    #[test]
    fn parse_extracts_contract_from_fenced_json() {
        let text = r#"결과:
```json
{
  "goal": "예약 화면을 만든다",
  "scope": [
    { "path": "src/pages/Home.tsx", "kind": "file", "reason": "예약 진입 버튼이 있는 곳" },
    { "path": "src/components/nav/", "kind": "dir", "reason": "이동 안내를 더하는 곳" }
  ],
  "exclusions": ["결제 흐름은 건드리지 않음"],
  "doneCriteria": ["예약 버튼을 누르면 예약 화면이 뜬다"]
}
```
끝."#;
        let contract = parse_contract(text, "123").expect("parsed");
        assert_eq!(contract.version, 1);
        assert_eq!(contract.extracted_at, "123");
        assert_eq!(contract.goal, "예약 화면을 만든다");
        assert_eq!(contract.scope.len(), 2);
        assert_eq!(contract.scope[0].kind, ScopeKind::File);
        assert_eq!(contract.scope[1].kind, ScopeKind::Dir);
        assert_eq!(contract.exclusions, vec!["결제 흐름은 건드리지 않음".to_string()]);
        assert_eq!(contract.done_criteria.len(), 1);
    }

    #[test]
    fn parse_fails_without_goal_and_on_broken_json() {
        assert!(parse_contract("JSON을 못 만들었어요.", "1").is_none());
        assert!(parse_contract(r#"{ "scope": [] }"#, "1").is_none()); // goal 없음 = 실패
        assert!(parse_contract(r#"{ "goal": "  " }"#, "1").is_none()); // 빈 goal = 실패
    }

    #[test]
    fn parse_drops_scope_entries_with_unknown_kind_or_empty_path() {
        let text = r#"{ "goal": "g", "scope": [
            { "path": "a.ts", "kind": "maybe", "reason": "" },
            { "path": "", "kind": "file", "reason": "" },
            { "path": "b.ts", "kind": "file", "reason": "이유" }
        ] }"#;
        let contract = parse_contract(text, "1").expect("parsed");
        assert_eq!(contract.scope.len(), 1);
        assert_eq!(contract.scope[0].path, "b.ts");
    }

    #[test]
    fn contract_serializes_camel_case() {
        let contract = PlanningContract {
            version: 1,
            extracted_at: "1".to_string(),
            goal: "g".to_string(),
            scope: Vec::new(),
            exclusions: Vec::new(),
            done_criteria: Vec::new(),
        };
        let json = serde_json::to_string(&contract).expect("json");
        assert!(json.contains("extractedAt"));
        assert!(json.contains("doneCriteria"));
    }

    #[test]
    fn project_map_summary_prefers_core_and_reports_truncation() {
        let root = TempDir::new().unwrap();
        std::fs::create_dir_all(root.path().join(".vibelign")).unwrap();
        std::fs::write(
            root.path().join(".vibelign/project_map.json"),
            r#"{ "files": {
                "zz_other.py": { "category": "other" },
                "aa_core.rs": { "category": "core" }
            } }"#,
        )
        .unwrap();
        let (lines, truncated) = project_map_summary(root.path());
        assert_eq!(lines[0], "aa_core.rs (core)"); // core가 other보다 먼저
        assert_eq!(lines.len(), 2);
        assert!(!truncated);
    }

    #[test]
    fn project_map_summary_is_empty_when_map_missing() {
        let root = TempDir::new().unwrap();
        let (lines, truncated) = project_map_summary(root.path());
        assert!(lines.is_empty());
        assert!(!truncated);
    }

    #[test]
    fn validate_scope_keeps_existing_and_drops_hallucinated() {
        let root = TempDir::new().unwrap();
        std::fs::create_dir_all(root.path().join("src/pages")).unwrap();
        std::fs::write(root.path().join("src/pages/Home.tsx"), b"x").unwrap();

        let validated = validate_scope(
            root.path(),
            vec![
                entry("src/pages/Home.tsx", ScopeKind::File),
                entry("src/pages", ScopeKind::Dir),       // 끝 '/' 없음 → 보정
                entry("src/ghost.tsx", ScopeKind::File),   // 실존 안 함 → 버림
                entry("imaginary/", ScopeKind::Dir),       // 실존 안 함 → 버림
                entry("/", ScopeKind::Dir),                // 루트 → 버림
            ],
        );
        let paths: Vec<&str> = validated.iter().map(|e| e.path.as_str()).collect();
        assert_eq!(paths, vec!["src/pages/Home.tsx", "src/pages/"]);
    }
}
// === ANCHOR: PLANNING_CHAT_CONTRACT_END ===
