// === ANCHOR: ERRORLOGS_START ===
import { invoke } from "@tauri-apps/api/core";

import type { ClearErrorLogsResult, ErrorLogEntry } from "./types";

/** `.vibelign/logs/{cli,gui}-error-*.jsonl` 통합 에러 로그를 ts 내림차순으로 반환. */
// === ANCHOR: ERRORLOGS_READERRORLOGS_START ===
export async function readErrorLogs(cwd: string, limit = 200): Promise<ErrorLogEntry[]> {
  return invoke<ErrorLogEntry[]>("read_error_logs", { root: cwd, limit });
}
// === ANCHOR: ERRORLOGS_READERRORLOGS_END ===

/** 에러 로그 파일 (`{cli,gui}-error-*.jsonl`) 만 삭제. lock/다른 로그 보존. */
// === ANCHOR: ERRORLOGS_CLEARERRORLOGS_START ===
export async function clearErrorLogs(cwd: string): Promise<ClearErrorLogsResult> {
  return invoke<ClearErrorLogsResult>("clear_error_logs", { root: cwd });
}
// === ANCHOR: ERRORLOGS_CLEARERRORLOGS_END ===
// === ANCHOR: ERRORLOGS_END ===
