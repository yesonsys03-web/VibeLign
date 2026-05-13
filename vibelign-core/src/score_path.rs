// === ANCHOR: SCORE_PATH_START ===
//! Pure-function port of `_meaningful_overlap` — probe slice for the score_path
//! Rust port track. See `docs/superpowers/plans/2026-05-13-score-path-rust-port-plan.md`
//! Session 1.
//!
//! Python source-of-truth: `vibelign/core/patch_suggester.py::_meaningful_overlap`.
//! Order-preserving intersection with request-side dedup.

use std::collections::HashSet;

/// Port of Python `_meaningful_overlap`:
/// `list(dict.fromkeys(token for token in request_tokens if token in set(candidate_tokens)))`.
pub fn meaningful_overlap(request_tokens: &[String], candidate_tokens: &[String]) -> Vec<String> {
    let candidate_set: HashSet<&str> = candidate_tokens.iter().map(String::as_str).collect();
    let mut seen: HashSet<&str> = HashSet::new();
    let mut matches: Vec<String> = Vec::new();
    for token in request_tokens {
        if candidate_set.contains(token.as_str()) && seen.insert(token.as_str()) {
            matches.push(token.clone());
        }
    }
    matches
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| (*s).to_string()).collect()
    }

    #[test]
    fn intersection_in_request_order() {
        let req = s(&["로그인", "button", "버튼", "submit"]);
        let cand = s(&["로그인", "submit", "screen", "버튼"]);
        assert_eq!(
            meaningful_overlap(&req, &cand),
            s(&["로그인", "버튼", "submit"])
        );
    }

    #[test]
    fn dedup_request_tokens() {
        let req = s(&["a", "b", "a", "b"]);
        let cand = s(&["a", "b"]);
        assert_eq!(meaningful_overlap(&req, &cand), s(&["a", "b"]));
    }

    #[test]
    fn no_overlap() {
        let req = s(&["x", "y"]);
        let cand = s(&["a", "b"]);
        assert!(meaningful_overlap(&req, &cand).is_empty());
    }

    #[test]
    fn empty_inputs() {
        assert!(meaningful_overlap(&[], &s(&["x"])).is_empty());
        assert!(meaningful_overlap(&s(&["x"]), &[]).is_empty());
    }

    #[test]
    fn request_token_not_in_candidate_skipped() {
        let req = s(&["a", "b", "c"]);
        let cand = s(&["a", "c"]);
        assert_eq!(meaningful_overlap(&req, &cand), s(&["a", "c"]));
    }
}
// === ANCHOR: SCORE_PATH_END ===
