// === ANCHOR: PROJECT_SUMMARY_START ===
use serde::Serialize;

use super::platform::hide_console;

/// Windows에서 PATH에 git이 없을 때도 기본 설치 경로에서 찾아 반환
fn git_cmd() -> std::process::Command {
    // PATH에서 찾히면 바로 사용
    let mut probe = std::process::Command::new("git");
    probe.arg("--version");
    hide_console(&mut probe);
    if probe.output().map(|o| o.status.success()).unwrap_or(false) {
        let mut cmd = std::process::Command::new("git");
        hide_console(&mut cmd);
        return cmd;
    }
    #[cfg(target_os = "windows")]
    {
        let candidates = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ];
        for path in &candidates {
            if std::path::Path::new(path).exists() {
                let mut cmd = std::process::Command::new(path);
                hide_console(&mut cmd);
                return cmd;
            }
        }
    }
    let mut cmd = std::process::Command::new("git"); // 최후 수단 — 실패해도 에러는 호출부에서 처리
    hide_console(&mut cmd);
    cmd
}

fn trunc(s: &str, max: usize) -> String {
    let mut chars = s.chars();
    let result: String = chars.by_ref().take(max).collect();
    if chars.next().is_some() {
        format!("{}…", result)
    } else {
        result
    }
}

fn parse_checkpoints_from_ctx(content: &str) -> Vec<[String; 2]> {
    let mut in_section = false;
    let mut results = Vec::new();
    for line in content.lines() {
        if line.starts_with("## 4.") {
            in_section = true;
            continue;
        }
        if in_section && line.starts_with("## ") {
            break;
        }
        if !in_section || !line.starts_with('|') {
            continue;
        }
        let cols: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if cols.len() < 3 {
            continue;
        }
        let ts = cols[1];
        let msg = cols[2];
        if msg.is_empty() || msg == "작업 내용" || msg.starts_with('-') || msg == "(메시지 없음)"
        {
            continue;
        }
        let detail = format!("{} — {}", ts, msg);
        results.push([trunc(msg, 20), detail]);
        if results.len() >= 2 {
            break;
        }
    }
    results
}

#[derive(Serialize)]
struct SummaryLine {
    display: String,
    detail: String,
}

#[derive(Serialize)]
pub(crate) struct ProjectSummary {
    project_name: String,
    checkpoints: Vec<SummaryLine>,
    git_commits: Vec<SummaryLine>,
}

#[tauri::command]
pub(crate) fn read_project_summary(dir: String) -> ProjectSummary {
    let path = std::path::Path::new(&dir);
    let project_name = path
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "프로젝트".to_string());

    // git log: hash|subject|date (최근 3개)
    let git_commits = git_cmd()
        .args(["log", "-3", "--pretty=format:%h|%s|%ad", "--date=short"])
        .current_dir(path)
        .output()
        .ok()
        .map(|o| {
            String::from_utf8_lossy(&o.stdout)
                .lines()
                .filter_map(|l| {
                    let parts: Vec<&str> = l.splitn(3, '|').collect();
                    if parts.len() < 2 {
                        return None;
                    }
                    let hash = parts[0].trim();
                    let subject = parts[1].trim();
                    if subject.is_empty() {
                        return None;
                    }
                    let date = parts.get(2).copied().unwrap_or("").trim();

                    // git show --stat: 변경 파일 목록 (on-load 프리페치)
                    let stat = git_cmd()
                        .args(["show", "--stat", "--pretty=format:%b", hash])
                        .current_dir(path)
                        .output()
                        .ok()
                        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                        .unwrap_or_default();

                    let mut detail = format!("{} — {}", date, subject);
                    if !stat.is_empty() {
                        detail.push_str(&format!("\n\n{}", stat));
                    }

                    Some(SummaryLine {
                        display: trunc(subject, 20),
                        detail,
                    })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let content = std::fs::read_to_string(path.join("PROJECT_CONTEXT.md")).unwrap_or_default();
    let checkpoints = parse_checkpoints_from_ctx(&content)
        .into_iter()
        .map(|[display, detail]| SummaryLine { display, detail })
        .collect();

    ProjectSummary {
        project_name,
        checkpoints,
        git_commits,
    }
}
// === ANCHOR: PROJECT_SUMMARY_END ===
