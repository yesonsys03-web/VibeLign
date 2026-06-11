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

#[cfg(test)]
mod tests {
    use super::*;

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
}
// === ANCHOR: PLANNING_CHAT_CONTRACT_END ===
