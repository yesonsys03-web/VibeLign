// === ANCHOR: GIT_STATUS_START ===
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ChangeStatus {
    Modified,
    New,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct ChangedEntry {
    pub path: String,
    pub status: ChangeStatus,
}

/// git status 기반 변경 경로 집합. 비-git 디렉토리는 빈 Vec (에러 아님).
/// 반환 경로는 `root` 기준 상대경로(`/` 구분)이며, 디스크에 실제 존재하는 파일만 포함한다
/// (삭제·경로 불일치는 자연히 제외된다).
/// Windows: GUI 프로세스가 콘솔 자식(git)을 spawn 할 때 콘솔 창이 깜빡였다 사라지는 것을 막는다.
/// (code_access/vib_bridge/watch 등에서 쓰는 CREATE_NO_WINDOW 패턴과 동일.)
fn apply_no_window(cmd: &mut std::process::Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    #[cfg(not(windows))]
    let _ = cmd;
}

pub(crate) fn list_changed_paths(root: &Path) -> Result<Vec<ChangedEntry>, String> {
    // 1. git 저장소인지 — 아니면 마커 없음
    let mut probe_cmd = std::process::Command::new("git");
    probe_cmd
        .args(["-C"])
        .arg(root)
        .args(["rev-parse", "--is-inside-work-tree"]);
    apply_no_window(&mut probe_cmd);
    let probe = match probe_cmd.output() {
        Ok(o) => o,
        Err(_) => return Ok(Vec::new()), // git 미설치 → 마커 없음
    };
    if !probe.status.success() {
        return Ok(Vec::new());
    }

    // 2. root가 repo 하위 디렉토리일 때의 prefix (예: "vibelign-gui/"), repo 루트면 ""
    let mut prefix_cmd = std::process::Command::new("git");
    prefix_cmd
        .args(["-C"])
        .arg(root)
        .args(["rev-parse", "--show-prefix"]);
    apply_no_window(&mut prefix_cmd);
    let prefix = prefix_cmd
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    // 3. porcelain -z: NUL 구분, 경로 이스케이프 없음(한글/공백 안전)
    let mut status_cmd = std::process::Command::new("git");
    status_cmd.args(["-C"]).arg(root).args([
        "status",
        "--porcelain",
        "-z",
        "--untracked-files=all",
    ]);
    apply_no_window(&mut status_cmd);
    let out = status_cmd
        .output()
        .map_err(|e| format!("git status 실행 실패: {e}"))?;
    if !out.status.success() {
        return Ok(Vec::new());
    }
    // 비-UTF8 파일명(드묾, Linux 한정)은 U+FFFD 로 치환 → is_file() 불일치 → 조용히 제외.
    let raw = String::from_utf8_lossy(&out.stdout);

    let mut entries = Vec::new();
    let mut tokens = raw.split('\0');
    while let Some(entry) = tokens.next() {
        // 각 엔트리는 "XY PATH" (X=index, Y=worktree, 그다음 공백, 그다음 경로)
        if entry.len() < 4 {
            continue;
        }
        let xy = &entry[0..2];
        let path = &entry[3..]; // entry[2]는 공백
                                // rename/copy 는 -z 에서 "XY new\0old" 2토큰 → old 토큰을 소비
        let bytes = xy.as_bytes();
        let is_rename =
            bytes[0] == b'R' || bytes[1] == b'R' || bytes[0] == b'C' || bytes[1] == b'C';
        if is_rename {
            let _orig = tokens.next();
        }

        let status = if xy == "??" {
            ChangeStatus::New
        } else {
            ChangeStatus::Modified
        };

        // root 기준 상대경로로 정규화. git -C 의 경로 기준(cwd=root vs repo-root)이
        // 버전/플랫폼마다 다를 수 있어, 디스크에 실제 존재하는 쪽을 채택한다
        // (삭제·root 밖 경로는 자동 제외).
        let rel = match resolve_rel(path, &prefix, root) {
            Some(r) => r,
            None => continue,
        };
        entries.push(ChangedEntry { path: rel, status });
    }
    Ok(entries)
}

/// porcelain 경로를 `root` 기준 상대경로로 해석한다.
/// `git status --porcelain` 경로는 **repo-root 기준**이다(실측: git 2.50.1,
/// status.relativePaths 무관). 따라서:
/// - root 가 repo 하위(prefix 비어있지 않음)면, root 안의 파일은 반드시 prefix 로 시작한다.
///   prefix 로 시작하지 않으면 root 밖 → 제외. (이전 as-is 폴백은 동명 파일 오탐을 유발)
/// - prefix 가 비어있으면 root == repo 루트 → 경로가 곧 root 기준.
/// 어느 경우든 디스크에 실제 존재하는 파일만 통과(삭제 자동 제외).
fn resolve_rel(path: &str, prefix: &str, root: &Path) -> Option<String> {
    let p = path.replace('\\', "/");
    if !prefix.is_empty() {
        let stripped = p.strip_prefix(prefix)?;
        return root.join(stripped).is_file().then(|| stripped.to_string());
    }
    root.join(&p).is_file().then(|| p)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn git_available() -> bool {
        std::process::Command::new("git")
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    fn run(root: &Path, args: &[&str]) {
        let st = std::process::Command::new("git")
            .args(["-C"])
            .arg(root)
            .args(args)
            .status()
            .expect("git");
        assert!(st.success(), "git {args:?} failed");
    }

    fn write(root: &Path, rel: &str, content: &[u8]) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, content).unwrap();
    }

    fn init_repo(root: &Path) {
        run(root, &["init", "-q", "-b", "main"]);
        run(root, &["config", "user.email", "t@t.dev"]);
        run(root, &["config", "user.name", "t"]);
    }

    #[test]
    fn non_git_dir_returns_empty() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"x\n");
        let changed = list_changed_paths(root.path()).expect("ok");
        assert!(changed.is_empty());
    }

    #[test]
    fn modified_tracked_file_is_modified() {
        if !git_available() {
            return;
        }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/main.ts", b"old\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        write(root.path(), "src/main.ts", b"new\n"); // worktree 수정

        let changed = list_changed_paths(root.path()).expect("ok");
        let hit = changed
            .iter()
            .find(|e| e.path == "src/main.ts")
            .expect("found");
        assert_eq!(hit.status, ChangeStatus::Modified);
    }

    #[test]
    fn untracked_file_is_new() {
        if !git_available() {
            return;
        }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/main.ts", b"a\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        write(root.path(), "src/brand_new.ts", b"fresh\n"); // add 안 함

        let changed = list_changed_paths(root.path()).expect("ok");
        let hit = changed
            .iter()
            .find(|e| e.path == "src/brand_new.ts")
            .expect("found");
        assert_eq!(hit.status, ChangeStatus::New);
    }

    #[test]
    fn deleted_file_is_excluded() {
        if !git_available() {
            return;
        }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/gone.ts", b"bye\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        std::fs::remove_file(root.path().join("src/gone.ts")).unwrap();

        let changed = list_changed_paths(root.path()).expect("ok");
        assert!(changed.iter().all(|e| e.path != "src/gone.ts"));
    }

    #[test]
    fn subdir_root_paths_are_relative_to_root() {
        if !git_available() {
            return;
        }
        // repo 루트에서 init 후, 하위 디렉토리 app/ 을 root 로 사용
        let repo = TempDir::new().unwrap();
        init_repo(repo.path());
        write(repo.path(), "app/src/main.ts", b"old\n");
        write(repo.path(), "outside.ts", b"o\n");
        run(repo.path(), &["add", "."]);
        run(repo.path(), &["commit", "-q", "-m", "init"]);
        write(repo.path(), "app/src/main.ts", b"new\n");

        let root = repo.path().join("app");
        let changed = list_changed_paths(&root).expect("ok");
        // root 기준 상대경로 "src/main.ts" 로 나와야 한다 (app/ prefix 제거)
        let hit = changed
            .iter()
            .find(|e| e.path == "src/main.ts")
            .expect("found");
        assert_eq!(hit.status, ChangeStatus::Modified);
        // app/ 밖의 outside.ts 는 포함되지 않는다
        assert!(changed.iter().all(|e| !e.path.contains("outside.ts")));
    }

    #[test]
    fn renamed_file_uses_new_path() {
        if !git_available() {
            return;
        }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/old.ts", b"x\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        run(root.path(), &["mv", "src/old.ts", "src/new.ts"]);

        let changed = list_changed_paths(root.path()).expect("ok");
        assert!(
            changed.iter().any(|e| e.path == "src/new.ts"),
            "new path present"
        );
        assert!(
            changed.iter().all(|e| e.path != "src/old.ts"),
            "old path absent"
        );
    }
}
// === ANCHOR: GIT_STATUS_END ===
