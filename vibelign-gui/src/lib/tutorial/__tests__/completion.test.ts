import { describe, it, expect } from "vitest";
import { isStepComplete } from "../completion";
import type { GuideSignals } from "../../nav/guide";

const base: GuideSignals = {
  hasPlanDoc: false,
  planningPending: false,
  hasCheckpoint: false,
  changedFileCount: null,
  guardStatus: null,
  runVerified: false,
};

describe("isStepComplete", () => {
  it("planResponded: 기획안이 생기면 완료", () => {
    expect(isStepComplete("planResponded", base)).toBe(false);
    expect(isStepComplete("planResponded", { ...base, hasPlanDoc: true })).toBe(true);
  });

  it("changedFiles: 변경 파일이 1개 이상이면 완료", () => {
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: 0 })).toBe(false);
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: null })).toBe(false);
    expect(isStepComplete("changedFiles", { ...base, changedFileCount: 2 })).toBe(true);
  });

  it("checkpoint: 체크포인트가 있으면 완료", () => {
    expect(isStepComplete("checkpoint", { ...base, hasCheckpoint: true })).toBe(true);
  });

  it("guardChecked: guard 결과가 나오면(ok든 issue든) 완료", () => {
    expect(isStepComplete("guardChecked", base)).toBe(false);
    expect(isStepComplete("guardChecked", { ...base, guardStatus: "ok" })).toBe(true);
    expect(isStepComplete("guardChecked", { ...base, guardStatus: "issue" })).toBe(true);
  });

  it("runVerified: 실행 검증되면 완료", () => {
    expect(isStepComplete("runVerified", { ...base, runVerified: true })).toBe(true);
  });

  it("copy/manual: 신호로는 절대 자동 완료되지 않는다", () => {
    const full: GuideSignals = {
      hasPlanDoc: true, planningPending: false, hasCheckpoint: true,
      changedFileCount: 5, guardStatus: "ok", runVerified: true,
    };
    expect(isStepComplete("copy", full)).toBe(false);
    expect(isStepComplete("manual", full)).toBe(false);
  });
});
