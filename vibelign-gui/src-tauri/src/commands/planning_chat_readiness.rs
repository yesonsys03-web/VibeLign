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
}
// === ANCHOR: PLANNING_CHAT_READINESS_END ===
