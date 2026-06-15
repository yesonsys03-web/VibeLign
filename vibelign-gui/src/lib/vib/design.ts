// === ANCHOR: DESIGN_START ===
import { invoke } from "@tauri-apps/api/core";
import type { StyleSpec } from "../design-preview/styles";

export interface DesignMockupResult { readonly html: string; readonly cached: boolean; }

// === ANCHOR: DESIGN_GENERATEDESIGNMOCKUP_START ===
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
// === ANCHOR: DESIGN_GENERATEDESIGNMOCKUP_END ===

// === ANCHOR: DESIGN_SAVEDESIGNMOCKUP_START ===
export function saveDesignMockup(req: {
  projectDir: string; styleId: string; html: string;
}): Promise<string> {
  return invoke<string>("save_design_mockup", {
    projectDir: req.projectDir, styleId: req.styleId, html: req.html,
  });
}
// === ANCHOR: DESIGN_SAVEDESIGNMOCKUP_END ===

// === ANCHOR: DESIGN_SYNTHESIZESTYLE_START ===
export function synthesizeStyle(req: {
  projectDir: string; planPath: string; description: string; baseStyle?: StyleSpec;
}): Promise<StyleSpec> {
  return invoke<StyleSpec>("synthesize_style", {
    projectDir: req.projectDir, planPath: req.planPath,
    description: req.description, baseStyle: req.baseStyle ?? null,
  });
}
// === ANCHOR: DESIGN_SYNTHESIZESTYLE_END ===
// === ANCHOR: DESIGN_SAVECUSTOMSTYLE_START ===
export function saveCustomStyle(req: { projectDir: string; style: StyleSpec }): Promise<void> {
  return invoke<void>("save_custom_style", { projectDir: req.projectDir, style: req.style });
}
// === ANCHOR: DESIGN_SAVECUSTOMSTYLE_END ===
// === ANCHOR: DESIGN_LISTCUSTOMSTYLES_START ===
export function listCustomStyles(projectDir: string): Promise<StyleSpec[]> {
  return invoke<StyleSpec[]>("list_custom_styles", { projectDir });
}
// === ANCHOR: DESIGN_LISTCUSTOMSTYLES_END ===
// === ANCHOR: DESIGN_DELETECUSTOMSTYLE_START ===
export function deleteCustomStyle(req: { projectDir: string; styleId: string }): Promise<void> {
  return invoke<void>("delete_custom_style", { projectDir: req.projectDir, styleId: req.styleId });
}
// === ANCHOR: DESIGN_DELETECUSTOMSTYLE_END ===
// === ANCHOR: DESIGN_END ===
