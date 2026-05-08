// === ANCHOR: ERROR_REPORTER_START ===
import { invoke } from "@tauri-apps/api/core";

type GuiErrorSource = "window.onerror" | "unhandledrejection" | "react.errorBoundary";

export interface GuiErrorPayload {
  source: GuiErrorSource;
  message: string;
  stack?: string;
  url?: string;
  componentStack?: string;
}

let activeProjectDir: string | null = null;
let installed = false;

export function setErrorReporterProjectDir(projectDir: string | null): void {
  activeProjectDir = projectDir;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return String(error);
}

function errorStack(error: unknown): string | undefined {
  if (error instanceof Error) return error.stack;
  return undefined;
}

function enqueueGuiError(payload: GuiErrorPayload): void {
  if (!activeProjectDir) return;
  invoke<void>("record_gui_error", {
    projectDir: activeProjectDir,
    payload,
  }).catch((error: unknown) => {
    void error;
  });
}

export function installGuiErrorReporter(): void {
  if (installed) return;
  installed = true;

  window.addEventListener("error", (event) => {
    enqueueGuiError({
      source: "window.onerror",
      message: event.message || errorMessage(event.error),
      stack: errorStack(event.error),
      url: event.filename || window.location.href,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    enqueueGuiError({
      source: "unhandledrejection",
      message: errorMessage(event.reason),
      stack: errorStack(event.reason),
      url: window.location.href,
    });
  });
}

export function reportReactError(error: Error, componentStack?: string): void {
  enqueueGuiError({
    source: "react.errorBoundary",
    message: error.message,
    stack: error.stack,
    componentStack,
    url: window.location.href,
  });
}
// === ANCHOR: ERROR_REPORTER_END ===
