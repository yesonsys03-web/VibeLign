// === ANCHOR: HANDLER_START ===
use crate::backup::checkpoint::{self, CheckpointCreateMetadata};
use crate::backup::retention;
use crate::backup::{db_maintenance, db_viewer, diff, graph_summary, restore, suggestions};

use super::protocol::{EngineRequest, EngineResponse, ResponseCheckpoint, ResponseFile};

pub fn handle(request: EngineRequest) -> EngineResponse {
    match request {
        EngineRequest::EngineInfo => EngineResponse::Ok {
            result: "engine_info".to_string(),
            checkpoint_id: None,
            created_at: None,
            message: None,
            file_count: None,
            total_size_bytes: None,
            files: None,
            checkpoints: None,
            pruned_count: None,
            pruned_bytes: None,
            diff: None,
            preview: None,
            restored_count: None,
            suggestions: None,
            legacy_notice: None,
        },
        EngineRequest::CheckpointCreate {
            root,
            message,
            trigger,
            git_commit_sha,
            git_commit_message,
        } => {
            match checkpoint::create_with_metadata(
                &root,
                &message,
                CheckpointCreateMetadata {
                    trigger,
                    git_commit_sha,
                    git_commit_message,
                },
            ) {
                Ok(Some(created)) => {
                    let files = created
                        .files
                        .into_iter()
                        .map(|file| ResponseFile {
                            relative_path: file.relative_path,
                            size: file.size,
                        })
                        .collect();
                    EngineResponse::Ok {
                        result: "created".to_string(),
                        checkpoint_id: Some(created.checkpoint_id),
                        created_at: Some(created.created_at),
                        message: Some(message),
                        file_count: Some(created.file_count),
                        total_size_bytes: Some(created.total_size_bytes),
                        files: Some(files),
                        checkpoints: None,
                        pruned_count: None,
                        pruned_bytes: None,
                        diff: None,
                        preview: None,
                        restored_count: None,
                        suggestions: None,
                        legacy_notice: None,
                    }
                }
                Ok(None) => EngineResponse::Ok {
                    result: "no_changes".to_string(),
                    checkpoint_id: None,
                    created_at: None,
                    message: Some(message),
                    file_count: Some(0),
                    total_size_bytes: Some(0),
                    files: Some(Vec::new()),
                    checkpoints: None,
                    pruned_count: None,
                    pruned_bytes: None,
                    diff: None,
                    preview: None,
                    restored_count: None,
                    suggestions: None,
                    legacy_notice: None,
                },
                Err(error) => EngineResponse::Error {
                    code: "CHECKPOINT_CREATE_FAILED".to_string(),
                    message: error,
                },
            }
        }
        EngineRequest::CheckpointList { root } => match checkpoint::list(&root) {
            Ok(checkpoints) => {
                let checkpoints = checkpoints
                    .into_iter()
                    .map(|checkpoint| ResponseCheckpoint {
                        checkpoint_id: checkpoint.checkpoint_id,
                        created_at: checkpoint.created_at,
                        message: checkpoint.message,
                        file_count: checkpoint.file_count,
                        total_size_bytes: checkpoint.total_size_bytes,
                        pinned: checkpoint.pinned,
                        trigger: checkpoint.trigger,
                        git_commit_message: checkpoint.git_commit_message,
                        files: checkpoint
                            .files
                            .into_iter()
                            .map(|file| ResponseFile {
                                relative_path: file.relative_path,
                                size: file.size,
                            })
                            .collect(),
                    })
                    .collect();
                EngineResponse::Ok {
                    result: "listed".to_string(),
                    checkpoint_id: None,
                    created_at: None,
                    message: None,
                    file_count: None,
                    total_size_bytes: None,
                    files: None,
                    checkpoints: Some(checkpoints),
                    pruned_count: None,
                    pruned_bytes: None,
                    diff: None,
                    preview: None,
                    restored_count: None,
                    suggestions: None,
                    legacy_notice: None,
                }
            }
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_LIST_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointRestore {
            root,
            checkpoint_id,
        } => match restore::full::restore_full(&root, &checkpoint_id) {
            Ok(()) => EngineResponse::Ok {
                result: "restored".to_string(),
                checkpoint_id: Some(checkpoint_id),
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: None,
                restored_count: None,
                suggestions: None,
                legacy_notice: None,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_RESTORE_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointPrune { root, keep_latest } => {
            match checkpoint::prune(&root, keep_latest) {
                Ok(result) => EngineResponse::Ok {
                    result: "pruned".to_string(),
                    checkpoint_id: None,
                    created_at: None,
                    message: None,
                    file_count: None,
                    total_size_bytes: None,
                    files: None,
                    checkpoints: None,
                    pruned_count: Some(result.count),
                    pruned_bytes: Some(result.bytes),
                    diff: None,
                    preview: None,
                    restored_count: None,
                    suggestions: None,
                    legacy_notice: None,
                },
                Err(error) => EngineResponse::Error {
                    code: "CHECKPOINT_PRUNE_FAILED".to_string(),
                    message: error,
                },
            }
        }
        EngineRequest::RetentionApply { root } => match retention::apply(&root) {
            Ok(result) => EngineResponse::RetentionOk {
                result: "retention_applied".to_string(),
                pruned_count: result.deleted_count,
                planned_count: result.planned_count,
                planned_bytes: result.planned_bytes,
                reclaimed_bytes: result.reclaimed_bytes,
                partial_failure: result.partial_failure,
            },
            Err(error) => EngineResponse::Error {
                code: "RETENTION_APPLY_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::BackupDbViewerInspect { root } => match db_viewer::inspect(&root) {
            Ok(report) => EngineResponse::BackupDbViewerInspectOk {
                result: "backup_db_viewer_inspect".to_string(),
                report,
            },
            Err(error) => EngineResponse::Error {
                code: "BACKUP_DB_VIEWER_INSPECT_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointDiff {
            root,
            from_checkpoint_id,
            to_checkpoint_id,
        } => match diff::between_checkpoints(&root, &from_checkpoint_id, &to_checkpoint_id) {
            Ok(result) => EngineResponse::Ok {
                result: "diffed".to_string(),
                checkpoint_id: None,
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: Some(result),
                preview: None,
                restored_count: None,
                suggestions: None,
                legacy_notice: None,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_DIFF_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointRestorePreview {
            root,
            checkpoint_id,
        } => match restore::preview::preview_full(&root, &checkpoint_id) {
            Ok(result) => EngineResponse::Ok {
                result: "previewed".to_string(),
                checkpoint_id: Some(checkpoint_id),
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: Some(result),
                restored_count: None,
                suggestions: None,
                legacy_notice: None,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_PREVIEW_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointRestoreFilesPreview {
            root,
            checkpoint_id,
            relative_paths,
        } => match restore::preview::preview_selected(&root, &checkpoint_id, &relative_paths) {
            Ok(result) => EngineResponse::Ok {
                result: "previewed".to_string(),
                checkpoint_id: Some(checkpoint_id),
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: Some(result),
                restored_count: None,
                suggestions: None,
                legacy_notice: None,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_PREVIEW_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointRestoreFilesSafe {
            root,
            checkpoint_id,
            relative_paths,
        } => match restore::files::restore_selected(&root, &checkpoint_id, &relative_paths) {
            Ok(count) => EngineResponse::Ok {
                result: "restored_files".to_string(),
                checkpoint_id: Some(checkpoint_id),
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: None,
                restored_count: Some(count),
                suggestions: None,
                legacy_notice: None,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_RESTORE_FILES_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::CheckpointRestoreSuggestions {
            root,
            checkpoint_id,
            cap,
        } => match suggestions::suggest(&root, &checkpoint_id, cap.unwrap_or(5)) {
            Ok(result) => EngineResponse::Ok {
                result: "suggested".to_string(),
                checkpoint_id: Some(checkpoint_id),
                created_at: None,
                message: None,
                file_count: None,
                total_size_bytes: None,
                files: None,
                checkpoints: None,
                pruned_count: None,
                pruned_bytes: None,
                diff: None,
                preview: None,
                restored_count: None,
                suggestions: Some(result.suggestions),
                legacy_notice: result.legacy_notice,
            },
            Err(error) => EngineResponse::Error {
                code: "CHECKPOINT_SUGGESTIONS_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::BackupDbMaintenance { root, apply } => {
            let result = if apply {
                db_maintenance::compact(&root)
            } else {
                db_maintenance::inspect(&root)
            };
            match result {
                Ok(report) => EngineResponse::BackupDbMaintenanceOk {
                    result: "backup_db_maintenance".to_string(),
                    report,
                },
                Err(error) => EngineResponse::Error {
                    code: "BACKUP_DB_MAINTENANCE_FAILED".to_string(),
                    message: error,
                },
            }
        }
        EngineRequest::BackupGraphSummary { root } => match graph_summary::summarize(&root) {
            Ok(report) => EngineResponse::BackupGraphSummaryOk {
                result: "backup_graph_summary".to_string(),
                report,
            },
            Err(error) => EngineResponse::Error {
                code: "BACKUP_GRAPH_SUMMARY_FAILED".to_string(),
                message: error,
            },
        },
    }
}

#[cfg(test)]
mod tests {
    use super::handle;
    use crate::ipc::protocol::{EngineRequest, EngineResponse};

    #[test]
    fn engine_info_returns_ok() {
        let response = handle(EngineRequest::EngineInfo);
        assert!(matches!(response, EngineResponse::Ok { .. }));
    }
}
// === ANCHOR: HANDLER_END ===
