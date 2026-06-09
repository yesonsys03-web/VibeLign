// === ANCHOR: PLANNING_PERSONA_START ===
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use super::platform::{augmented_vib_path, hide_console};

pub(crate) const INTERNAL_PROVIDER_PRIORITY: &[&str] = &["claude", "codex", "agy", "opencode"];

/// 페르소나 CLI 한 번 호출의 상한. 초과하면 자식을 죽이고 timeout 으로 처리한다.
const PERSONA_TIMEOUT_SECS: u64 = 120;

/// CLI 실행을 timeout 상한으로 감싼다. stdout/stderr 는 별도 스레드로 비워 파이프
/// 교착을 막고, 상한을 넘기면 자식 프로세스를 죽인 뒤 Ok(None)(=timeout)을 돌려준다.
fn output_with_timeout(
    mut cmd: Command,
    timeout: Duration,
) -> std::io::Result<Option<std::process::Output>> {
    use std::io::Read;
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    let mut child = cmd.spawn()?;
    let mut stdout = child.stdout.take();
    let mut stderr = child.stderr.take();
    let out_handle = std::thread::spawn(move || {
        let mut buf = Vec::new();
        if let Some(s) = stdout.as_mut() {
            let _ = s.read_to_end(&mut buf);
        }
        buf
    });
    let err_handle = std::thread::spawn(move || {
        let mut buf = Vec::new();
        if let Some(s) = stderr.as_mut() {
            let _ = s.read_to_end(&mut buf);
        }
        buf
    });
    let deadline = Instant::now() + timeout;
    loop {
        if let Some(status) = child.try_wait()? {
            let stdout = out_handle.join().unwrap_or_default();
            let stderr = err_handle.join().unwrap_or_default();
            return Ok(Some(std::process::Output { status, stdout, stderr }));
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            // 리더 스레드를 join 하지 않는다: Windows 의 .cmd/.bat 셔임은 cmd.exe 를 죽여도
            // 손자 프로세스(node 등)가 파이프 쓰기단을 쥐고 있어 read_to_end 가 EOF 를 못 받고
            // join 이 영원히 막힐 수 있다. timeout 시 출력은 어차피 버리므로 스레드를 분리한다.
            drop(out_handle);
            drop(err_handle);
            return Ok(None);
        }
        std::thread::sleep(Duration::from_millis(50));
    }
}

fn provider_try_order(preferred: &str) -> Vec<String> {
    let mut order: Vec<String> = Vec::new();
    if !preferred.is_empty() {
        order.push(preferred.to_string());
    }
    for provider in INTERNAL_PROVIDER_PRIORITY {
        if !order.iter().any(|p| p == provider) {
            order.push((*provider).to_string());
        }
    }
    order
}

fn persona_enabled_from_value(config: &serde_json::Value, persona_id: &str) -> bool {
    config
        .get("planning_personas")
        .and_then(|s| s.get("personas"))
        .and_then(|p| p.get(persona_id))
        .and_then(|e| e.get("enabled"))
        .and_then(|v| v.as_bool())
        .unwrap_or(true)
}

/// 전역 설정에서 해당 페르소나가 활성인지. 부재 시 true.
pub(crate) fn is_persona_enabled(persona_id: &str) -> bool {
    persona_enabled_from_value(&read_gui_config_value(), persona_id)
}

/// 전역 gui_config.json 을 읽는다. 부재/손상 시 빈 객체.
fn read_gui_config_value() -> serde_json::Value {
    let Some(home) = std::env::var_os("HOME").or_else(|| std::env::var_os("USERPROFILE")) else {
        return serde_json::json!({});
    };
    let path = std::path::PathBuf::from(home).join(".vibelign").join("gui_config.json");
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_else(|| serde_json::json!({}))
}

/// persona 의 기본 provider 로 시도 목록을 만든다.
fn resolve_provider_order(_persona_id: &str, spec: &PersonaSpec) -> Vec<String> {
    provider_try_order(spec.default_provider)
}

/// 실패 출력에서 로그인 문제를 감지. 아니면 "error".
fn classify_failure(stdout: &str, stderr: &str) -> String {
    let combined = format!("{stdout}\n{stderr}").to_lowercase();
    const LOGIN_PATTERNS: &[&str] = &[
        "not logged in", "not signed in", "please login", "please log in",
        "log out and sign in", "sign in again", "login required",
        "authentication required", "auth required", "unauthorized",
        "token_expired", "token expired", "401",
    ];
    if LOGIN_PATTERNS.iter().any(|p| combined.contains(p)) {
        "not_logged_in".to_string()
    } else {
        "error".to_string()
    }
}

pub(crate) struct PersonaRun {
    pub(crate) content: String,
    pub(crate) status: String,
    pub(crate) provider_used: Option<String>,
    pub(crate) fallback_reason: Option<String>,
}

/// 실제 응답한 provider 가 preferred 와 다르면 Some(used), 같으면 None.
fn fallback_provider_used(preferred: &str, used: &str) -> Option<String> {
    if used == preferred {
        None
    } else {
        Some(used.to_string())
    }
}

pub(crate) struct PlanningChatLine<'a> {
    pub(crate) role: &'a str,
    pub(crate) persona_id: Option<&'a str>,
    pub(crate) content: &'a str,
}

#[derive(Clone, Copy)]
struct PersonaSpec {
    name: &'static str,
    default_provider: &'static str,
    default_role: &'static str,
}

pub(crate) fn run_persona_response(
    project_dir: &Path,
    persona_id: &str,
    lines: &[PlanningChatLine<'_>],
) -> PersonaRun {
    let Some(spec) = persona_spec(persona_id) else {
        return PersonaRun {
            content: "선택한 페르소나를 찾지 못했어요.".to_string(),
            status: "failed".to_string(),
            provider_used: None,
            fallback_reason: None,
        };
    };
    let role = resolve_role(persona_id, &spec);
    let capability_map = build_capability_map(project_dir);
    let prompt = build_persona_prompt(spec, role, lines, capability_map.as_deref());
    let order = resolve_provider_order(persona_id, &spec);
    let preferred = order.first().cloned().unwrap_or_default();
    let mut preferred_reason: Option<String> = None;
    for provider in order {
        let is_preferred = provider == preferred;
        let Some((executable_name, args)) = provider_spec(&provider) else {
            if is_preferred { preferred_reason = Some("not_installed".to_string()); }
            continue;
        };
        let Some(executable) = find_executable(executable_name) else {
            if is_preferred { preferred_reason = Some("not_installed".to_string()); }
            continue;
        };
        let mut cmd = Command::new(executable);
        cmd.args(args);
        cmd.arg(&prompt);
        cmd.current_dir(project_dir);
        cmd.stdin(Stdio::null());
        cmd.env("PATH", augmented_vib_path());
        cmd.env("NO_COLOR", "1");
        hide_console(&mut cmd);
        match output_with_timeout(cmd, Duration::from_secs(PERSONA_TIMEOUT_SECS)) {
            Ok(Some(output)) if output.status.success() => {
                let content = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !content.is_empty() {
                    return PersonaRun {
                        content,
                        status: "ok".to_string(),
                        provider_used: fallback_provider_used(&preferred, &provider),
                        fallback_reason: if is_preferred { None } else { preferred_reason.clone() },
                    };
                }
                if is_preferred { preferred_reason = Some("error".to_string()); }
            }
            Ok(Some(output)) => {
                if is_preferred {
                    let stdout = String::from_utf8_lossy(&output.stdout);
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    preferred_reason = Some(classify_failure(&stdout, &stderr));
                }
            }
            Ok(None) => {
                // 상한 초과: 자식은 이미 종료시켰다. 다음 provider 로 폴백한다.
                if is_preferred { preferred_reason = Some("timeout".to_string()); }
            }
            Err(_) => {
                if is_preferred { preferred_reason = Some("error".to_string()); }
            }
        }
    }
    PersonaRun {
        content: "AI 응답을 가져오지 못했어요. 설치된 AI가 없거나 로그인이 필요할 수 있어요.".to_string(),
        status: "failed".to_string(),
        provider_used: None,
        fallback_reason: preferred_reason,
    }
}

fn persona_spec(persona_id: &str) -> Option<PersonaSpec> {
    match persona_id {
        "chloe" => Some(PersonaSpec {
            name: "클로이",
            default_provider: "claude",
            default_role: "design",
        }),
        "gio" => Some(PersonaSpec {
            name: "지오",
            default_provider: "codex",
            default_role: "review",
        }),
        "mina" => Some(PersonaSpec {
            name: "미나",
            default_provider: "agy",
            default_role: "explore",
        }),
        "deepseek" => Some(PersonaSpec {
            name: "딥시기",
            default_provider: "opencode",
            default_role: "assist",
        }),
        _ => None,
    }
}

/// role id -> (라벨, 프롬프트 역할 설명)
fn role_spec(role_id: &str) -> Option<(&'static str, &'static str)> {
    match role_id {
        "design" => Some(("설계", "제품 설계자. 사용자의 막연한 아이디어를 기능 흐름과 화면 구조로 구체화한다.")),
        "review" => Some(("검토", "기획 검토자. 빠진 조건, 위험한 가정, 구현 전에 정해야 할 결정을 짚는다.")),
        "explore" => Some(("탐색", "사용자 탐색자. 실제 사용자가 겪을 상황, 입력 방식, 엣지케이스를 질문한다.")),
        "assist" => Some(("조교", "조교. 다른 페르소나의 설명과 결정을 사용자가 알기 쉽게 풀어 주고, 사용자의 질문에 차분히 답하며 논의를 정리한다.")),
        _ => None,
    }
}

fn persona_role_from_value(config: &serde_json::Value, persona_id: &str) -> Option<String> {
    config
        .get("planning_personas")?
        .get("personas")?
        .get(persona_id)?
        .get("role")?
        .as_str()
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
}

fn resolve_role(persona_id: &str, spec: &PersonaSpec) -> (&'static str, &'static str) {
    let config = read_gui_config_value();
    let role_id = persona_role_from_value(&config, persona_id)
        .unwrap_or_else(|| spec.default_role.to_string());
    role_spec(&role_id)
        .or_else(|| role_spec(spec.default_role))
        .unwrap_or(("", ""))
}

fn provider_spec(provider_id: &str) -> Option<(&'static str, &'static [&'static str])> {
    match provider_id {
        "claude" => Some(("claude", &["-p"])),
        "codex" => Some(("codex", &["exec"])),
        "agy" => Some(("agy", &["-p"])),
        "opencode" => Some(("opencode", &["run", "-m", "opencode/deepseek-v4-flash-free"])),
        _ => None,
    }
}

/// 카테고리당 기능지도에 나열할 디렉터리 상한. 파일 전체가 아니라 디렉터리 구성만
/// 추리므로 큰 프로젝트에서도 출력이 작게 유지된다(토큰 상한 전략은 v2).
const CAP_MAP_MAX_DIRS_PER_CATEGORY: usize = 20;

/// 기능지도 카테고리 정렬 순위. 미지정 카테고리는 뒤로.
fn category_rank(category: &str) -> u8 {
    match category {
        "ui" => 0,
        "core" => 1,
        "entry" => 2,
        "other" => 3,
        _ => 4,
    }
}

/// 코드맵 카테고리를 기획자 친화 라벨로. 미지정은 원문 그대로.
fn category_label(category: &str) -> String {
    match category {
        "ui" => "화면·UI".to_string(),
        "core" => "핵심 엔진/로직".to_string(),
        "entry" => "진입점".to_string(),
        "other" => "기타(빌드·스크립트 등)".to_string(),
        other => other.to_string(),
    }
}

/// 파일 경로의 상위 디렉터리. 루트 파일은 "(루트)".
fn capability_dir_of(path: &str) -> String {
    match path.rfind('/') {
        Some(idx) if idx > 0 => path[..idx].to_string(),
        _ => "(루트)".to_string(),
    }
}

/// project_map.json 의 files 맵을 카테고리 × 디렉터리 구성으로 압축한 '기능지도'.
/// 파일을 전부 나열하지 않고 카테고리별 대표 디렉터리(+파일 수)만 추려 작게 만든다.
/// 파일이 하나도 없으면 None.
fn capability_map_from_files(files: &serde_json::Map<String, serde_json::Value>) -> Option<String> {
    use std::collections::BTreeMap;
    let mut by_category: BTreeMap<String, BTreeMap<String, usize>> = BTreeMap::new();
    for (path, meta) in files {
        let category = meta
            .get("category")
            .and_then(|c| c.as_str())
            .unwrap_or("other")
            .to_string();
        let dir = capability_dir_of(path);
        *by_category.entry(category).or_default().entry(dir).or_insert(0) += 1;
    }
    if by_category.is_empty() {
        return None;
    }
    let mut categories: Vec<String> = by_category.keys().cloned().collect();
    categories.sort_by(|a, b| category_rank(a).cmp(&category_rank(b)).then_with(|| a.cmp(b)));
    let mut out = String::new();
    for category in categories {
        let Some(dirs) = by_category.get(&category) else {
            continue;
        };
        out.push_str("■ ");
        out.push_str(&category_label(&category));
        out.push('\n');
        let mut entries: Vec<(&String, &usize)> = dirs.iter().collect();
        entries.sort_by(|a, b| b.1.cmp(a.1).then_with(|| a.0.cmp(b.0)));
        let shown = entries.len().min(CAP_MAP_MAX_DIRS_PER_CATEGORY);
        for (dir, count) in entries.iter().take(shown) {
            out.push_str(&format!("  · {dir} ({count}개)\n"));
        }
        if entries.len() > shown {
            out.push_str(&format!("  · …외 {}곳\n", entries.len() - shown));
        }
    }
    Some(out.trim_end().to_string())
}

/// 프로젝트의 .vibelign/project_map.json 에서 기능지도를 만든다. 없거나 손상되면 None.
fn build_capability_map(project_dir: &Path) -> Option<String> {
    let path = project_dir.join(".vibelign").join("project_map.json");
    let text = std::fs::read_to_string(path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&text).ok()?;
    let files = value.get("files")?.as_object()?;
    capability_map_from_files(files)
}

fn build_persona_prompt(
    spec: PersonaSpec,
    role: (&'static str, &'static str),
    lines: &[PlanningChatLine<'_>],
    capability_map: Option<&str>,
) -> String {
    let mut prompt = format!(
        "너는 VibeLign 기획방의 {name}다.\n역할: {role}\n\n규칙:\n- 한국어로 답한다.\n- 사용자가 이해하기 쉽게 짧고 구체적으로 답한다.\n- 코드를 작성하지 말고, 기획 대화에 필요한 판단과 질문만 한다.\n- patch, CodeSpeak, anchor 같은 내부 구현 용어를 쓰지 않는다.\n- 구체적인 결론을 낼 때는 그 줄을 라벨로 시작해 한 줄씩 적는다: '핵심 기능:', '사용자 흐름:', '제외할 것:', '질문:'. 해당 없으면 생략하고, 매 줄을 라벨로 강제하지는 않는다.\n",
        name = spec.name,
        role = role.1
    );
    if let Some(map) = capability_map {
        prompt.push_str("\n[이 프로젝트의 구성 — 배경 이해용]\n");
        prompt.push_str(map);
        prompt.push_str("\n(위는 네 이해를 돕는 배경 정보다. 사용자에게 파일 경로나 내부 용어를 나열하지 말고, 무엇을 만들지 판단하는 데만 참고해라.)\n");
    }
    prompt.push_str("\n지금까지의 대화:\n");
    for line in super::planning_persona_context::recent_lines(
        lines,
        super::planning_persona_context::RECENT_CONTEXT_LINES,
    ) {
        let speaker = match (line.role, line.persona_id) {
            ("assistant", Some("chloe")) => "클로이",
            ("assistant", Some("gio")) => "지오",
            ("assistant", Some("mina")) => "미나",
            ("assistant", Some("deepseek")) => "딥시기",
            ("assistant", Some(_)) => "AI",
            ("assistant", None) => "AI",
            _ => "사용자",
        };
        prompt.push_str(speaker);
        prompt.push_str(": ");
        prompt.push_str(line.content.trim());
        prompt.push('\n');
    }
    if role.0 == "설계" {
        prompt.push_str(
            "\n[설계 습관] 결정이 설 때, 가끔 '이건 뭐가 발동시키고 어디에 저장되죠?'를 한 번 되물어라(매 턴 X — 흐름을 깨지 않게).\n",
        );
    }
    prompt.push_str("\n위 대화의 다음 응답을 ");
    prompt.push_str(spec.name);
    prompt.push_str(" 관점에서 작성해.");
    prompt
}

pub(crate) fn find_executable(name: &str) -> Option<PathBuf> {
    std::env::split_paths(&augmented_vib_path()).find_map(|dir| {
        // Unix: 무확장 실행파일을 먼저 본다. Windows: 무확장 파일은 git-bash 용 셔임이라
        // CreateProcess 로 직접 실행할 수 없으므로 건너뛰고 .exe/.cmd/.bat 를 찾는다.
        #[cfg(not(target_os = "windows"))]
        {
            let bare = dir.join(name);
            if bare.is_file() {
                return Some(bare);
            }
        }
        executable_with_extension(&dir, name)
    })
}

// 윈도 실행 확장자 후보를 순서대로 시도하는 순수 코어(exists 주입으로 OS 무관 테스트).
// npm/winget 셔임은 .cmd 가 흔하다. rustc >= 1.77.2 의 Command 가 .cmd/.bat 를
// cmd.exe 경유로 안전하게 실행하므로 경로만 찾으면 그대로 실행된다.
#[cfg(any(target_os = "windows", test))]
fn windows_executable_candidate(
    dir: &Path,
    name: &str,
    exists: impl Fn(&Path) -> bool,
) -> Option<PathBuf> {
    const EXEC_EXTS: &[&str] = &["exe", "cmd", "bat", "com"];
    EXEC_EXTS.iter().find_map(|ext| {
        let candidate = dir.join(format!("{name}.{ext}"));
        exists(&candidate).then_some(candidate)
    })
}

#[cfg(target_os = "windows")]
fn executable_with_extension(dir: &Path, name: &str) -> Option<PathBuf> {
    windows_executable_candidate(dir, name, |p| p.is_file())
}

#[cfg(not(target_os = "windows"))]
fn executable_with_extension(_dir: &Path, _name: &str) -> Option<PathBuf> {
    None
}

pub(crate) fn pick_judge_cli(
    messages: &[crate::commands::planning_chat_types::PlanningChatMessage],
) -> Option<(PathBuf, Vec<String>)> {
    for message in messages.iter().rev() {
        if message.role == "assistant" && message.status == "ok" {
            if let Some(persona_id) = message.persona_id.as_deref() {
                if let Some(resolved) = resolve_persona_cli(persona_id) {
                    return Some(resolved);
                }
            }
        }
    }
    for persona_id in ["chloe", "gio", "mina", "deepseek"] {
        if let Some(resolved) = resolve_persona_cli(persona_id) {
            return Some(resolved);
        }
    }
    None
}

fn resolve_persona_cli(persona_id: &str) -> Option<(PathBuf, Vec<String>)> {
    let spec = persona_spec(persona_id)?;
    for provider in resolve_provider_order(persona_id, &spec) {
        let (executable, args) = match provider_spec(&provider) {
            Some(pair) => pair,
            None => continue,
        };
        if let Some(path) = find_executable(executable) {
            return Some((path, args.iter().map(|a| a.to_string()).collect()));
        }
    }
    None
}

/// 활성 CLI를 골라 프롬프트를 1회 실행하고 stdout을 반환. 없거나 실패하면 None.
pub(crate) fn run_active_ai(
    project_dir: &Path,
    messages: &[crate::commands::planning_chat_types::PlanningChatMessage],
    prompt: &str,
) -> Option<String> {
    let (executable, args) = pick_judge_cli(messages)?;
    let mut cmd = std::process::Command::new(executable);
    cmd.args(&args);
    cmd.arg(prompt);
    cmd.current_dir(project_dir);
    cmd.stdin(std::process::Stdio::null());
    cmd.env("PATH", augmented_vib_path());
    cmd.env("NO_COLOR", "1");
    hide_console(&mut cmd);
    match output_with_timeout(cmd, Duration::from_secs(PERSONA_TIMEOUT_SECS)) {
        Ok(Some(output)) if output.status.success() => {
            Some(String::from_utf8_lossy(&output.stdout).to_string())
        }
        _ => None,
    }
}

/// resolver(실행파일명→설치여부)로 설치된 provider id 만 추린다.
/// provider 후보 순서는 INTERNAL_PROVIDER_PRIORITY(드롭다운/탐지 공용)를 재사용한다.
fn installed_providers_from(resolver: impl Fn(&str) -> bool) -> Vec<String> {
    INTERNAL_PROVIDER_PRIORITY
        .iter()
        .filter(|provider| {
            provider_spec(provider)
                .map(|(executable, _)| resolver(executable))
                .unwrap_or(false)
        })
        .map(|p| (*p).to_string())
        .collect()
}

/// 실제 PATH(augmented)에서 설치된 planning provider 목록.
pub(crate) fn probe_planning_providers() -> Vec<String> {
    installed_providers_from(|executable| find_executable(executable).is_some())
}

#[tauri::command]
pub(crate) fn planning_provider_status() -> Vec<String> {
    probe_planning_providers()
}

#[cfg(test)]
mod tests {
    use super::{build_persona_prompt, capability_map_from_files, classify_failure, fallback_provider_used, installed_providers_from, persona_enabled_from_value, persona_role_from_value, persona_spec, provider_spec, provider_try_order, role_spec, windows_executable_candidate, PlanningChatLine, INTERNAL_PROVIDER_PRIORITY};
    use std::path::Path;

    #[test]
    fn windows_candidate_finds_cmd_shim() {
        let dir = Path::new("/fake/bin");
        // claude.cmd 만 존재(npm 셔임)
        let found = windows_executable_candidate(dir, "claude", |p| {
            p == Path::new("/fake/bin/claude.cmd")
        });
        assert_eq!(found, Some(dir.join("claude.cmd")));
    }

    #[test]
    fn windows_candidate_prefers_exe_over_cmd() {
        let dir = Path::new("/fake/bin");
        let found = windows_executable_candidate(dir, "codex", |p| {
            p == Path::new("/fake/bin/codex.exe") || p == Path::new("/fake/bin/codex.cmd")
        });
        assert_eq!(found, Some(dir.join("codex.exe")));
    }

    #[test]
    fn windows_candidate_none_when_missing() {
        assert_eq!(
            windows_executable_candidate(Path::new("/fake"), "nope", |_| false),
            None
        );
    }

    #[test]
    fn installed_providers_filters_by_resolver() {
        let resolver = |name: &str| matches!(name, "codex" | "agy");
        let installed = installed_providers_from(resolver);
        assert_eq!(installed, vec!["codex".to_string(), "agy".to_string()]);
    }

    #[test]
    fn role_spec_has_label_and_prompt() {
        assert_eq!(role_spec("design").unwrap().0, "설계");
        assert_eq!(role_spec("assist").unwrap().0, "조교");
        assert!(role_spec("review").unwrap().1.contains("검토자"));
    }

    #[test]
    fn persona_role_reads_config_then_default() {
        let v: serde_json::Value = serde_json::from_str(
            r#"{"planning_personas":{"personas":{"chloe":{"role":"review"}}}}"#,
        ).unwrap();
        assert_eq!(persona_role_from_value(&v, "chloe"), Some("review".to_string()));
        assert_eq!(persona_role_from_value(&v, "gio"), None);
    }

    #[test]
    fn persona_default_role_mapping() {
        assert_eq!(persona_spec("chloe").unwrap().default_role, "design");
        assert_eq!(persona_spec("gio").unwrap().default_role, "review");
        assert_eq!(persona_spec("mina").unwrap().default_role, "explore");
        assert_eq!(persona_spec("deepseek").unwrap().default_role, "assist");
    }

    #[test]
    fn provider_spec_returns_executable_and_args() {
        assert_eq!(provider_spec("codex").unwrap(), ("codex", &["exec"][..]));
        assert_eq!(provider_spec("claude").unwrap(), ("claude", &["-p"][..]));
        assert_eq!(provider_spec("agy").unwrap(), ("agy", &["-p"][..]));
        assert_eq!(
            provider_spec("opencode").unwrap(),
            ("opencode", &["run", "-m", "opencode/deepseek-v4-flash-free"][..])
        );
    }

    #[test]
    fn build_persona_prompt_includes_conversation_when_lines_exist() {
        let spec = persona_spec("mina").expect("mina persona");
        let role = role_spec("explore").expect("explore role");
        let lines = [
            PlanningChatLine { role: "user", persona_id: None, content: "화상회의 번역 앱을 만들고 싶어" },
            PlanningChatLine { role: "assistant", persona_id: Some("gio"), content: "회의 플랫폼 범위를 정해야 해요." },
        ];
        let prompt = build_persona_prompt(spec, role, &lines, None);
        assert!(prompt.contains("미나"));
        assert!(prompt.contains("화상회의 번역 앱을 만들고 싶어"));
        assert!(prompt.contains("지오: 회의 플랫폼 범위를 정해야 해요."));
    }

    #[test]
    fn build_persona_prompt_includes_output_label_rule() {
        let spec = persona_spec("chloe").expect("chloe persona");
        let role = role_spec("design").expect("design role");
        let prompt = build_persona_prompt(spec, role, &[], None);
        assert!(prompt.contains("핵심 기능:"));
        assert!(prompt.contains("사용자 흐름:"));
        assert!(prompt.contains("제외할 것:"));
        assert!(prompt.contains("질문:"));
    }

    #[test]
    fn design_role_nudges_for_mechanism() {
        let spec = persona_spec("chloe").expect("chloe persona");
        let role = role_spec("design").expect("design role");
        let prompt = build_persona_prompt(spec, role, &[], None);
        assert!(prompt.contains("발동시키고 어디에 저장"));
    }

    #[test]
    fn try_order_puts_preferred_first_no_dupes() {
        let order = provider_try_order("agy");
        assert_eq!(order[0], "agy");
        let mut seen = std::collections::HashSet::new();
        assert!(order.iter().all(|p| seen.insert(p.clone())));
        for base in INTERNAL_PROVIDER_PRIORITY {
            assert!(order.iter().any(|p| p == base));
        }
    }

    #[test]
    fn persona_enabled_defaults_true_and_reads_false() {
        let v: serde_json::Value = serde_json::from_str(
            r#"{"planning_personas":{"personas":{"gio":{"enabled":false}}}}"#,
        )
        .unwrap();
        assert!(!persona_enabled_from_value(&v, "gio"));
        assert!(persona_enabled_from_value(&v, "chloe")); // 미지정 → true
    }

    #[test]
    fn fallback_provider_used_marks_only_non_preferred() {
        assert_eq!(fallback_provider_used("claude", "claude"), None);
        assert_eq!(fallback_provider_used("claude", "codex"), Some("codex".to_string()));
    }

    #[test]
    fn classify_failure_detects_login_from_stderr() {
        let stderr = "ERROR codex_login: 401 Unauthorized token_expired. Please log out and sign in again.";
        assert_eq!(classify_failure("", stderr), "not_logged_in");
    }

    #[test]
    fn classify_failure_defaults_to_error() {
        assert_eq!(classify_failure("", "some random crash"), "error");
    }

    #[cfg(unix)]
    #[test]
    fn output_with_timeout_returns_output_for_fast_command() {
        let mut cmd = std::process::Command::new("sh");
        cmd.args(["-c", "printf hi"]);
        let out = super::output_with_timeout(cmd, std::time::Duration::from_secs(5))
            .expect("spawn")
            .expect("should not time out");
        assert!(out.status.success());
        assert_eq!(String::from_utf8_lossy(&out.stdout), "hi");
    }

    #[cfg(unix)]
    #[test]
    fn output_with_timeout_kills_slow_command() {
        let mut cmd = std::process::Command::new("sh");
        cmd.args(["-c", "sleep 5"]);
        let result =
            super::output_with_timeout(cmd, std::time::Duration::from_millis(150)).expect("spawn");
        assert!(result.is_none()); // 상한 초과 → 자식 종료 후 None
    }

    #[test]
    fn capability_map_groups_by_category_with_dir_counts() {
        let v: serde_json::Value = serde_json::from_str(
            r#"{
                "vibelign-gui/src/pages/Home.tsx": {"category": "ui"},
                "vibelign-gui/src/pages/Doctor.tsx": {"category": "ui"},
                "vibelign-core/src/backup/cas.rs": {"category": "core"},
                "setup.py": {"category": "other"}
            }"#,
        )
        .unwrap();
        let map = capability_map_from_files(v.as_object().unwrap()).expect("non-empty");
        assert!(map.contains("화면·UI"));
        assert!(map.contains("vibelign-gui/src/pages (2개)"));
        assert!(map.contains("핵심 엔진/로직"));
        assert!(map.contains("vibelign-core/src/backup (1개)"));
        assert!(map.contains("(루트)")); // setup.py
        // ui(rank0) 가 core(rank1) 보다 앞에 온다.
        assert!(map.find("화면·UI").unwrap() < map.find("핵심 엔진/로직").unwrap());
    }

    #[test]
    fn capability_map_none_when_empty() {
        let empty = serde_json::Map::new();
        assert!(capability_map_from_files(&empty).is_none());
    }

    #[test]
    fn capability_map_caps_dirs_per_category() {
        // 한 카테고리에 디렉터리 25곳 → 상한 20 + "…외 5곳".
        let mut obj = serde_json::Map::new();
        for i in 0..25 {
            obj.insert(format!("dir{i}/file.rs"), serde_json::json!({"category": "core"}));
        }
        let map = capability_map_from_files(&obj).expect("non-empty");
        assert!(map.contains("…외 5곳"));
    }

    #[test]
    fn build_persona_prompt_includes_capability_block_and_leak_rule() {
        let spec = persona_spec("chloe").expect("chloe persona");
        let role = role_spec("design").expect("design role");
        let prompt =
            build_persona_prompt(spec, role, &[], Some("■ 화면·UI\n  · src/pages (3개)"));
        assert!(prompt.contains("[이 프로젝트의 구성 — 배경 이해용]"));
        assert!(prompt.contains("src/pages (3개)"));
        assert!(prompt.contains("파일 경로나 내부 용어를 나열하지 말"));
        // 배경 블록은 대화 앞에 온다.
        assert!(prompt.find("배경 이해용").unwrap() < prompt.find("지금까지의 대화").unwrap());
    }

    #[test]
    fn build_persona_prompt_omits_capability_block_when_none() {
        let spec = persona_spec("gio").expect("gio persona");
        let role = role_spec("review").expect("review role");
        let prompt = build_persona_prompt(spec, role, &[], None);
        assert!(!prompt.contains("배경 이해용"));
        assert!(prompt.contains("지금까지의 대화"));
    }
}
// === ANCHOR: PLANNING_PERSONA_END ===
