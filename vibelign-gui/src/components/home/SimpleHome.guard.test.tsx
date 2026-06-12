// === ANCHOR: SIMPLEHOME_GUARD_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import type { GuardResult } from "../../lib/vib";
import { SimpleHome } from "./SimpleHome";

const GUARD_WITH_RAW_COMMAND = {
  status: "warn",
  verdict: "prepare",
  summary: "guard found 1 issue",
  recommendations: ["Run vib guard --strict and vib anchor --auto"],
  issues: [],
} satisfies GuardResult;

const PASSING_GUARD = {
  status: "pass",
  verdict: "pass",
  summary: "guard passed",
  recommendations: [],
  issues: [],
} satisfies GuardResult;

describe("SimpleHome guard copy", () => {
  afterEach(() => {
    cleanup();
  });

  test("humanizes_guard_recommendation_on_beginner_surface", () => {
    const openGuardDetails = vi.fn();

    render(
      <SimpleHome
        guardResult={GUARD_WITH_RAW_COMMAND}
        watchOn={false}
        watchError={null}
        hasCheckpoint={false}
        guardCheckPending={false}
        guardCheckError={null}
        onRetryWatch={() => undefined}
        onRunGuard={() => undefined}
        onShowAdvanced={() => undefined}
        onNavigateBackups={() => undefined}
        onOpenGuardDetails={openGuardDetails}
      />
    );

    // 3단 verdict(2026-06-12): 위생 누적(prepare)은 공포 어휘 대신 '준비' 프레임으로 안내
    expect(screen.getByText("다음 작업 전 준비 항목을 확인하세요")).toBeInTheDocument();
    expect(screen.getByText("앵커 설정 같은 준비를 마치면 다음 AI 작업이 더 안전해져요.")).toBeInTheDocument();
    expect(screen.queryByText(/vib guard/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/vib anchor/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "확인하기" }));
    expect(openGuardDetails).toHaveBeenCalledOnce();
  });

  test("hides_problem_details_button_when_guard_passes_without_issues", () => {
    render(
      <SimpleHome
        guardResult={PASSING_GUARD}
        watchOn={false}
        watchError={null}
        hasCheckpoint={false}
        guardCheckPending={false}
        guardCheckError={null}
        onRetryWatch={() => undefined}
        onRunGuard={() => undefined}
        onShowAdvanced={() => undefined}
        onNavigateBackups={() => undefined}
        onOpenGuardDetails={() => undefined}
      />
    );

    expect(screen.getByText("안전장치가 켜져 있어요")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "문제 확인하기" })).not.toBeInTheDocument();
  });

  test("shows_scope_report_with_out_of_scope_paths", () => {
    render(
      <SimpleHome
        guardResult={PASSING_GUARD}
        watchOn={false}
        watchError={null}
        hasCheckpoint={false}
        guardCheckPending={false}
        guardCheckError={null}
        scopeReport={{ inScope: 2, outOfScope: ["src/pages/Settings.tsx"] }}
        onRetryWatch={() => undefined}
        onRunGuard={() => undefined}
        onShowAdvanced={() => undefined}
        onNavigateBackups={() => undefined}
        onOpenGuardDetails={() => undefined}
      />
    );

    expect(screen.getByText(/약속 범위 안 변경 2건/)).toBeInTheDocument();
    expect(screen.getByText(/범위 밖 1건/)).toBeInTheDocument();
    expect(screen.getByText("src/pages/Settings.tsx")).toBeInTheDocument();
    // 판정 어조 금지 — 안내 문구 확인 (spec §6)
    expect(screen.getByText(/의도한 작업인지 확인해보세요/)).toBeInTheDocument();
  });

  test("hides_scope_report_when_absent", () => {
    render(
      <SimpleHome
        guardResult={PASSING_GUARD}
        watchOn={false}
        watchError={null}
        hasCheckpoint={false}
        guardCheckPending={false}
        guardCheckError={null}
        scopeReport={null}
        onRetryWatch={() => undefined}
        onRunGuard={() => undefined}
        onShowAdvanced={() => undefined}
        onNavigateBackups={() => undefined}
        onOpenGuardDetails={() => undefined}
      />
    );

    expect(screen.queryByText(/약속 범위/)).not.toBeInTheDocument();
  });
});
// === ANCHOR: SIMPLEHOME_GUARD_TEST_END ===
