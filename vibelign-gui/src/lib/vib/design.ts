import { invoke } from "@tauri-apps/api/core";
import type { StyleSpec } from "../design-preview/styles";

export interface DesignMockupResult { readonly html: string; readonly cached: boolean; }

export function generateDesignMockup(req: {
  projectDir: string; planPath: string; style: StyleSpec;
  feedback?: string; previousHtml?: string;
}): Promise<DesignMockupResult> {
  return invoke<DesignMockupResult>("generate_design_mockup", {
    projectDir: req.projectDir,
    planPath: req.planPath,
    style: req.style,
    feedback: req.feedback ?? null,
    previousHtml: req.previousHtml ?? null,
  });
}

export function saveDesignMockup(req: {
  projectDir: string; styleId: string; html: string;
}): Promise<string> {
  return invoke<string>("save_design_mockup", {
    projectDir: req.projectDir, styleId: req.styleId, html: req.html,
  });
}
