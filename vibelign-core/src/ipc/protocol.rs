// === ANCHOR: PROTOCOL_START ===
use crate::backup::{db_maintenance, db_viewer, diff, graph_summary, restore, suggestions};
use crate::project_scan;
use crate::secret_scan;
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
    ProjectScan {
        root: PathBuf,
    },
    SecretScanDiff {
        diff_text: String,
        path_hint: String,
    },
    AiEnhancementStatus {
        root: PathBuf,
    },
    AutoBackupStatus {
        root: PathBuf,
    },
    AnchorListMeta {
        root: PathBuf,
    },
    AiEnhancementSet {
        root: PathBuf,
        enabled: bool,
    },
    AutoBackupSet {
        root: PathBuf,
        enabled: bool,
    },
    AnchorSetIntent {
        root: PathBuf,
        anchor_name: String,
        intent: String,
        #[serde(default)]
        connects: Option<Vec<String>>,
        #[serde(default)]
        warning: Option<String>,
        #[serde(default)]
        aliases: Option<Vec<String>>,
        #[serde(default)]
        description: Option<String>,
    },
    MemorySummaryRead {
        root: PathBuf,
        #[serde(default = "default_memory_tool")]
        tool: String,
    },
}

fn default_memory_tool() -> String {
    "vib-gui".to_string()
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
    #[serde(rename = "ok")]
    ProjectScanOk {
        result: String,
        #[serde(flatten)]
        report: project_scan::ProjectScanReport,
    },
    #[serde(rename = "ok")]
    SecretScanDiffOk {
        result: String,
        path_hint: String,
        findings: Vec<secret_scan::SecretFinding>,
    },
    #[serde(rename = "ok")]
    BoolStatusOk {
        result: String,
        enabled: bool,
    },
    #[serde(rename = "ok")]
    AnchorListMetaOk {
        result: String,
        meta: serde_json::Map<String, serde_json::Value>,
    },
    #[serde(rename = "ok")]
    AnchorSetIntentOk {
        result: String,
        anchor_name: String,
        entry: serde_json::Map<String, serde_json::Value>,
    },
    #[serde(rename = "ok")]
    MemorySummaryReadOk {
        result: String,
        payload: serde_json::Value,
    },
}

pub use super::handler::handle;

#[cfg(test)]
mod tests {
    use super::{handle, EngineRequest, EngineResponse};

    #[test]
    fn engine_info_returns_ok() {
        let response = handle(EngineRequest::EngineInfo);
        assert!(matches!(response, EngineResponse::Ok { .. }));
    }

    #[test]
    fn project_scan_request_parses() {
        let request = serde_json::from_value::<EngineRequest>(serde_json::json!({
            "command": "project_scan",
            "root": "/tmp/demo"
        }));

        assert!(request.is_ok());
    }

    #[test]
    fn secret_scan_diff_request_parses() {
        let request = serde_json::from_value::<EngineRequest>(serde_json::json!({
            "command": "secret_scan_diff",
            "diff_text": "diff --git a/x b/x\n",
            "path_hint": "x"
        }));

        assert!(request.is_ok());
    }
}
// === ANCHOR: PROTOCOL_END ===
