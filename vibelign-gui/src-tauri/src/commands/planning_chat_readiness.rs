// === ANCHOR: PLANNING_CHAT_READINESS_START ===
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Verdict {
    Green,
    Red,
    Na,
}

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub(crate) enum ReadinessStatus {
    Judged,
    Unavailable,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ReadinessCheck {
    pub(crate) verdict: Verdict,
    pub(crate) note: String,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ReadinessChecks {
    pub(crate) trigger: ReadinessCheck,
    pub(crate) data: ReadinessCheck,
    pub(crate) logic: ReadinessCheck,
    pub(crate) acceptance: ReadinessCheck,
    pub(crate) edge: ReadinessCheck,
    pub(crate) platform: ReadinessCheck,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RequirementReadiness {
    pub(crate) title: String,
    pub(crate) summary: String,
    pub(crate) core: bool,
    pub(crate) checks: ReadinessChecks,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ReadinessReport {
    pub(crate) status: ReadinessStatus,
    pub(crate) requirements: Vec<RequirementReadiness>,
}

impl ReadinessReport {
    pub(crate) fn unavailable() -> Self {
        ReadinessReport {
            status: ReadinessStatus::Unavailable,
            requirements: Vec::new(),
        }
    }
}

/// "green" | "na"/"n/a" → 해당 verdict, 그 외/누락 → Red(불확실하면 통과시키지 않는다).
fn normalize_verdict(raw: Option<&str>) -> Verdict {
    match raw.map(|value| value.trim().to_lowercase()) {
        Some(ref value) if value == "green" => Verdict::Green,
        Some(ref value) if value == "na" || value == "n/a" => Verdict::Na,
        _ => Verdict::Red,
    }
}

/// 텍스트에서 첫 '{' ~ 마지막 '}' 구간을 JSON 후보로 추출(코드펜스 무시).
fn extract_json(text: &str) -> Option<&str> {
    let start = text.find('{')?;
    let end = text.rfind('}')?;
    if end > start {
        Some(&text[start..=end])
    } else {
        None
    }
}

fn check_from_value(checks: &serde_json::Value, key: &str) -> ReadinessCheck {
    let entry = checks.get(key);
    let verdict = normalize_verdict(entry.and_then(|value| value.get("verdict")).and_then(|v| v.as_str()));
    let note = entry
        .and_then(|value| value.get("note"))
        .and_then(|v| v.as_str())
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| if matches!(verdict, Verdict::Red) { "미정".to_string() } else { String::new() });
    ReadinessCheck { verdict, note }
}

pub(crate) fn parse_readiness_report(text: &str) -> ReadinessReport {
    let Some(json) = extract_json(text) else {
        return ReadinessReport::unavailable();
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(json) else {
        return ReadinessReport::unavailable();
    };
    let Some(items) = value.get("requirements").and_then(|v| v.as_array()) else {
        return ReadinessReport::unavailable();
    };
    let requirements = items
        .iter()
        .map(|item| {
            let checks = item.get("checks").cloned().unwrap_or(serde_json::Value::Null);
            RequirementReadiness {
                title: item.get("title").and_then(|v| v.as_str()).unwrap_or("").trim().to_string(),
                summary: item.get("summary").and_then(|v| v.as_str()).unwrap_or("").trim().to_string(),
                core: item.get("core").and_then(|v| v.as_bool()).unwrap_or(false),
                checks: ReadinessChecks {
                    trigger: check_from_value(&checks, "trigger"),
                    data: check_from_value(&checks, "data"),
                    logic: check_from_value(&checks, "logic"),
                    acceptance: check_from_value(&checks, "acceptance"),
                    edge: check_from_value(&checks, "edge"),
                    platform: check_from_value(&checks, "platform"),
                },
            }
        })
        .collect::<Vec<_>>();
    ReadinessReport {
        status: ReadinessStatus::Judged,
        requirements,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_verdict_maps_known_values() {
        assert_eq!(normalize_verdict(Some("green")), Verdict::Green);
        assert_eq!(normalize_verdict(Some(" NA ")), Verdict::Na);
        assert_eq!(normalize_verdict(Some("n/a")), Verdict::Na);
    }

    #[test]
    fn normalize_verdict_downgrades_unknown_and_missing_to_red() {
        assert_eq!(normalize_verdict(Some("maybe")), Verdict::Red);
        assert_eq!(normalize_verdict(None), Verdict::Red);
    }

    #[test]
    fn parse_extracts_report_from_fenced_json() {
        let text = r#"여기 결과입니다:
```json
{
  "requirements": [
    {
      "title": "카드 발동",
      "summary": "결정이 생기면 카드가 뜬다",
      "core": true,
      "checks": {
        "trigger": { "verdict": "red", "note": "감지 방법 미정" },
        "data": { "verdict": "red", "note": "저장 위치 미정" },
        "logic": { "verdict": "red", "note": "분류 방법 미정" },
        "acceptance": { "verdict": "green", "note": "" },
        "edge": { "verdict": "green", "note": "" },
        "platform": { "verdict": "na", "note": "단일 타깃" }
      }
    }
  ]
}
```
끝."#;
        let report = parse_readiness_report(text);
        assert!(matches!(report.status, ReadinessStatus::Judged));
        assert_eq!(report.requirements.len(), 1);
        let req = &report.requirements[0];
        assert_eq!(req.title, "카드 발동");
        assert!(req.core);
        assert_eq!(req.checks.trigger.verdict, Verdict::Red);
        assert_eq!(req.checks.acceptance.verdict, Verdict::Green);
        assert_eq!(req.checks.platform.verdict, Verdict::Na);
    }

    #[test]
    fn parse_downgrades_missing_check_to_red() {
        let text = r#"{ "requirements": [
          { "title": "t", "summary": "s", "core": false,
            "checks": { "trigger": { "verdict": "green" } } } ] }"#;
        let report = parse_readiness_report(text);
        assert!(matches!(report.status, ReadinessStatus::Judged));
        let checks = &report.requirements[0].checks;
        assert_eq!(checks.trigger.verdict, Verdict::Green);
        assert_eq!(checks.data.verdict, Verdict::Red); // 누락 → red
        assert_eq!(checks.data.note, "미정");
    }

    #[test]
    fn parse_returns_unavailable_on_broken_json() {
        let report = parse_readiness_report("죄송합니다, JSON을 못 만들었어요.");
        assert!(matches!(report.status, ReadinessStatus::Unavailable));
        assert!(report.requirements.is_empty());
    }
}
// === ANCHOR: PLANNING_CHAT_READINESS_END ===
