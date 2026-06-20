import { invoke } from "@tauri-apps/api/core";
import type { EmitPayload } from "./reportModel";

export const REPORT_RENDER_PAYLOAD_PATH_ENV = "VIBELIGN_REPORT_RENDER_PAYLOAD_PATH";

export async function writeReportRenderPayload(cwd: string, payload: EmitPayload): Promise<string> {
  return writeReportJsonPayload(cwd, payload);
}

export async function writeReportJsonPayload(cwd: string, payload: unknown): Promise<string> {
  return invoke<string>("write_report_render_payload", {
    root: cwd,
    payloadJson: JSON.stringify(payload),
  });
}

export async function removeReportRenderPayload(cwd: string, path: string): Promise<void> {
  await invoke<void>("remove_report_render_payload", { root: cwd, path });
}
