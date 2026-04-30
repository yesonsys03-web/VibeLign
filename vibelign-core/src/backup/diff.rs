use crate::db::schema;
use rusqlite::{params, Connection, OptionalExtension};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

#[derive(Debug, Clone)]
pub struct StoredFile {
    pub relative_path: String,
    pub hash: String,
    pub size: u64,
    pub storage_path: String,
    pub object_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct AddedFile {
    pub relative_path: String,
    pub size: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct ModifiedFile {
    pub relative_path: String,
    pub before_size: u64,
    pub after_size: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct DeletedFile {
    pub relative_path: String,
    pub size: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct DiffSummary {
    pub added_count: usize,
    pub modified_count: usize,
    pub deleted_count: usize,
    pub unchanged_count: usize,
    pub net_size_bytes: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct DiffResult {
    pub added: Vec<AddedFile>,
    pub modified: Vec<ModifiedFile>,
    pub deleted: Vec<DeletedFile>,
    pub summary: DiffSummary,
}

pub fn between_checkpoints(
    root: &Path,
    from_checkpoint_id: &str,
    to_checkpoint_id: &str,
) -> Result<DiffResult, String> {
    let conn = open_db(root)?;
    let from = load_checkpoint_files(&conn, from_checkpoint_id)?;
    let to = load_checkpoint_files(&conn, to_checkpoint_id)?;
    Ok(diff_maps(&from, &to))
}

pub fn open_db(root: &Path) -> Result<Connection, String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Err("checkpoint database missing".to_string());
    }
    let conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    schema::initialize(&conn).map_err(|error| error.to_string())?;
    Ok(conn)
}

pub fn checkpoint_engine_version(
    conn: &Connection,
    checkpoint_id: &str,
) -> Result<Option<String>, String> {
    conn.query_row(
        "SELECT engine_version FROM checkpoints WHERE checkpoint_id = ?",
        params![checkpoint_id],
        |row| row.get(0),
    )
    .optional()
    .map_err(|error| error.to_string())?
    .ok_or_else(|| "checkpoint not found".to_string())
}

pub fn checkpoint_parent_id(
    conn: &Connection,
    checkpoint_id: &str,
) -> Result<Option<String>, String> {
    conn.query_row(
        "SELECT parent_checkpoint_id FROM checkpoints WHERE checkpoint_id = ?",
        params![checkpoint_id],
        |row| row.get(0),
    )
    .optional()
    .map_err(|error| error.to_string())?
    .ok_or_else(|| "checkpoint not found".to_string())
}

pub fn load_checkpoint_files(
    conn: &Connection,
    checkpoint_id: &str,
) -> Result<BTreeMap<String, StoredFile>, String> {
    let exists: Option<i64> = conn
        .query_row(
            "SELECT 1 FROM checkpoints WHERE checkpoint_id = ?",
            params![checkpoint_id],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    if exists.is_none() {
        return Err("checkpoint not found".to_string());
    }
    let mut statement = conn
        .prepare(
            "SELECT relative_path, hash, size, storage_path, object_hash
             FROM checkpoint_files WHERE checkpoint_id = ? ORDER BY relative_path ASC",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![checkpoint_id], |row| {
            Ok(StoredFile {
                relative_path: row.get(0)?,
                hash: row.get(1)?,
                size: row.get::<_, i64>(2)? as u64,
                storage_path: row.get(3)?,
                object_hash: row.get(4)?,
            })
        })
        .map_err(|error| error.to_string())?;
    let mut files = BTreeMap::new();
    for row in rows {
        let file = row.map_err(|error| error.to_string())?;
        files.insert(file.relative_path.clone(), file);
    }
    Ok(files)
}

pub fn diff_maps(
    from: &BTreeMap<String, StoredFile>,
    to: &BTreeMap<String, StoredFile>,
) -> DiffResult {
    let mut added = Vec::new();
    let mut modified = Vec::new();
    let mut deleted = Vec::new();
    let mut unchanged_count = 0_usize;
    let paths = from
        .keys()
        .chain(to.keys())
        .cloned()
        .collect::<BTreeSet<_>>();
    for path in paths {
        match (from.get(&path), to.get(&path)) {
            (None, Some(after)) => added.push(AddedFile {
                relative_path: path,
                size: after.size,
            }),
            (Some(before), None) => deleted.push(DeletedFile {
                relative_path: path,
                size: before.size,
            }),
            (Some(before), Some(after))
                if before.hash != after.hash || before.size != after.size =>
            {
                modified.push(ModifiedFile {
                    relative_path: path,
                    before_size: before.size,
                    after_size: after.size,
                });
            }
            (Some(_), Some(_)) => unchanged_count += 1,
            (None, None) => {}
        }
    }
    let added_bytes = added.iter().map(|file| file.size as i64).sum::<i64>();
    let deleted_bytes = deleted.iter().map(|file| file.size as i64).sum::<i64>();
    let modified_net = modified
        .iter()
        .map(|file| file.after_size as i64 - file.before_size as i64)
        .sum::<i64>();
    DiffResult {
        summary: DiffSummary {
            added_count: added.len(),
            modified_count: modified.len(),
            deleted_count: deleted.len(),
            unchanged_count,
            net_size_bytes: added_bytes + modified_net - deleted_bytes,
        },
        added,
        modified,
        deleted,
    }
}

#[cfg(test)]
mod tests {
    use super::{diff_maps, StoredFile};
    use std::collections::BTreeMap;

    fn file(path: &str, hash: &str, size: u64) -> StoredFile {
        StoredFile {
            relative_path: path.to_string(),
            hash: hash.to_string(),
            size,
            storage_path: String::new(),
            object_hash: None,
        }
    }

    #[test]
    fn classifies_added_modified_deleted_and_empty_changes() {
        let mut from = BTreeMap::new();
        from.insert("delete.txt".to_string(), file("delete.txt", "a", 4));
        from.insert("empty.txt".to_string(), file("empty.txt", "old", 9));
        from.insert("same.txt".to_string(), file("same.txt", "s", 0));
        let mut to = BTreeMap::new();
        to.insert("add.txt".to_string(), file("add.txt", "z", 0));
        to.insert("empty.txt".to_string(), file("empty.txt", "empty", 0));
        to.insert("same.txt".to_string(), file("same.txt", "s", 0));

        let diff = diff_maps(&from, &to);

        assert_eq!(diff.added[0].relative_path, "add.txt");
        assert_eq!(diff.added[0].size, 0);
        assert_eq!(diff.modified[0].relative_path, "empty.txt");
        assert_eq!(diff.modified[0].after_size, 0);
        assert_eq!(diff.deleted[0].relative_path, "delete.txt");
        assert_eq!(diff.summary.unchanged_count, 1);
    }

    #[test]
    fn tracks_all_zero_byte_transition_shapes() {
        let mut empty_from = BTreeMap::new();
        let mut with_zero = BTreeMap::new();
        with_zero.insert("zero.txt".to_string(), file("zero.txt", "empty", 0));
        let added_zero = diff_maps(&empty_from, &with_zero);
        assert_eq!(added_zero.summary.added_count, 1);
        assert_eq!(added_zero.added[0].size, 0);

        empty_from.insert("zero.txt".to_string(), file("zero.txt", "empty", 0));
        let mut with_content = BTreeMap::new();
        with_content.insert("zero.txt".to_string(), file("zero.txt", "content", 7));
        let zero_to_content = diff_maps(&empty_from, &with_content);
        assert_eq!(zero_to_content.summary.modified_count, 1);
        assert_eq!(zero_to_content.modified[0].before_size, 0);
        assert_eq!(zero_to_content.modified[0].after_size, 7);

        let content_to_zero = diff_maps(&with_content, &empty_from);
        assert_eq!(content_to_zero.summary.modified_count, 1);
        assert_eq!(content_to_zero.modified[0].before_size, 7);
        assert_eq!(content_to_zero.modified[0].after_size, 0);

        let deleted_zero = diff_maps(&empty_from, &BTreeMap::new());
        assert_eq!(deleted_zero.summary.deleted_count, 1);
        assert_eq!(deleted_zero.deleted[0].size, 0);
    }

    #[test]
    fn case_only_rename_is_reported_as_delete_and_add() {
        let mut from = BTreeMap::new();
        from.insert("App.tsx".to_string(), file("App.tsx", "a", 1));
        let mut to = BTreeMap::new();
        to.insert("app.tsx".to_string(), file("app.tsx", "a", 1));

        let diff = diff_maps(&from, &to);

        assert_eq!(diff.summary.added_count, 1);
        assert_eq!(diff.summary.deleted_count, 1);
        assert_eq!(diff.added[0].relative_path, "app.tsx");
        assert_eq!(diff.deleted[0].relative_path, "App.tsx");
    }
}
