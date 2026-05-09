// === ANCHOR: SECRET_SCAN_START ===
//! Pure-function port of Python `vibelign.core.secret_scan.scan_unified_diff_for_secrets`.
//!
//! Python is the source of truth — see `tests/fixtures/secret_scan_diffs/*.expected.json`.
//! Git invocation and file walking stay in Python; this module only does regex matching
//! on a single (diff_text, path_hint) pair, which is the CPU-hot work.

use regex::Regex;
use serde::Serialize;
use std::sync::OnceLock;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct SecretFinding {
    pub path: String,
    pub rule_id: String,
    pub line_number: Option<u32>,
    pub snippet: String,
}

const ALLOW_MARKER: &str = "vibelign: allow-secret";

const PLACEHOLDER_VALUES: &[&str] = &[
    "ENV",
    "YOUR_API_KEY",
    "YOUR_KEY",
    "YOUR_TOKEN",
    "YOUR_SECRET",
    "EXAMPLE",
    "CHANGE_ME",
    "CHANGEME",
    "CHANGE-ME",
    "REPLACE_ME",
    "REPLACE_WITH_REAL_VALUE",
];

struct HighConfidenceRule {
    rule_id: &'static str,
    pattern: &'static str,
}

const HIGH_CONFIDENCE_RULES: &[HighConfidenceRule] = &[
    HighConfidenceRule { rule_id: "private-key", pattern: r"-----BEGIN [A-Z ]*PRIVATE KEY-----" },
    HighConfidenceRule {
        rule_id: "github-token",
        pattern: r"\b(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b",
    },
    HighConfidenceRule { rule_id: "slack-token", pattern: r"\bxox(?:a|b|p|r|s)-[A-Za-z0-9-]{10,}\b" },
    HighConfidenceRule { rule_id: "stripe-live-key", pattern: r"\bsk_live_[A-Za-z0-9]{16,}\b" },
    HighConfidenceRule { rule_id: "aws-access-key", pattern: r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b" },
    HighConfidenceRule { rule_id: "gemini-api-key", pattern: r"\bAIzaSy[A-Za-z0-9_-]{33}\b" },
    HighConfidenceRule { rule_id: "anthropic-api-key", pattern: r"\bsk-ant-[A-Za-z0-9_-]{40,}\b" },
    HighConfidenceRule { rule_id: "openai-api-key", pattern: r"\bsk-[A-Za-z0-9]{32,}\b" },
    HighConfidenceRule { rule_id: "url-inline-key", pattern: r"[?&]key=[A-Za-z0-9_-]{16,}" },
    HighConfidenceRule {
        rule_id: "jwt-token",
        pattern: r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
    },
    HighConfidenceRule {
        rule_id: "db-url-with-password",
        pattern: r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|amqps)://[^:/\s\x22']+:[^@\s\x22']+@[^\s\x22']+",
    },
    HighConfidenceRule { rule_id: "gcp-service-account", pattern: r#""type"\s*:\s*"service_account""# },
];

const KEYWORD_VALUE_PATTERN: &str =
    r"(?i)(api[_-]?key|token|secret|password|passwd|client_secret|access_key)\s*[:=]\s*[\x22']?([A-Za-z0-9_./+=:@\-]{16,})[\x22']?";

const HUNK_HEADER_PLUS_PATTERN: &str = r"\+(\d+)";

fn high_confidence_regexes() -> &'static [(&'static str, Regex)] {
    static CACHE: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    CACHE.get_or_init(|| {
        HIGH_CONFIDENCE_RULES
            .iter()
            .map(|rule| (rule.rule_id, Regex::new(rule.pattern).expect("static high-confidence rule must compile")))
            .collect()
    })
}

fn keyword_regex() -> &'static Regex {
    static CACHE: OnceLock<Regex> = OnceLock::new();
    CACHE.get_or_init(|| Regex::new(KEYWORD_VALUE_PATTERN).expect("static keyword pattern must compile"))
}

fn hunk_plus_regex() -> &'static Regex {
    static CACHE: OnceLock<Regex> = OnceLock::new();
    CACHE.get_or_init(|| Regex::new(HUNK_HEADER_PLUS_PATTERN).expect("static hunk header pattern must compile"))
}

fn is_placeholder(value: &str) -> bool {
    let trimmed = value.trim().trim_matches(|character| character == '"' || character == '\'');
    let normalized = trimmed.to_uppercase();
    if PLACEHOLDER_VALUES.iter().any(|placeholder| placeholder == &normalized.as_str()) {
        return true;
    }
    normalized.starts_with("YOUR_")
}

fn redact(text: &str) -> String {
    let compact: String = text.split_whitespace().collect::<Vec<_>>().join(" ");
    if compact.chars().count() <= 4 {
        return "[redacted]".to_string();
    }
    let tail: String = compact.chars().rev().take(4).collect::<String>().chars().rev().collect();
    format!("...{tail}")
}

fn extract_added_line(line: &str) -> Option<&str> {
    if !line.starts_with('+') || line.starts_with("+++") {
        return None;
    }
    Some(&line[1..])
}

pub fn scan_unified_diff(diff_text: &str, path_hint: &str) -> Vec<SecretFinding> {
    let mut findings: Vec<SecretFinding> = Vec::new();
    let mut current_line_number: Option<u32> = None;

    for raw_line in diff_text.split('\n') {
        let line = raw_line.strip_suffix('\r').unwrap_or(raw_line);

        if line.starts_with("@@") {
            current_line_number = hunk_plus_regex()
                .captures(line)
                .and_then(|captures| captures.get(1))
                .and_then(|matched| matched.as_str().parse::<u32>().ok());
            continue;
        }

        let added_line = match extract_added_line(line) {
            Some(content) => content,
            None => {
                if line.starts_with('-') || line.starts_with("diff --git") {
                    continue;
                }
                if let Some(counter) = current_line_number.as_mut() {
                    if !line.starts_with('\\') {
                        *counter = counter.saturating_add(1);
                    }
                }
                continue;
            }
        };

        let line_number_for_finding = current_line_number;
        if let Some(counter) = current_line_number.as_mut() {
            *counter = counter.saturating_add(1);
        }

        if added_line.contains(ALLOW_MARKER) {
            continue;
        }

        let mut matched_high_confidence = false;
        for (rule_id, pattern) in high_confidence_regexes() {
            if let Some(matched) = pattern.find(added_line) {
                matched_high_confidence = true;
                findings.push(SecretFinding {
                    path: path_hint.to_string(),
                    rule_id: (*rule_id).to_string(),
                    line_number: line_number_for_finding,
                    snippet: redact(matched.as_str()),
                });
            }
        }

        if matched_high_confidence {
            continue;
        }

        let Some(keyword_match) = keyword_regex().captures(added_line) else {
            continue;
        };
        let Some(value_group) = keyword_match.get(2) else {
            continue;
        };
        let value = value_group.as_str();
        if is_placeholder(value) {
            continue;
        }
        findings.push(SecretFinding {
            path: path_hint.to_string(),
            rule_id: "generic-secret".to_string(),
            line_number: line_number_for_finding,
            snippet: redact(value),
        });
    }

    findings
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn fixtures_dir() -> PathBuf {
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        manifest.parent().expect("workspace root").join("tests/fixtures/secret_scan_diffs")
    }

    fn path_hint_from_golden(diff_name: &str) -> String {
        let dir = fixtures_dir();
        let expected_name = format!("{}.expected.json", diff_name.trim_end_matches(".diff"));
        let expected_text = std::fs::read_to_string(dir.join(&expected_name)).expect("fixture .expected.json exists");
        let expected: serde_json::Value = serde_json::from_str(&expected_text).expect("valid expected json");
        expected["path_hint"].as_str().expect("path_hint string").to_string()
    }

    fn run_fixture(diff_name: &str) -> Vec<SecretFinding> {
        let dir = fixtures_dir();
        let diff_text = std::fs::read_to_string(dir.join(diff_name)).expect("fixture .diff exists");
        scan_unified_diff(&diff_text, &path_hint_from_golden(diff_name))
    }

    fn expected_findings(diff_name: &str) -> Vec<SecretFinding> {
        let dir = fixtures_dir();
        let expected_name = format!("{}.expected.json", diff_name.trim_end_matches(".diff"));
        let expected_text = std::fs::read_to_string(dir.join(&expected_name)).expect("fixture .expected.json exists");
        let expected: serde_json::Value = serde_json::from_str(&expected_text).expect("valid expected json");
        let findings = expected["findings"].as_array().expect("findings array").clone();
        findings
            .into_iter()
            .map(|item| SecretFinding {
                path: item["path"].as_str().unwrap_or_default().to_string(),
                rule_id: item["rule_id"].as_str().unwrap_or_default().to_string(),
                line_number: item["line_number"].as_u64().map(|number| number as u32),
                snippet: item["snippet"].as_str().unwrap_or_default().to_string(),
            })
            .collect()
    }

    fn assert_parity(diff_name: &str) {
        let actual = run_fixture(diff_name);
        let expected = expected_findings(diff_name);
        assert_eq!(actual, expected, "fixture {} parity mismatch", diff_name);
    }

    #[test]
    fn empty_diff_yields_no_findings() {
        assert_parity("01_empty.diff");
    }

    #[test]
    fn high_confidence_aws_rule_fires() {
        assert_parity("02_high_confidence_aws.diff");
    }

    #[test]
    fn high_confidence_combo_emits_one_finding_per_rule() {
        assert_parity("03_high_confidence_combo.diff");
    }

    #[test]
    fn keyword_rule_skips_placeholder() {
        assert_parity("04_keyword_with_placeholder.diff");
    }

    #[test]
    fn allow_marker_suppresses_findings_on_that_line() {
        assert_parity("05_allow_marker.diff");
    }

    #[test]
    fn line_numbers_track_across_hunks() {
        assert_parity("06_line_number_tracking.diff");
    }

    #[test]
    fn removed_line_does_not_emit_finding() {
        assert_parity("07_removed_line_ignored.diff");
    }

    #[test]
    fn no_newline_marker_does_not_increment_line_counter() {
        assert_parity("08_no_newline_marker.diff");
    }

    #[test]
    fn high_confidence_wins_over_keyword_on_same_line() {
        assert_parity("09_high_confidence_wins.diff");
    }

    #[test]
    fn unicode_path_and_body_round_trip_intact() {
        assert_parity("10_unicode_path_and_body.diff");
    }
}
// === ANCHOR: SECRET_SCAN_END ===
