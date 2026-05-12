// === ANCHOR: HANDLER_START ===
use crate::anchor_meta;
use crate::backup::checkpoint::{self, CheckpointCreateMetadata};
use crate::backup::retention;
use crate::backup::{db_maintenance, db_viewer, diff, graph_summary, restore, suggestions};
use crate::config;
use crate::memory_audit::{self, MemoryAuditEventBuilder};
use crate::memory_state;
use crate::project_scan;
use crate::secret_scan;

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
        EngineRequest::ProjectScan { root } => match project_scan::scan(&root) {
            Ok(report) => EngineResponse::ProjectScanOk {
                result: "project_scan".to_string(),
                report,
            },
            Err(error) => EngineResponse::Error {
                code: "PROJECT_SCAN_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::SecretScanDiff { diff_text, path_hint } => {
            let findings = secret_scan::scan_unified_diff(&diff_text, &path_hint);
            EngineResponse::SecretScanDiffOk {
                result: "secret_scan_diff".to_string(),
                path_hint,
                findings,
            }
        }
        EngineRequest::AiEnhancementStatus { root } => match config::ai_enhancement_status(&root) {
            Ok(enabled) => EngineResponse::BoolStatusOk {
                result: "ai_enhancement_status".to_string(),
                enabled,
            },
            Err(error) => EngineResponse::Error {
                code: "AI_ENHANCEMENT_STATUS_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::AutoBackupStatus { root } => match config::auto_backup_status(&root) {
            Ok(enabled) => EngineResponse::BoolStatusOk {
                result: "auto_backup_status".to_string(),
                enabled,
            },
            Err(error) => EngineResponse::Error {
                code: "AUTO_BACKUP_STATUS_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::AnchorListMeta { root } => EngineResponse::AnchorListMetaOk {
            result: "anchor_list_meta".to_string(),
            meta: anchor_meta::list_anchor_meta(&root),
        },
        EngineRequest::AiEnhancementSet { root, enabled } => match config::set_ai_enhancement(&root, enabled) {
            Ok(stored) => EngineResponse::BoolStatusOk {
                result: "ai_enhancement_set".to_string(),
                enabled: stored,
            },
            Err(error) => EngineResponse::Error {
                code: "AI_ENHANCEMENT_SET_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::AutoBackupSet { root, enabled } => match config::set_auto_backup(&root, enabled) {
            Ok(stored) => EngineResponse::BoolStatusOk {
                result: "auto_backup_set".to_string(),
                enabled: stored,
            },
            Err(error) => EngineResponse::Error {
                code: "AUTO_BACKUP_SET_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::AnchorSetIntent {
            root,
            anchor_name,
            intent,
            connects,
            warning,
            aliases,
            description,
        } => match anchor_meta::set_anchor_intent(
            &root,
            &anchor_name,
            &intent,
            connects.as_deref(),
            warning.as_deref(),
            aliases.as_deref(),
            description.as_deref(),
        ) {
            Ok(entry) => EngineResponse::AnchorSetIntentOk {
                result: "anchor_set_intent".to_string(),
                anchor_name,
                entry,
            },
            Err(error) => EngineResponse::Error {
                code: "ANCHOR_SET_INTENT_FAILED".to_string(),
                message: error,
            },
        },
        EngineRequest::MemorySummaryRead { root, tool } => {
            let payload = match memory_state::load_payload(&root) {
                Ok(value) => value,
                Err(error) => {
                    return EngineResponse::Error {
                        code: "MEMORY_SUMMARY_READ_FAILED".to_string(),
                        message: error,
                    };
                }
            };
            let event = memory_audit::build_event(
                &root,
                MemoryAuditEventBuilder {
                    event: "memory_summary_read",
                    tool: tool.as_str(),
                    result: "success",
                },
            );
            if let Err(error) = memory_audit::append_event(&memory_audit::memory_audit_path(&root), event) {
                return EngineResponse::Error {
                    code: "MEMORY_AUDIT_APPEND_FAILED".to_string(),
                    message: error,
                };
            }
            EngineResponse::MemorySummaryReadOk {
                result: "memory_summary_read".to_string(),
                payload,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::handle;
    use crate::ipc::protocol::{EngineRequest, EngineResponse};
    use tempfile::TempDir;

    #[test]
    fn engine_info_returns_ok() {
        let response = handle(EngineRequest::EngineInfo);
        assert!(matches!(response, EngineResponse::Ok { .. }));
    }

    #[test]
    fn project_scan_matches_python_contract_fixture() {
        let root = TempDir::new().expect("temp root");
        write_fixture(root.path(), "main.py", "from services.api_client import fetch\nprint(fetch())\n");
        write_fixture(root.path(), "ui/views/panel.tsx", "import React from 'react';\nimport { api } from '../../services/api';\n");
        write_fixture(root.path(), "services/api_client.py", "import requests\nfrom core.guard import check\n");
        write_fixture(root.path(), "services/emoji_😀.py", "import pathlib\n");
        write_fixture(root.path(), "services/도우미.py", "import os\n");
        write_fixture(root.path(), "core/guard.py", "def check():\n    return True\n");
        write_fixture(root.path(), "scripts/migrate.rs", "fn main() {}\n");
        write_fixture(root.path(), "docs/guide.py", "print('ignored docs')\n");
        write_fixture(root.path(), "tests/test_app.py", "print('ignored tests')\n");
        write_fixture(root.path(), "node_modules/pkg/index.js", "console.log('ignored dependency')\n");
        write_fixture(root.path(), "target/debug/build.rs", "fn main() {}\n");
        write_fixture(root.path(), ".vibelign/project_map.json", "{}\n");
        write_fixture(root.path(), ".vibelign/anchor_meta.json", "{}\n");
        write_fixture(root.path(), ".vibelign/engine.sock", "ignored daemon artifact\n");
        write_fixture(root.path(), ".vibelign/app.py", "print('ignored vibelign source')\n");

        let response = handle(EngineRequest::ProjectScan { root: root.path().to_path_buf() });
        let value = serde_json::to_value(response).expect("json response");

        assert_eq!(value["status"], "ok");
        assert_eq!(value["result"], "project_scan");
        let files = value["files"].as_array().expect("files array");
        let paths: Vec<&str> = files.iter().filter_map(|item| item["path"].as_str()).collect();
        assert_eq!(paths, vec!["core/guard.py", "main.py", "scripts/migrate.rs", "services/api_client.py", "services/emoji_😀.py", "services/도우미.py", "ui/views/panel.tsx"]);
        assert_eq!(files[0]["category"], "core");
        assert_eq!(files[1]["category"], "entry");
        assert_eq!(files[2]["category"], "other");
        assert_eq!(files[3]["category"], "service");
        assert_eq!(files[4]["category"], "service");
        assert_eq!(files[5]["category"], "service");
        assert_eq!(files[6]["category"], "ui");
        assert_eq!(files[1]["imports"], serde_json::json!(["services.api_client"]));
        assert_eq!(files[3]["imports"], serde_json::json!(["requests", "core.guard"]));
        assert_eq!(files[4]["imports"], serde_json::json!(["pathlib"]));
        assert_eq!(files[5]["imports"], serde_json::json!(["os"]));
        assert_eq!(files[6]["imports"], serde_json::json!(["react", "../../services/api"]));
    }

    #[test]
    fn secret_scan_diff_handler_returns_findings_for_aws_fixture() {
        let manifest = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let fixtures = manifest.parent().expect("workspace root").join("tests/fixtures/secret_scan_diffs");
        let diff_text = std::fs::read_to_string(fixtures.join("02_high_confidence_aws.diff"))
            .expect("aws fixture exists");

        let response = handle(EngineRequest::SecretScanDiff {
            diff_text,
            path_hint: "config/.env".to_string(),
        });
        let value = serde_json::to_value(response).expect("json response");

        assert_eq!(value["status"], "ok");
        assert_eq!(value["result"], "secret_scan_diff");
        assert_eq!(value["path_hint"], "config/.env");
        let findings = value["findings"].as_array().expect("findings array");
        assert_eq!(findings.len(), 1);
        assert_eq!(findings[0]["rule_id"], "aws-access-key");
        assert_eq!(findings[0]["line_number"], 2);
        assert_eq!(findings[0]["path"], "config/.env");
    }

    fn write_fixture(root: &std::path::Path, rel: &str, content: &str) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, content).expect("write fixture");
    }
}
// === ANCHOR: HANDLER_END ===
