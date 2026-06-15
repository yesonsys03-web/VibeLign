// === ANCHOR: WORKROOMCTA_TEST_START ===
import { describe, expect, test } from "vitest";
import { runCtaVisible } from "../workRoomCta";

describe("runCtaVisible", () => {
  test("finished + pass → 표시", () => {
    expect(runCtaVisible("finished", "pass")).toBe(true);
  });

  test("finished + prepare → 표시 (prepare 도 safe)", () => {
    expect(runCtaVisible("finished", "prepare")).toBe(true);
  });

  test("finished + stop → 숨김 (안전 우선)", () => {
    expect(runCtaVisible("finished", "stop")).toBe(false);
  });

  test("finished + verdict 없음(null/undefined) → 숨김", () => {
    expect(runCtaVisible("finished", null)).toBe(false);
    expect(runCtaVisible("finished", undefined)).toBe(false);
  });

  test("아직 안 끝남(running/idle/verifying) → 숨김", () => {
    expect(runCtaVisible("running", "pass")).toBe(false);
    expect(runCtaVisible("idle", "pass")).toBe(false);
    expect(runCtaVisible("verifying", "pass")).toBe(false);
  });
});
// === ANCHOR: WORKROOMCTA_TEST_END ===
