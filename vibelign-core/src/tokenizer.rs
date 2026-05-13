// === ANCHOR: TOKENIZER_START ===
//! Pure-function port of `vibelign.core.patch_suggester` 의 6 토큰 leaf 함수.
//!
//! Python is the source of truth — see `tests/fixtures/tokenizer_goldens/*.expected.json`.
//! 본 모듈은 한 입력에 대해 동일한 출력을 byte-equal 로 보장해야 한다 (612 fixture
//! record × 6 함수). Orchestration (`_score_all_files`, `score_path`) 은 그대로
//! Python 에 유지하고 leaf 만 Rust 로 이전.
//!
//! Bottleneck (cProfile 2026-05-13): `vib recover --preview --json` warm 4.7s 의
//! 86% 가 한국어 토큰 분해/정규화 hot loop 에서 소비됨 (`_normalize_korean_token`
//! 609k 호출, `_decompose_korean_compound` 705k 호출). leaf 이전으로 ~90% 시간을
//! 회수하는 것이 목표.
//!
//! Alias 테이블 동기화 책임: `vibelign/core/patch_suggester.py` 의
//! `_TOKEN_ALIASES` / `_KOREAN_ALIAS_KEYS` / `_KOREAN_PARTICLE_SUFFIXES` 변경 시
//! (1) `_regenerate.py` 재실행으로 fixture 갱신, (2) 본 모듈 const 동기화 → cargo
//! test parity 가 자동 보장. plan §7 R2 의 build-time codegen 은 향후 작업.

use regex::Regex;
use std::collections::HashSet;
use std::sync::OnceLock;

// --- ANCHOR: TOKENIZER_DATA_START ---

/// `_TOKEN_ALIASES` 의 Python insertion order 그대로. `expand_token` 의 alias
/// lookup 과 `KOREAN_ALIAS_KEYS` 의 stable sort 결과 모두 이 순서에 의존.
const TOKEN_ALIASES: &[(&str, &[&str])] = &[
    ("홈", &["home"]),
    ("홈화면", &["home", "screen", "page"]),
    ("메인화면", &["main", "home", "screen", "page"]),
    ("화면", &["screen", "page"]),
    ("메뉴", &["menu", "nav", "navigation"]),
    ("첫화면", &["onboarding", "screen"]),
    ("시작화면", &["onboarding", "screen"]),
    ("버전", &["version"]),
    ("설정", &["settings", "config"]),
    ("설치", &["install"]),
    ("안내", &["guide"]),
    ("가이드", &["guide"]),
    ("클로드", &["claude"]),
    ("훅", &["hook"]),
    ("상태", &["state", "status"]),
    ("유지", &["persist", "state"]),
    ("활성화", &["enable", "enabled"]),
    ("비활성화", &["disable", "disabled"]),
    ("프로필", &["profile"]),
    ("로그인", &["login"]),
    ("이메일", &["email"]),
    ("비밀번호", &["password"]),
    ("서버", &["server", "app"]),
    ("포트", &["port"]),
    ("사용자", &["user", "users"]),
    ("회원가입", &["signup", "register"]),
    ("조회", &["get", "query"]),
    ("검증", &["validate", "validators"]),
    ("유효성", &["validate", "validators"]),
    ("토큰", &["token", "auth"]),
    ("발급", &["generate", "issue", "token"]),
    ("저장", &["save", "store", "update"]),
    ("평문", &["hash", "encrypt", "plaintext"]),
    ("해시", &["hash", "encrypt"]),
    ("중복", &["duplicate", "create", "unique"]),
    ("캐시", &["cache", "database"]),
    ("느려", &["performance", "optimize"]),
];

/// Python `sorted(korean_keys, key=len, reverse=True)` 결과 — stable sort 라 동일
/// char-length 내부 순서는 `TOKEN_ALIASES` insertion order 그대로. `decompose_
/// korean_compound` 의 greedy prefix match 결정성이 이 정렬에 의존.
const KOREAN_ALIAS_KEYS: &[&str] = &[
    // len 4
    "메인화면", "시작화면", "비활성화", "비밀번호", "회원가입",
    // len 3
    "홈화면", "첫화면", "가이드", "클로드", "활성화",
    "프로필", "로그인", "이메일", "사용자", "유효성",
    // len 2
    "화면", "메뉴", "버전", "설정", "설치",
    "안내", "상태", "유지", "서버", "포트",
    "조회", "검증", "토큰", "발급", "저장",
    "평문", "해시", "중복", "캐시", "느려",
    // len 1
    "홈", "훅",
];

/// `_KOREAN_PARTICLE_SUFFIXES` — char-length desc, lexicographic ASC tie-break.
/// `normalize_korean_token` 의 첫 매칭 break 패턴 상 같은 char-length 끼리는
/// collision 이 발생하지 않으므로 (각 suffix 가 고유 ending) 순서 변동에 둔감하지만,
/// 결정성 보장을 위해 explicit sort.
const KOREAN_PARTICLE_SUFFIXES_SORTED: &[&str] = &[
    // len 3
    "입니다",
    // len 2
    "과는", "과의", "까지", "께서", "라고", "라서", "보다", "부터",
    "에게", "에는", "에서", "였다", "와는", "와의", "으로", "이고",
    "이다", "이라", "이며", "처럼", "하고", "하며", "하면", "한테", "했다",
    // len 1
    "가", "과", "는", "도", "로", "를", "만", "에", "와", "은", "을", "의", "이",
];

// --- ANCHOR: TOKENIZER_DATA_END ---

fn token_split_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"[a-zA-Z0-9_]+|[가-힣]+").expect("static regex"))
}

fn identifier_split_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"[a-z]+|[0-9]+|[가-힣]+").expect("static regex"))
}

fn find_alias(token: &str) -> Option<&'static [&'static str]> {
    TOKEN_ALIASES
        .iter()
        .find_map(|(k, v)| if *k == token { Some(*v) } else { None })
}

fn is_all_hangul(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| ('가'..='힣').contains(&c))
}

/// Port of Python `_decompose_korean_compound`.
pub fn decompose_korean_compound(token: &str) -> Vec<String> {
    if !is_all_hangul(token) {
        return Vec::new();
    }
    if find_alias(token).is_some() {
        return Vec::new();
    }
    let mut parts: Vec<String> = Vec::new();
    let bytes_len = token.len();
    let mut i = 0;
    while i < bytes_len {
        let remaining = &token[i..];
        let mut matched: Option<&str> = None;
        for &key in KOREAN_ALIAS_KEYS {
            if remaining.starts_with(key) {
                matched = Some(key);
                break;
            }
        }
        match matched {
            None => return Vec::new(),
            Some(key) => {
                parts.push(key.to_string());
                i += key.len();
            }
        }
    }
    if parts.len() >= 2 {
        parts
    } else {
        Vec::new()
    }
}

/// Port of Python `_split_identifier_parts`.
pub fn split_identifier_parts(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    identifier_split_regex()
        .find_iter(&lower)
        .map(|m| m.as_str().to_string())
        .collect()
}

/// Port of Python `_normalize_korean_token`. char-length 비교 (Rust `chars().
/// count()`) 가 Python `len(str)` 과 일치.
pub fn normalize_korean_token(token: &str) -> Vec<String> {
    let mut values = vec![token.to_string()];
    let token_char_len = token.chars().count();
    for &suffix in KOREAN_PARTICLE_SUFFIXES_SORTED {
        let suffix_char_len = suffix.chars().count();
        if token_char_len > suffix_char_len + 1 && token.ends_with(suffix) {
            let trim_bytes = suffix.len();
            values.push(token[..token.len() - trim_bytes].to_string());
            break;
        }
    }
    values
}

/// Port of Python `_expand_token`. Order-preserving dedup, empty filter.
pub fn expand_token(token: &str) -> Vec<String> {
    let mut expanded: Vec<String> = Vec::new();
    for candidate in normalize_korean_token(token) {
        expanded.push(candidate.clone());
        expanded.extend(split_identifier_parts(&candidate));
        if let Some(aliases) = find_alias(&candidate) {
            expanded.extend(aliases.iter().map(|s| s.to_string()));
        }
        for part in decompose_korean_compound(&candidate) {
            expanded.push(part.clone());
            if let Some(aliases) = find_alias(&part) {
                expanded.extend(aliases.iter().map(|s| s.to_string()));
            }
        }
    }
    let mut seen: HashSet<String> = HashSet::new();
    let mut result: Vec<String> = Vec::new();
    for item in expanded {
        if !item.is_empty() && seen.insert(item.clone()) {
            result.push(item);
        }
    }
    result
}

/// Port of Python `tokenize`.
pub fn tokenize(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let raw_tokens: Vec<String> = token_split_regex()
        .find_iter(&lower)
        .map(|m| m.as_str().to_string())
        .collect();
    let mut tokens: Vec<String> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for raw in raw_tokens {
        for token in expand_token(&raw) {
            if seen.insert(token.clone()) {
                tokens.push(token);
            }
        }
    }
    tokens
}

/// Port of Python `_intent_tokens`. Python 측이 `set` 반환이고 fixture 의
/// `expected` 는 sorted list 이므로 Rust 도 sorted Vec 반환하여 byte-equal.
pub fn intent_tokens(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let mut tokens: HashSet<String> = HashSet::new();
    for raw in token_split_regex().find_iter(&lower) {
        for token in expand_token(raw.as_str()) {
            tokens.insert(token);
        }
    }
    let mut result: Vec<String> = tokens.into_iter().collect();
    result.sort();
    result
}

// --- ANCHOR: TOKENIZER_TESTS_START ---
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;
    use std::path::PathBuf;

    fn fixtures_dir() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("workspace root")
            .join("tests/fixtures/tokenizer_goldens")
    }

    fn load_cases(name: &str) -> Vec<(String, String, Vec<String>)> {
        let path = fixtures_dir().join(format!("{name}.expected.json"));
        let text = std::fs::read_to_string(&path)
            .unwrap_or_else(|_| panic!("read fixture: {}", path.display()));
        let json: Value = serde_json::from_str(&text).expect("fixture is valid json");
        json["cases"]
            .as_array()
            .expect("cases array")
            .iter()
            .map(|c| {
                let desc = c["description"].as_str().expect("description").to_string();
                let input = c["input"].as_str().expect("input").to_string();
                let expected: Vec<String> = c["expected"]
                    .as_array()
                    .unwrap_or_else(|| panic!("expected array for {desc}"))
                    .iter()
                    .map(|v| v.as_str().expect("expected str").to_string())
                    .collect();
                (desc, input, expected)
            })
            .collect()
    }

    fn assert_parity<F>(name: &str, func: F)
    where
        F: Fn(&str) -> Vec<String>,
    {
        let cases = load_cases(name);
        assert_eq!(cases.len(), 102, "{name}: case count");
        for (desc, input, expected) in cases {
            let actual = func(&input);
            assert_eq!(
                actual, expected,
                "function={name} case={desc} input={input:?}"
            );
        }
    }

    #[test]
    fn parity_decompose_korean_compound() {
        assert_parity("_decompose_korean_compound", decompose_korean_compound);
    }

    #[test]
    fn parity_split_identifier_parts() {
        assert_parity("_split_identifier_parts", split_identifier_parts);
    }

    #[test]
    fn parity_normalize_korean_token() {
        assert_parity("_normalize_korean_token", normalize_korean_token);
    }

    #[test]
    fn parity_expand_token() {
        assert_parity("_expand_token", expand_token);
    }

    #[test]
    fn parity_tokenize() {
        assert_parity("tokenize", tokenize);
    }

    #[test]
    fn parity_intent_tokens() {
        assert_parity("_intent_tokens", intent_tokens);
    }
}
// --- ANCHOR: TOKENIZER_TESTS_END ---
// === ANCHOR: TOKENIZER_END ===
