// === ANCHOR: DOCTOR_FLOW_TEST_START ===
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import Doctor from "../Doctor";
import type { DoctorLaunchIntent } from "../doctorFlow";

const mocks = vi.hoisted(() => ({
  doctorJsonMock: vi.fn<(...args: readonly [string, boolean?]) => Promise<unknown>>(),
  doctorPlanJsonMock: vi.fn<(...args: readonly [string]) => Promise<unknown>>(),
  getAiEnhancementMock: vi.fn<(...args: readonly [string]) => Promise<boolean>>(),
  doctorApplyMock: vi.fn<(...args: readonly [string, Record<string, string>?]) => Promise<unknown>>(),
  buildGuiAiEnvMock: vi.fn<(...args: readonly [Record<string, string> | undefined, string | null | undefined]) => Record<string, string>>(),
  anchorAutoIntentJsonMock: vi.fn(),
}));

vi.mock("../../lib/vib", async () => {
  const actual = await vi.importActual<typeof import("../../lib/vib")>("../../lib/vib");
  return {
    ...actual,
    doctorJson: mocks.doctorJsonMock,
    doctorPlanJson: mocks.doctorPlanJsonMock,
    getAiEnhancement: mocks.getAiEnhancementMock,
    doctorApply: mocks.doctorApplyMock,
    buildGuiAiEnv: mocks.buildGuiAiEnvMock,
    anchorAutoIntentJson: mocks.anchorAutoIntentJsonMock,
  };
});

describe("Doctor handoff flow", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mocks.doctorJsonMock.mockReset();
    mocks.doctorPlanJsonMock.mockReset();
    mocks.getAiEnhancementMock.mockReset();
    mocks.doctorApplyMock.mockReset();
    mocks.buildGuiAiEnvMock.mockReset();
    mocks.anchorAutoIntentJsonMock.mockReset();
    mocks.doctorJsonMock.mockResolvedValue({
      project_score: 72,
      status: "Caution",
      anchor_coverage: 80,
      issues: [],
      recommended_actions: [],
    });
    mocks.doctorPlanJsonMock.mockResolvedValue({
      actions: [{ action_type: "fix_anchor", description: "앵커 intent 보강" }],
      source_score: 72,
      warnings: [],
    });
    mocks.getAiEnhancementMock.mockResolvedValue(false);
    mocks.buildGuiAiEnvMock.mockReturnValue({});
  });

  test("opens_plan_with_ai_enhancement_selected_when_launched_with_api_key", async () => {
    const launchIntent: DoctorLaunchIntent = {
      targetView: "plan",
      applyMode: "ai",
    };

    render(<Doctor projectDir="/tmp/demo" launchIntent={launchIntent} apiKey="sk-test" providerKeys={{}} />);

    expect(await screen.findByText("실행 예정 1개 항목")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "AI 보강" })).toBeChecked();
  });

  test("opens_plan_without_ai_enhancement_when_launched_without_api_key", async () => {
    const launchIntent: DoctorLaunchIntent = {
      targetView: "plan",
      applyMode: "local",
    };

    render(<Doctor projectDir="/tmp/demo" launchIntent={launchIntent} providerKeys={{}} />);

    expect(await screen.findByText("실행 예정 1개 항목")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "AI 보강" })).not.toBeChecked();
  });

  test("updates_ai_enhancement_default_when_launch_intent_changes_after_key_load", async () => {
    const localIntent: DoctorLaunchIntent = {
      targetView: "plan",
      applyMode: "local",
    };
    const aiIntent: DoctorLaunchIntent = {
      targetView: "plan",
      applyMode: "ai",
    };

    const { rerender } = render(<Doctor projectDir="/tmp/demo" launchIntent={localIntent} providerKeys={{}} />);

    expect(await screen.findByText("실행 예정 1개 항목")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "AI 보강" })).not.toBeChecked();

    rerender(<Doctor projectDir="/tmp/demo" launchIntent={aiIntent} apiKey="sk-test" providerKeys={{}} />);

    expect(screen.getByRole("checkbox", { name: "AI 보강" })).toBeChecked();
  });
});
// === ANCHOR: DOCTOR_FLOW_TEST_END ===
