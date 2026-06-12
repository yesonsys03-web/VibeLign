import { describe, expect, it } from "vitest";
import { collectErrorTail, isFixable, isTerminal, kindLabel, phaseLabel, statusView } from "./runView";

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

describe("collectErrorTail", () => {
  it("includes both stdout and stderr (vite/next print errors to stdout)", () => {
    const out = collectErrorTail([
      { stream: "stdout", text: "SyntaxError: Unexpected token" },
      { stream: "stderr", text: "exit code 1" },
    ]);
    expect(out).toContain("SyntaxError: Unexpected token");
    expect(out).toContain("exit code 1");
  });

  it("marks stderr lines with a prefix", () => {
    expect(collectErrorTail([{ stream: "stderr", text: "boom" }])).toBe("! boom");
    expect(collectErrorTail([{ stream: "stdout", text: "info" }])).toBe("info");
  });

  it("keeps only the last `max` lines", () => {
    const many = Array.from({ length: 100 }, (_, i) => ({ stream: "stdout" as const, text: `line ${i}` }));
    const out = collectErrorTail(many, 5);
    expect(out.split("\n")).toHaveLength(5);
    expect(out).toContain("line 99");
    expect(out).not.toContain("line 94");
  });

  it("returns empty string for no lines", () => {
    expect(collectErrorTail([])).toBe("");
  });
});
