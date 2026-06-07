// === ANCHOR: PLANNING_PERSONA_START ===
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use super::platform::{augmented_vib_path, hide_console};

pub(crate) struct PersonaRun {
    pub(crate) content: String,
    pub(crate) status: String,
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
    executable: &'static str,
    args_before_prompt: &'static [&'static str],
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
        };
    };
    let Some(executable) = find_executable(spec.executable) else {
        return PersonaRun {
            content: format!(
                "{} CLI를 찾지 못했어요. 설치 또는 PATH 설정을 확인해 주세요.",
                spec.name
            ),
            status: "failed".to_string(),
        };
    };
    let prompt = build_persona_prompt(spec, lines);
    let mut cmd = Command::new(executable);
    cmd.args(spec.args_before_prompt);
    cmd.arg(prompt);
    cmd.current_dir(project_dir);
    cmd.stdin(Stdio::null());
    cmd.env("PATH", augmented_vib_path());
    cmd.env("NO_COLOR", "1");
    hide_console(&mut cmd);

    match cmd.output() {
        Ok(output) if output.status.success() => {
            let content = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if content.is_empty() {
                failed_persona_run()
            } else {
                PersonaRun {
                    content,
                    status: "ok".to_string(),
                }
            }
        }
        Ok(_) | Err(_) => failed_persona_run(),
    }
}

fn failed_persona_run() -> PersonaRun {
    PersonaRun {
        content: "AI 응답을 가져오지 못했어요. 로그인 상태나 CLI 설정을 확인해 주세요.".to_string(),
        status: "failed".to_string(),
    }
}

fn persona_spec(persona_id: &str) -> Option<PersonaSpec> {
    match persona_id {
        "chloe" => Some(PersonaSpec {
            name: "클로이",
            role: "제품 설계자. 사용자의 막연한 아이디어를 기능 흐름과 화면 구조로 구체화한다.",
            executable: "claude",
            args_before_prompt: &["-p"],
        }),
        "gio" => Some(PersonaSpec {
            name: "지오",
            role: "기획 검토자. 빠진 조건, 위험한 가정, 구현 전에 정해야 할 결정을 짚는다.",
            executable: "codex",
            args_before_prompt: &["exec"],
        }),
        "mina" => Some(PersonaSpec {
            name: "미나",
            role: "사용자 탐색자. 실제 사용자가 겪을 상황, 입력 방식, 엣지케이스를 질문한다.",
            executable: "agy",
            args_before_prompt: &["-p"],
        }),
        "deepseek" => Some(PersonaSpec {
            name: "딥시기",
            role: "조교. 다른 페르소나의 설명과 결정을 사용자가 알기 쉽게 풀어 주고, 사용자의 질문에 차분히 답하며 논의를 정리한다.",
            executable: "opencode",
            args_before_prompt: &["run", "-m", "opencode/deepseek-v4-flash-free"],
        }),
        _ => None,
    }
}

pub(crate) fn persona_cli(persona_id: &str) -> Option<(&'static str, &'static [&'static str])> {
    let spec = persona_spec(persona_id)?;
    Some((spec.executable, spec.args_before_prompt))
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
    let (executable, args) = persona_cli(persona_id)?;
    let path = find_executable(executable)?;
    Some((path, args.iter().map(|arg| arg.to_string()).collect()))
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

#[cfg(test)]
mod tests {
    use super::{build_persona_prompt, persona_spec, PlanningChatLine};

    #[test]
    fn persona_spec_maps_gio_to_codex_when_known_persona() {
        let spec = persona_spec("gio").expect("gio persona");

        assert_eq!(spec.executable, "codex");
        assert_eq!(spec.args_before_prompt, &["exec"]);
    }

    #[test]
    fn persona_spec_maps_mina_to_agy_print_mode() {
        let spec = persona_spec("mina").expect("mina persona");

        assert_eq!(spec.executable, "agy");
        assert_eq!(spec.args_before_prompt, &["-p"]);
    }

    #[test]
    fn persona_spec_maps_deepseek_to_opencode_free_model() {
        let spec = persona_spec("deepseek").expect("deepseek persona");

        assert_eq!(spec.executable, "opencode");
        assert_eq!(
            spec.args_before_prompt,
            &["run", "-m", "opencode/deepseek-v4-flash-free"]
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
}
// === ANCHOR: PLANNING_PERSONA_END ===
