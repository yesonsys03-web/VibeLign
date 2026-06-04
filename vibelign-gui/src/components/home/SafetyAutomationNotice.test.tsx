import { describe, expect, test } from "vitest";

import { humanizeAutomationError } from "./SafetyAutomationNotice";

describe("humanizeAutomationError", () => {
  test("returns_no_notice_when_error_is_empty", () => {
    expect(humanizeAutomationError(null)).toBeNull();
    expect(humanizeAutomationError("   ")).toBeNull();
  });

  test("explains_permission_denied_without_raw_error_text", () => {
    const copy = humanizeAutomationError("spawn error: permission denied");

    expect(copy?.title).toBe("폴더 권한을 확인해야 해요");
    expect(copy?.detail).toBe("파일 변경 감시에 필요한 권한이 부족해요. 폴더 접근 권한을 확인한 뒤 다시 시도하세요.");
    expect(copy?.detail).not.toMatch(/permission denied/i);
  });

  test("explains_missing_watch_command_without_raw_error_text", () => {
    const copy = humanizeAutomationError("watch command not found");

    expect(copy?.title).toBe("감시 도구를 찾지 못했어요");
    expect(copy?.detail).toBe("파일 변경 감시를 시작하는 도구가 준비되지 않았어요. VibeLign 시작 설정을 다시 확인하세요.");
    expect(copy?.detail).not.toMatch(/command not found/i);
  });

  test("explains_timeout_without_raw_error_text", () => {
    const copy = humanizeAutomationError("watch start timeout after 30s");

    expect(copy?.title).toBe("감시 시작이 오래 걸리고 있어요");
    expect(copy?.detail).toBe("프로젝트가 크거나 시스템이 바빠서 자동 감시가 제때 시작되지 않았어요. 잠시 후 다시 시도하세요.");
    expect(copy?.detail).not.toMatch(/timeout/i);
  });

  test("falls_back_to_generic_automation_copy", () => {
    const copy = humanizeAutomationError("unhandled backend exception");

    expect(copy?.title).toBe("자동 안전장치 일부가 꺼져 있어요");
    expect(copy?.detail).toBe("파일 변경 감시를 시작하지 못했어요. 프로젝트 상태 확인은 계속 사용할 수 있어요.");
    expect(copy?.detail).not.toMatch(/backend/i);
  });
});
