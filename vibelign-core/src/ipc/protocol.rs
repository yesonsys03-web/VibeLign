use crate::backup::checkpoint::{self, CheckpointCreateMetadata};
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
    CheckpointPrune {
        root: PathBuf,
        keep_latest: usize,
    },
}

#[derive(Debug, Serialize)]
pub struct ResponseCheckpoint {
    checkpoint_id: String,
    created_at: String,
    message: String,
    file_count: usize,
    total_size_bytes: u64,
    pinned: bool,
}

#[derive(Debug, Serialize)]
pub struct ResponseFile {
    relative_path: String,
    size: u64,
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
    },
    Error {
        code: String,
        message: String,
    },
}

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
        } => match checkpoint::restore(&root, &checkpoint_id) {
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
                },
                Err(error) => EngineResponse::Error {
                    code: "CHECKPOINT_PRUNE_FAILED".to_string(),
                    message: error,
                },
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{handle, EngineRequest, EngineResponse};

    #[test]
    fn engine_info_returns_ok() {
        let response = handle(EngineRequest::EngineInfo);
        assert!(matches!(response, EngineResponse::Ok { .. }));
    }
}
