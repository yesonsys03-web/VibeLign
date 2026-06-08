// === ANCHOR: PLANNING_PERSONA_START ===
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use super::platform::{augmented_vib_path, hide_console};

pub(crate) const INTERNAL_PROVIDER_PRIORITY: &[&str] = &["claude", "codex", "agy", "opencode"];

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

fn persona_provider_from_value(config: &serde_json::Value, persona_id: &str) -> Option<String> {
    config
        .get("planning_personas")?
        .get("personas")?
        .get(persona_id)?
        .get("provider")?
        .as_str()
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
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

/// persona 의 1순위 provider(설정 우선, 없으면 기본)로 시도 목록을 만든다.
fn resolve_provider_order(persona_id: &str, spec: &PersonaSpec) -> Vec<String> {
    let config = read_gui_config_value();
    let preferred = persona_provider_from_value(&config, persona_id)
        .unwrap_or_else(|| spec.default_provider.to_string());
    provider_try_order(&preferred)
}

pub(crate) struct PersonaRun {
    pub(crate) content: String,
    pub(crate) status: String,
    pub(crate) provider_used: Option<String>,
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
    role: &'static str,
    default_provider: &'static str,
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
        };
    };
    let prompt = build_persona_prompt(spec, lines);
    let order = resolve_provider_order(persona_id, &spec);
    let preferred = order.first().cloned().unwrap_or_default();
    for provider in order {
        let Some((executable_name, args)) = provider_spec(&provider) else {
            continue;
        };
        let Some(executable) = find_executable(executable_name) else {
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
        if let Ok(output) = cmd.output() {
            if output.status.success() {
                let content = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !content.is_empty() {
                    return PersonaRun {
                        content,
                        status: "ok".to_string(),
                        provider_used: fallback_provider_used(&preferred, &provider),
                    };
                }
            }
        }
        // 실패 → 다음 provider 로 폴백
    }
    PersonaRun {
        content: "AI 응답을 가져오지 못했어요. 설치된 AI가 없거나 로그인이 필요할 수 있어요.".to_string(),
        status: "failed".to_string(),
        provider_used: None,
    }
}

fn persona_spec(persona_id: &str) -> Option<PersonaSpec> {
    match persona_id {
        "chloe" => Some(PersonaSpec {
            name: "클로이",
            role: "제품 설계자. 사용자의 막연한 아이디어를 기능 흐름과 화면 구조로 구체화한다.",
            default_provider: "claude",
        }),
        "gio" => Some(PersonaSpec {
            name: "지오",
            role: "기획 검토자. 빠진 조건, 위험한 가정, 구현 전에 정해야 할 결정을 짚는다.",
            default_provider: "codex",
        }),
        "mina" => Some(PersonaSpec {
            name: "미나",
            role: "사용자 탐색자. 실제 사용자가 겪을 상황, 입력 방식, 엣지케이스를 질문한다.",
            default_provider: "agy",
        }),
        "deepseek" => Some(PersonaSpec {
            name: "딥시기",
            role: "조교. 다른 페르소나의 설명과 결정을 사용자가 알기 쉽게 풀어 주고, 사용자의 질문에 차분히 답하며 논의를 정리한다.",
            default_provider: "opencode",
        }),
        _ => None,
    }
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

fn build_persona_prompt(spec: PersonaSpec, lines: &[PlanningChatLine<'_>]) -> String {
    let mut prompt = format!(
        "너는 VibeLign 기획방의 {name}다.\n역할: {role}\n\n규칙:\n- 한국어로 답한다.\n- 사용자가 이해하기 쉽게 짧고 구체적으로 답한다.\n- 코드를 작성하지 말고, 기획 대화에 필요한 판단과 질문만 한다.\n- patch, CodeSpeak, anchor 같은 내부 구현 용어를 쓰지 않는다.\n\n지금까지의 대화:\n",
        name = spec.name,
        role = spec.role
    );
    for line in lines {
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
    if spec.name == "클로이" {
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
        let candidate = dir.join(name);
        if candidate.is_file() {
            Some(candidate)
        } else {
            executable_with_extension(&dir, name)
        }
    })
}

#[cfg(target_os = "windows")]
fn executable_with_extension(dir: &Path, name: &str) -> Option<PathBuf> {
    let candidate = dir.join(format!("{name}.exe"));
    candidate.is_file().then_some(candidate)
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
    match cmd.output() {
        Ok(output) if output.status.success() => {
            Some(String::from_utf8_lossy(&output.stdout).to_string())
        }
        _ => None,
    }
}

/// provider 후보 순서(드롭다운/탐지 공용).
const PLANNING_PROVIDERS: &[&str] = &["claude", "codex", "agy", "opencode"];

/// resolver(실행파일명→설치여부)로 설치된 provider id 만 추린다.
fn installed_providers_from(resolver: impl Fn(&str) -> bool) -> Vec<String> {
    PLANNING_PROVIDERS
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
    use super::{build_persona_prompt, fallback_provider_used, installed_providers_from, persona_enabled_from_value, persona_spec, persona_provider_from_value, provider_spec, provider_try_order, PlanningChatLine, INTERNAL_PROVIDER_PRIORITY};

    #[test]
    fn installed_providers_filters_by_resolver() {
        let resolver = |name: &str| matches!(name, "codex" | "agy");
        let installed = installed_providers_from(resolver);
        assert_eq!(installed, vec!["codex".to_string(), "agy".to_string()]);
    }

    #[test]
    fn persona_default_provider_mapping() {
        assert_eq!(persona_spec("chloe").unwrap().default_provider, "claude");
        assert_eq!(persona_spec("gio").unwrap().default_provider, "codex");
        assert_eq!(persona_spec("mina").unwrap().default_provider, "agy");
        assert_eq!(persona_spec("deepseek").unwrap().default_provider, "opencode");
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
        let lines = [
            PlanningChatLine {
                role: "user",
                persona_id: None,
                content: "화상회의 번역 앱을 만들고 싶어",
            },
            PlanningChatLine {
                role: "assistant",
                persona_id: Some("gio"),
                content: "회의 플랫폼 범위를 정해야 해요.",
            },
        ];

        let prompt = build_persona_prompt(spec, &lines);

        assert!(prompt.contains("미나"));
        assert!(prompt.contains("화상회의 번역 앱을 만들고 싶어"));
        assert!(prompt.contains("지오: 회의 플랫폼 범위를 정해야 해요."));
    }

    #[test]
    fn chloe_prompt_nudges_for_mechanism() {
        let spec = persona_spec("chloe").expect("chloe persona");
        let prompt = build_persona_prompt(spec, &[]);
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
    fn persona_provider_reads_config_value() {
        let v: serde_json::Value = serde_json::from_str(
            r#"{"planning_personas":{"personas":{"chloe":{"enabled":true,"provider":"codex"}}}}"#,
        )
        .unwrap();
        assert_eq!(persona_provider_from_value(&v, "chloe"), Some("codex".to_string()));
        assert_eq!(persona_provider_from_value(&v, "mina"), None);
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
}
// === ANCHOR: PLANNING_PERSONA_END ===
