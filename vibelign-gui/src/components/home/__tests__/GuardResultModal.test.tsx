// === ANCHOR: GUARDRESULTMODAL_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import type { GuardResult } from "../../../lib/vib";
import { GuardResultModal } from "../GuardResultModal";

const WARN_GUARD = {
  status: "warn",
  verdict: "prepare",
  summary: "안전 검사에서 확인할 항목을 찾았어요.",
  recommendations: ["권장 조치 1"],
  issues: [{ found: "문제 파일", next_step: "다음 행동" }],
} satisfies GuardResult;

describe("GuardResultModal", () => {
  afterEach(() => {
    cleanup();
  });

  test("renders_guard_summary_recommendations_and_issues", () => {
    render(<GuardResultModal guardResult={WARN_GUARD} onClose={() => undefined} />);

    expect(screen.getByText("GUARD 결과")).toBeInTheDocument();
    // 배지는 사람용 3단 verdict 라벨(2026-06-12) — 기계 status(WARN)를 그대로 노출하지 않는다
    expect(screen.getByText("준비 필요")).toBeInTheDocument();
    expect(screen.getByText("안전 검사에서 확인할 항목을 찾았어요.")).toBeInTheDocument();
    expect(screen.getByText("권장 액션")).toBeInTheDocument();
    expect(screen.getByText("권장 조치 1")).toBeInTheDocument();
    expect(screen.getByText("전체 이슈 (1개)")).toBeInTheDocument();
    expect(screen.getByText("문제 파일")).toBeInTheDocument();
    expect(screen.getByText("→ 다음 행동")).toBeInTheDocument();
  });

  test("closes_from_overlay_header_and_footer_actions", () => {
    const close = vi.fn();
    render(<GuardResultModal guardResult={WARN_GUARD} onClose={close} />);

    fireEvent.click(screen.getByLabelText("모달 닫기"));
    fireEvent.click(screen.getByRole("button", { name: "닫기" }));
    fireEvent.click(screen.getByRole("button", { name: "닫고 다시 실행" }));

    expect(close).toHaveBeenCalledTimes(3);
  });

  test("offers_doctor_handoff_when_guard_has_issues", () => {
    const openDoctor = vi.fn();
    const close = vi.fn();

    render(<GuardResultModal guardResult={WARN_GUARD} onClose={close} onOpenDoctor={openDoctor} />);

    fireEvent.click(screen.getByRole("button", { name: "Doctor로 해결안 만들기" }));

    expect(close).toHaveBeenCalledOnce();
    expect(openDoctor).toHaveBeenCalledOnce();
  });
});
// === ANCHOR: GUARDRESULTMODAL_TEST_END ===
