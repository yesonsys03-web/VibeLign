import { describe, expect, test } from "vitest";
import { TOOL_INSTALLERS, getInstaller, shouldGuideManual } from "../installerRegistry";

describe("installerRegistry", () => {
  test("opencode 는 무키 추천 기본", () => {
    const t = getInstaller("opencode")!;
    expect(t.auth).toBe("none");
    expect(t.recommendedForBeginner).toBe(true);
  });
  test("codex·agy 는 login 필요", () => {
    expect(getInstaller("codex")!.auth).toBe("login");
    expect(getInstaller("agy")!.auth).toBe("login");
  });
  test("미등록 도구는 undefined", () => {
    expect(getInstaller("nope")).toBeUndefined();
  });
  test("설치 실패/미설치면 수동 가이드", () => {
    expect(shouldGuideManual({ installed: false, exitCode: 1 })).toBe(true);
    expect(shouldGuideManual({ installed: false, exitCode: null })).toBe(true); // 미지원 OS
    expect(shouldGuideManual({ installed: true, exitCode: 0 })).toBe(false);
  });
});
