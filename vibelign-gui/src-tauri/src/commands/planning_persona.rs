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
            args_before_prompt: &["--print"],
        }),
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
            ("assistant", Some(_)) => "AI",
            ("assistant", None) => "AI",
            _ => "사용자",
        };
        prompt.push_str(speaker);
        prompt.push_str(": ");
        prompt.push_str(line.content.trim());
        prompt.push('\n');
    }
    prompt.push_str("\n위 대화의 다음 응답을 ");
    prompt.push_str(spec.name);
    prompt.push_str(" 관점에서 작성해.");
    prompt
}

fn find_executable(name: &str) -> Option<PathBuf> {
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
}
