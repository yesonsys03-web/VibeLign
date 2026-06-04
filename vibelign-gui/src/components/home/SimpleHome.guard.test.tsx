import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import type { GuardResult } from "../../lib/vib";
import { SimpleHome } from "./SimpleHome";

const GUARD_WITH_RAW_COMMAND = {
  status: "warn",
  summary: "guard found 1 issue",
  recommendations: ["Run vib guard --strict and vib anchor --auto"],
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
        onRetryWatch={() => undefined}
        onShowAdvanced={() => undefined}
        onNavigateBackups={() => undefined}
        onOpenGuardDetails={openGuardDetails}
      />
    );

    expect(screen.getByText("안전 검사 결과를 확인하세요")).toBeInTheDocument();
    expect(screen.getByText("문제가 있는 파일과 다음 행동을 쉬운 목록으로 확인할 수 있어요.")).toBeInTheDocument();
    expect(screen.queryByText(/vib guard/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/vib anchor/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "확인하기" }));
    expect(openGuardDetails).toHaveBeenCalledOnce();
  });
});
