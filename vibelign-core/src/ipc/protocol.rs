// === ANCHOR: PROTOCOL_START ===
use crate::backup::{db_maintenance, db_viewer, diff, graph_summary, restore, suggestions};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "snake_case")]
pub enum EngineRequest {
    EngineInfo,
    CheckpointCreate {
        root: PathBuf,
        message: String,
        trigger: Option<String>,
        git_commit_sha: Option<String>,
        git_commit_message: Option<String>,
    },
    CheckpointList {
        root: PathBuf,
    },
    CheckpointRestore {
        root: PathBuf,
        checkpoint_id: String,
    },
    CheckpointDiff {
        root: PathBuf,
        from_checkpoint_id: String,
        to_checkpoint_id: String,
    },
    CheckpointRestorePreview {
        root: PathBuf,
        checkpoint_id: String,
    },
    CheckpointRestoreFilesPreview {
        root: PathBuf,
        checkpoint_id: String,
        relative_paths: Vec<String>,
    },
    CheckpointRestoreFilesSafe {
        root: PathBuf,
        checkpoint_id: String,
        relative_paths: Vec<String>,
    },
    CheckpointRestoreSuggestions {
        root: PathBuf,
        checkpoint_id: String,
        cap: Option<usize>,
    },
    CheckpointPrune {
        root: PathBuf,
        keep_latest: usize,
    },
    RetentionApply {
        root: PathBuf,
    },
    BackupDbViewerInspect {
        root: PathBuf,
    },
    BackupDbMaintenance {
        root: PathBuf,
        apply: bool,
    },
    BackupGraphSummary {
        root: PathBuf,
    },
}

#[derive(Debug, Serialize)]
pub struct ResponseCheckpoint {
    pub(crate) checkpoint_id: String,
    pub(crate) created_at: String,
    pub(crate) message: String,
    pub(crate) file_count: usize,
    pub(crate) total_size_bytes: u64,
    pub(crate) pinned: bool,
    pub(crate) trigger: Option<String>,
    pub(crate) git_commit_message: Option<String>,
    pub(crate) files: Vec<ResponseFile>,
}

#[derive(Debug, Serialize)]
pub struct ResponseFile {
    pub(crate) relative_path: String,
    pub(crate) size: u64,
}

#[derive(Debug, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum EngineResponse {
    Ok {
        result: String,
        checkpoint_id: Option<String>,
        created_at: Option<String>,
        message: Option<String>,
        file_count: Option<usize>,
        total_size_bytes: Option<u64>,
        files: Option<Vec<ResponseFile>>,
        checkpoints: Option<Vec<ResponseCheckpoint>>,
        pruned_count: Option<usize>,
        pruned_bytes: Option<u64>,
        diff: Option<diff::DiffResult>,
        preview: Option<restore::preview::RestorePreview>,
        restored_count: Option<usize>,
        suggestions: Option<Vec<suggestions::RestoreSuggestion>>,
        legacy_notice: Option<String>,
    },
    Error {
        code: String,
        message: String,
    },
    #[serde(rename = "ok")]
    RetentionOk {
        result: String,
        pruned_count: usize,
        planned_count: usize,
        planned_bytes: u64,
        reclaimed_bytes: u64,
        partial_failure: bool,
    },
    #[serde(rename = "ok")]
    BackupDbViewerInspectOk {
        result: String,
        #[serde(flatten)]
        report: db_viewer::BackupDbViewerInspectReport,
    },
    #[serde(rename = "ok")]
    BackupDbMaintenanceOk {
        result: String,
        #[serde(flatten)]
        report: db_maintenance::DbMaintenanceReport,
    },
    #[serde(rename = "ok")]
    BackupGraphSummaryOk {
        result: String,
        #[serde(flatten)]
        report: graph_summary::BackupGraphSummaryReport,
    },
}

pub use super::handler::handle;

// === ANCHOR: PROTOCOL_END ===
