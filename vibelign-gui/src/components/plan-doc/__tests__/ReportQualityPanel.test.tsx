import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { parseReportAssistPayload, type ReportAssistPayload } from "../../../lib/vib/reportAssist";
import { parseReportQualityPayload } from "../../../lib/vib/reportQuality";
import { ReportQualityPanel, type ReportQualityPanelProceedPayload } from "../ReportQualityPanel";

afterEach(cleanup);

const okQuality = parseReportQualityPayload({
  status: "ok",
  score: 96,
  readiness: "ready",
  summary: "업무 보고서 기준을 충족합니다.",
  findings: [],
});

const warningQuality = parseReportQualityPayload({
  status: "warn",
  score: 72,
  readiness: "needs_review",
  summary: "근거와 다음 액션 보완이 필요합니다.",
  findings: [
    {
      code: "missing_evidence",
      severity: "warn",
      message: "정량 근거가 부족합니다.",
      source: "report_model",
      blocking: false,
      suggestion: "성과 수치를 추가하세요.",
    },
    {
      code: "future_backend_check",
      severity: "critical",
      message: "새 점검 항목입니다.",
      source: "future_source",
      blocking: false,
    },
  ],
});

const riskOnlyQuality = parseReportQualityPayload({
  status: "warn",
  score: 82,
  readiness: "needs_review",
  summary: "리스크와 대응 관점 보완이 필요합니다.",
  findings: [
    {
      code: "missing_risk",
      severity: "warn",
      message: "리스크 대응 관점이 부족합니다.",
      source: "report_model",
      blocking: false,
      suggestion: "리스크와 대응 방안을 추가하세요.",
    },
  ],
});

const blockingQuality = parseReportQualityPayload({
  status: "block",
  score: 8,
  readiness: "blocked",
  summary: "보고서로 만들 내용이 없습니다.",
  findings: [
    {
      code: "empty_content",
      severity: "block",
      message: "선택한 보고서 양식에 들어갈 섹션이 없습니다.",
      source: "template",
      blocking: true,
    },
  ],
});

const assistance = parseReportAssistPayload({
  status: "needs_user_input",
  suggestions: [
    {
      id: "evidence-1",
      finding_code: "missing_evidence",
      kind: "source_candidate",
      title: "성과 근거 추가",
      proposed_text: "파일럿 검증에서 재확인 건수가 31% 줄었습니다.",
      rationale: "중간 검증 섹션의 수치 근거입니다.",
      source_refs: [{ chunk_id: "chunk-7", heading_path: ["검증"], start_line: 842, end_line: 870 }],
      requires_user_confirmation: true,
    },
    {
      id: "risk-1",
      finding_code: "missing_risk",
      kind: "risk_candidate",
      title: "일정 리스크",
      proposed_text: "운영팀 확인이 늦어지면 배포 일정이 밀릴 수 있습니다.",
      rationale: "리스크 메모 기반 후보입니다.",
      source_refs: [],
      requires_user_confirmation: true,
    },
  ],
  questions: [
    {
      id: "owner-question",
      finding_code: "missing_next_action",
      kind: "user_question",
      title: "담당자 확인",
      proposed_text: "다음 액션 담당자는 누구인가요?",
      rationale: "원문에 담당자가 없습니다.",
      source_refs: [],
      requires_user_confirmation: true,
    },
  ],
});

const riskOnlyAssistance = parseReportAssistPayload({
  status: "needs_user_input",
  suggestions: [
    {
      id: "risk-only-1",
      finding_code: "missing_risk",
      kind: "risk_candidate",
      title: "리스크와 대응 보완",
      proposed_text: "사용자 전환 과정에서 기존 업무 방식과 충돌할 수 있어, 파일럿 그룹을 먼저 운영하고 피드백을 반영합니다.",
      rationale: "리스크와 대응 관점을 함께 보완합니다.",
      source_refs: [],
      requires_user_confirmation: true,
    },
  ],
  questions: [],
});

function renderPanel(
  onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>(),
  onRequestAssistance?: () => Promise<ReportAssistPayload>,
) {
  const onCancel = vi.fn();
  render(
    <ReportQualityPanel
      quality={warningQuality}
      assistance={assistance}
      sourceLabel="기획안"
      longSource={{ totalLines: 2048, analyzedSections: 5 }}
      onProceed={onProceed}
      onCancel={onCancel}
      onRequestAssistance={onRequestAssistance}
    />,
  );
  return { onCancel, onProceed };
}

function activateButtonWithKeyboard(button: HTMLElement, key: "Enter" | " ") {
  button.focus();
  fireEvent.keyDown(button, { key, code: key === " " ? "Space" : "Enter" });
}

test("shows ok status and direct next action", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  render(<ReportQualityPanel quality={okQuality} onProceed={onProceed} onCancel={() => {}} />);

  expect(screen.getByRole("heading", { name: "생성 가능" })).toBeInTheDocument();
  expect(screen.getByText("점수 96")).toBeInTheDocument();
  expect(screen.getByText("바로 생성할 수 있습니다.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "생성 계속" }));
  expect(onProceed).toHaveBeenCalledWith({
    mode: "normal",
    selectedSuggestions: [],
    rejectedSuggestionIds: [],
    questionAnswers: [],
  });
});

test("groups warnings and unknown categories while activating generate-anyway and cancel from keyboard", () => {
  const { onCancel, onProceed } = renderPanel();

  expect(screen.getByRole("heading", { name: "검토 필요" })).toBeInTheDocument();
  expect(screen.getByText("주의")).toBeInTheDocument();
  expect(screen.getByText("근거 누락")).toBeInTheDocument();
  expect(screen.getByText("기타 점검")).toBeInTheDocument();

  const generateAnyway = screen.getByRole("button", { name: "그래도 생성" });
  const cancel = screen.getByRole("button", { name: "취소" });
  generateAnyway.focus();
  expect(generateAnyway).toHaveFocus();
  cancel.focus();
  expect(cancel).toHaveFocus();

  activateButtonWithKeyboard(cancel, " ");
  expect(onCancel).toHaveBeenCalledTimes(1);
  activateButtonWithKeyboard(generateAnyway, "Enter");
  expect(onProceed).toHaveBeenCalledWith(expect.objectContaining({ mode: "generate_anyway" }));
});

test("blocks final generation when quality is blocking", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  render(<ReportQualityPanel quality={blockingQuality} onProceed={onProceed} onCancel={() => {}} />);

  expect(screen.getByRole("heading", { name: "생성 중단" })).toBeInTheDocument();
  expect(screen.getByText("중단")).toBeInTheDocument();
  expect(screen.getByText("문서 그대로 양식으로 바꾸거나 원문 섹션을 보완하세요.")).toBeInTheDocument();
  const generate = screen.getByRole("button", { name: "생성 불가" });
  expect(generate).toBeDisabled();
  fireEvent.click(generate);
  expect(onProceed).not.toHaveBeenCalled();
});

test("shows request-AI-help loading and error states", async () => {
  let rejectRequest: (error: Error) => void = () => {};
  const onRequestAssistance = vi.fn(
    () =>
      new Promise<ReportAssistPayload>((_resolve, reject) => {
        rejectRequest = reject;
      }),
  );

  render(
    <ReportQualityPanel
      quality={warningQuality}
      onProceed={() => {}}
      onCancel={() => {}}
      onRequestAssistance={onRequestAssistance}
    />,
  );

  activateButtonWithKeyboard(screen.getByRole("button", { name: "AI 보완 제안 요청" }), "Enter");
  expect(screen.getByText("관련 섹션을 분석하고 있습니다.")).toBeInTheDocument();
  rejectRequest(new Error("assist failed"));
  expect(await screen.findByRole("alert")).toHaveTextContent("보완 제안을 불러오지 못했습니다.");
  expect(onRequestAssistance).toHaveBeenCalledTimes(1);
});

test("requires confirmation before applying assistance", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  renderPanel(onProceed);

  const scorePreview = within(screen.getByRole("region", { name: "선택 후 재채점" }));
  expect(scorePreview.getAllByText("72점")).toHaveLength(2);
  expect(screen.getByText("예상 +14점")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "성과 근거 추가 수락" }));
  expect(scorePreview.getByText("86점")).toBeInTheDocument();
  expect(scorePreview.getByText("선택 반영 1개, 남은 점검 1개입니다.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "보완 반영해 생성" })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("일정 리스크 편집"), {
    target: { value: "운영팀 승인 지연 시 배포 일정을 재조정합니다." },
  });
  fireEvent.click(screen.getByRole("button", { name: "일정 리스크 수정 반영" }));
  fireEvent.click(screen.getByRole("button", { name: "일정 리스크 제외" }));
  fireEvent.click(screen.getByRole("button", { name: "보완 반영해 생성" }));

  expect(onProceed).toHaveBeenCalledWith({
    mode: "generate_anyway",
    selectedSuggestions: [
      {
        id: "evidence-1",
        text: "파일럿 검증에서 재확인 건수가 31% 줄었습니다.",
        status: "accepted",
      },
    ],
    rejectedSuggestionIds: ["risk-1"],
    questionAnswers: [],
  });
});

test("projects a full score after the last warning is covered", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  render(
    <ReportQualityPanel
      quality={riskOnlyQuality}
      assistance={riskOnlyAssistance}
      onProceed={onProceed}
      onCancel={() => {}}
    />,
  );

  const scorePreview = within(screen.getByRole("region", { name: "선택 후 재채점" }));
  expect(screen.getByText("예상 +18점")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "리스크와 대응 보완 수락" }));

  expect(scorePreview.getByText("100점")).toBeInTheDocument();
  expect(scorePreview.getByText("생성 가능")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "생성 계속" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "생성 계속" }));
  expect(onProceed).toHaveBeenCalledWith(
    expect.objectContaining({
      mode: "normal",
      selectedSuggestions: [
        {
          id: "risk-only-1",
          text: "사용자 전환 과정에서 기존 업무 방식과 충돌할 수 있어, 파일럿 그룹을 먼저 운영하고 피드백을 반영합니다.",
          status: "accepted",
        },
      ],
    }),
  );
});

test("captures answers for generated user questions", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  renderPanel(onProceed);

  fireEvent.change(screen.getByLabelText("담당자 확인 답변"), {
    target: { value: "운영팀 박민수 리드가 다음 주 수요일까지 확정합니다." },
  });
  fireEvent.click(screen.getByRole("button", { name: "담당자 확인 답변 저장" }));
  fireEvent.click(screen.getByRole("button", { name: "보완 반영해 생성" }));

  expect(onProceed).toHaveBeenCalledWith(
    expect.objectContaining({
      questionAnswers: [
        {
          suggestionId: "owner-question",
          answer: "운영팀 박민수 리드가 다음 주 수요일까지 확정합니다.",
        },
      ],
    }),
  );
});

test("shows visible feedback after saving a generated user-question answer", () => {
  renderPanel();

  fireEvent.change(screen.getByLabelText("담당자 확인 답변"), {
    target: { value: "운영팀 박민수 리드가 다음 주 수요일까지 확정합니다." },
  });
  fireEvent.click(screen.getByRole("button", { name: "담당자 확인 답변 저장" }));

  expect(screen.getByRole("status")).toHaveTextContent("답변이 저장되었습니다.");
  expect(screen.getByRole("button", { name: "담당자 확인 답변 다시 저장" })).toBeInTheDocument();
});

test("omits saved user-question answers after the question is excluded", () => {
  const onProceed = vi.fn<(payload: ReportQualityPanelProceedPayload) => void>();
  renderPanel(onProceed);

  fireEvent.change(screen.getByLabelText("담당자 확인 답변"), {
    target: { value: "운영팀 박민수 리드가 다음 주 수요일까지 확정합니다." },
  });
  fireEvent.click(screen.getByRole("button", { name: "담당자 확인 답변 저장" }));
  fireEvent.click(screen.getByRole("button", { name: "담당자 확인 제외" }));
  fireEvent.click(screen.getByRole("button", { name: "그래도 생성" }));

  expect(onProceed).toHaveBeenCalledWith(
    expect.objectContaining({
      rejectedSuggestionIds: ["owner-question"],
      questionAnswers: [],
    }),
  );
});

test("renders long-source line refs without narrow overflow styles", () => {
  renderPanel();

  expect(screen.getByText(/긴 문서는 관련 섹션 5개만 분석합니다/)).toBeInTheDocument();
  const chip = screen.getByText("기획안 842-870줄");
  expect(chip).toHaveStyle({ maxWidth: "100%", overflowWrap: "anywhere" });
  expect(screen.getByText("원문 근거 후보")).toBeInTheDocument();
  expect(screen.getByText("사용자 확인 필요")).toBeInTheDocument();
});
