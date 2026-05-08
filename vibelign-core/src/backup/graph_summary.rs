use crate::security::path_guard::resolve_under;
use rusqlite::{Connection, OpenFlags};
use serde::Serialize;
use std::cmp::Ordering;
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::path::Path;

// === ANCHOR: BACKUP_GRAPH_SUMMARY_START ===
#[derive(Debug, Clone, Serialize)]
pub struct BackupGraphSummaryReport {
    pub db_exists: bool,
    pub file_row_count: i64,
    pub root: BackupGraphNode,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupGraphNode {
    pub id: String,
    pub name: String,
    pub path: String,
    pub size_bytes: i64,
    pub children: Vec<BackupGraphNode>,
}

#[derive(Debug, Clone)]
struct GraphNodeBuilder {
    name: String,
    path: String,
    size_bytes: i64,
    children: BTreeMap<String, GraphNodeBuilder>,
}

pub fn summarize(root: &Path) -> Result<BackupGraphSummaryReport, String> {
    let db_path = resolve_under(root, ".vibelign/vibelign.db")
        .ok_or_else(|| "backup DB path escaped project root".to_string())?;
    let mut warnings = Vec::new();
    let mut tree = GraphNodeBuilder::root();

    if !db_path.exists() {
        warnings.push("Rust backup DB가 아직 없어요. 백업을 먼저 만들어 주세요.".to_string());
        return Ok(BackupGraphSummaryReport {
            db_exists: false,
            file_row_count: 0,
            root: tree.into_node(),
            warnings,
        });
    }
    reject_symlink_if_exists(&db_path)?;

    let conn = Connection::open_with_flags(
        &db_path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .map_err(|error| format!("failed to open backup DB read-only: {error}"))?;
    if let Err(error) = conn.pragma_update(None, "query_only", true) {
        warnings.push(format!(
            "query_only pragma를 적용하지 못했지만 read-only connection으로 계속 표시합니다: {error}"
        ));
    }

    if !table_exists(&conn, "checkpoint_files")? {
        warnings.push(
            "checkpoint_files table이 없어 백업 범위 그래프를 표시하지 않습니다.".to_string(),
        );
        return Ok(BackupGraphSummaryReport {
            db_exists: true,
            file_row_count: 0,
            root: tree.into_node(),
            warnings,
        });
    }

    let mut statement = conn
        .prepare(
            "SELECT relative_path, size
             FROM checkpoint_files
             WHERE size > 0
             ORDER BY relative_path ASC",
        )
        .map_err(|error| format!("failed to prepare backup graph summary query: {error}"))?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })
        .map_err(|error| format!("failed to read backup graph summary rows: {error}"))?;

    let mut file_row_count = 0_i64;
    for row in rows {
        let (relative_path, size_bytes) =
            row.map_err(|error| format!("failed to parse backup graph summary row: {error}"))?;
        if size_bytes <= 0 {
            continue;
        }
        if tree.add_path(&relative_path, size_bytes) {
            file_row_count += 1;
        }
    }

    Ok(BackupGraphSummaryReport {
        db_exists: true,
        file_row_count,
        root: tree.into_node(),
        warnings,
    })
}

fn table_exists(conn: &Connection, table: &str) -> Result<bool, String> {
    let mut statement = conn
        .prepare("SELECT name FROM sqlite_master WHERE type='table'")
        .map_err(|error| format!("failed to inspect backup DB tables: {error}"))?;
    let rows = statement
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(|error| format!("failed to read backup DB table list: {error}"))?;
    let mut tables = HashSet::new();
    for row in rows {
        tables
            .insert(row.map_err(|error| format!("failed to parse backup DB table name: {error}"))?);
    }
    Ok(tables.contains(table))
}

fn reject_symlink_if_exists(path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            Err("backup graph summary refuses to follow symlinks".to_string())
        }
        Ok(_) | Err(_) => Ok(()),
    }
}

impl GraphNodeBuilder {
    fn root() -> Self {
        Self {
            name: "백업".to_string(),
            path: String::new(),
            size_bytes: 0,
            children: BTreeMap::new(),
        }
    }

    fn add_path(&mut self, raw_path: &str, size_bytes: i64) -> bool {
        let normalized = normalize_relative_path(raw_path);
        if normalized.is_empty() {
            return false;
        }
        self.size_bytes += size_bytes;
        let mut current = self;
        let mut path_parts = Vec::new();
        for part in normalized.split('/') {
            if part.is_empty() {
                continue;
            }
            path_parts.push(part.to_string());
            let path = path_parts.join("/");
            current = current
                .children
                .entry(part.to_string())
                .or_insert_with(|| Self {
                    name: part.to_string(),
                    path,
                    size_bytes: 0,
                    children: BTreeMap::new(),
                });
            current.size_bytes += size_bytes;
        }
        true
    }

    fn into_node(self) -> BackupGraphNode {
        let mut children: Vec<BackupGraphNode> = self
            .children
            .into_values()
            .map(GraphNodeBuilder::into_node)
            .collect();
        children.sort_by(compare_nodes);
        BackupGraphNode {
            id: if self.path.is_empty() {
                "root".to_string()
            } else {
                self.path.clone()
            },
            name: self.name,
            path: self.path,
            size_bytes: self.size_bytes,
            children,
        }
    }
}

fn normalize_relative_path(path: &str) -> String {
    path.replace('\\', "/")
        .split('/')
        .filter(|part| !part.is_empty() && *part != "." && *part != "..")
        .collect::<Vec<_>>()
        .join("/")
}

fn compare_nodes(left: &BackupGraphNode, right: &BackupGraphNode) -> Ordering {
    right
        .size_bytes
        .cmp(&left.size_bytes)
        .then_with(|| left.name.cmp(&right.name))
}
// === ANCHOR: BACKUP_GRAPH_SUMMARY_END ===

#[cfg(test)]
mod tests {
    use super::{normalize_relative_path, summarize};
    use rusqlite::{params, Connection};
    use tempfile::tempdir;

    #[test]
    fn graph_summary_compacts_windows_paths() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        std::fs::create_dir_all(root.join(".vibelign")).unwrap();
        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        conn.execute_batch(
            "CREATE TABLE checkpoint_files(
                id INTEGER PRIMARY KEY,
                checkpoint_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size INTEGER NOT NULL
            );",
        )
        .unwrap();
        conn.execute(
            "INSERT INTO checkpoint_files(checkpoint_id, relative_path, size) VALUES (?, ?, ?)",
            params!["a", "src\\app.py", 10_i64],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO checkpoint_files(checkpoint_id, relative_path, size) VALUES (?, ?, ?)",
            params!["b", "src/lib.rs", 5_i64],
        )
        .unwrap();
        drop(conn);

        let report = summarize(root).unwrap();

        assert!(report.db_exists);
        assert_eq!(report.file_row_count, 2);
        assert_eq!(report.root.size_bytes, 15);
        assert_eq!(report.root.children[0].path, "src");
        assert_eq!(report.root.children[0].children.len(), 2);
    }

    #[test]
    fn relative_path_normalization_skips_unsafe_segments() {
        assert_eq!(normalize_relative_path("src\\./../app.py"), "src/app.py");
    }

    #[test]
    #[cfg(unix)]
    fn graph_summary_rejects_symlinked_db_source() {
        use std::os::unix::fs::symlink;

        let temp = tempdir().unwrap();
        let root = temp.path();
        let db_dir = root.join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let outside = root.join("outside.db");
        let conn = Connection::open(&outside).unwrap();
        conn.execute_batch(
            "CREATE TABLE checkpoint_files(
                id INTEGER PRIMARY KEY,
                checkpoint_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size INTEGER NOT NULL
            );",
        )
        .unwrap();
        drop(conn);
        symlink(&outside, db_dir.join("vibelign.db")).unwrap();

        let error = summarize(root).unwrap_err();

        assert!(error.contains("symlink"));
    }
}
