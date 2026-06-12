import { describe, expect, it } from "vitest";
import { isFixable, isTerminal, kindLabel, phaseLabel, statusView } from "./runView";

describe("kindLabel", () => {
  it("maps each project kind to a Korean label", () => {
    expect(kindLabel("web")).toBe("웹앱");
    expect(kindLabel("electron")).toContain("Electron");
    expect(kindLabel("unknown")).toBe("프로그램");
  });
});

describe("statusView", () => {
  it("marks installing/running as in-progress tones", () => {
    expect(statusView("installing").tone).toBe("info");
    expect(statusView("running").tone).toBe("running");
  });

  it("marks done as success and failed as error", () => {
    expect(statusView("done").tone).toBe("success");
    expect(statusView("failed").tone).toBe("error");
  });

  it("marks stopped as idle (user intent, not failure)", () => {
    expect(statusView("stopped").tone).toBe("idle");
  });

  it("returns non-empty copy for every status", () => {
    for (const s of ["installing", "running", "done", "failed", "stopped"] as const) {
      expect(statusView(s).text.length).toBeGreaterThan(0);
    }
  });
});

describe("phaseLabel", () => {
  it("labels install and run phases", () => {
    expect(phaseLabel("install")).toBe("설치");
    expect(phaseLabel("run")).toBe("실행");
  });
});

describe("isTerminal", () => {
  it("is true only for done/failed/stopped", () => {
    expect(isTerminal("done")).toBe(true);
    expect(isTerminal("failed")).toBe(true);
    expect(isTerminal("stopped")).toBe(true);
    expect(isTerminal("installing")).toBe(false);
    expect(isTerminal("running")).toBe(false);
  });
});

describe("isFixable", () => {
  it("is true only for failed (the error→작업방 handoff target, M3b)", () => {
    expect(isFixable("failed")).toBe(true);
    expect(isFixable("stopped")).toBe(false);
    expect(isFixable("done")).toBe(false);
    expect(isFixable("running")).toBe(false);
  });
});
