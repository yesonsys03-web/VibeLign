import { describe, expect, test } from "vitest";

import {
  acceptedReportAssistSuggestionIds,
  createReportAssistSuggestionState,
  editedReportAssistSuggestionIds,
  parseReportAssistPayload,
  reportAssistSuggestionKindLabel,
  reportAssistSuggestionStateUpdate,
  selectedReportAssistSuggestions,
} from "../reportAssist";

describe("report assist parser", () => {
  test("normalizes unknown status, kind, and malformed source refs without throwing", () => {
    const assistance = parseReportAssistPayload({
      schema_version: "report-assist-v1",
      status: "waiting",
      suggestions: [
        {
          id: "s1",
          finding_code: "missing_evidence",
          kind: "future_kind",
          title: "Backend suggestion",
          proposed_text: "Draft",
          rationale: "Because",
          source_refs: [
            "broken",
            {
              chunk_id: "chunk-9999",
              heading_path: ["Root", 42],
              start_line: -1,
              end_line: 999999,
            },
          ],
          requires_user_confirmation: false,
        },
      ],
      questions: "bad",
      applied_suggestion_ids: ["s1", 7],
    });

    expect(assistance.status).toBe("needs_user_input");
    expect(assistance.rawStatus).toBe("waiting");
    expect(assistance.suggestions[0]).toMatchObject({
      id: "s1",
      kind: "user_question",
      rawKind: "future_kind",
      kindLabel: "사용자 확인 필요",
      requires_user_confirmation: true,
    });
    expect(assistance.suggestions[0].source_refs).toEqual([
      {
        chunk_id: "unknown-source",
        heading_path: [],
        warning: "출처 범위를 확인할 수 없습니다.",
      },
      {
        chunk_id: "chunk-9999",
        heading_path: ["Root"],
        warning: "출처 줄 범위가 올바르지 않습니다.",
      },
    ]);
    expect(assistance.applied_suggestion_ids).toEqual(["s1"]);
  });

  test("keeps assistance suggestions user-confirmed", () => {
    const assistance = parseReportAssistPayload({
      status: "ready",
      suggestions: [
        {
          id: "accept-me",
          finding_code: "missing_evidence",
          kind: "source_candidate",
          title: "근거 보완",
          proposed_text: "파일럿 재확인 건수가 31% 감소했습니다.",
          rationale: "source-backed",
          source_refs: [],
          requires_user_confirmation: true,
        },
        {
          id: "edit-me",
          finding_code: "missing_next_action",
          kind: "next_action_candidate",
          title: "다음 액션",
          proposed_text: "다음 주에 공유합니다.",
          rationale: "source-backed",
          source_refs: [],
          requires_user_confirmation: true,
        },
        {
          id: "reject-me",
          finding_code: "missing_risk",
          kind: "risk_candidate",
          title: "리스크",
          proposed_text: "일정 지연 가능성이 있습니다.",
          rationale: "source-backed",
          source_refs: [],
          requires_user_confirmation: true,
        },
      ],
    });

    const accepted = reportAssistSuggestionStateUpdate(createReportAssistSuggestionState(), {
      type: "accept",
      suggestionId: "accept-me",
      text: "파일럿 재확인 건수가 31% 감소했습니다.",
    });
    const edited = reportAssistSuggestionStateUpdate(accepted, {
      type: "edit",
      suggestionId: "edit-me",
      text: "다음 주 수요일까지 운영팀이 기준표를 공유합니다.",
    });
    const rejected = reportAssistSuggestionStateUpdate(edited, {
      type: "reject",
      suggestionId: "reject-me",
    });

    expect(acceptedReportAssistSuggestionIds(rejected)).toEqual(["accept-me"]);
    expect(editedReportAssistSuggestionIds(rejected)).toEqual(["edit-me"]);
    expect(rejected.rejectedIds).toEqual(["reject-me"]);
    expect(selectedReportAssistSuggestions(assistance, rejected)).toEqual([
      {
        id: "accept-me",
        text: "파일럿 재확인 건수가 31% 감소했습니다.",
        status: "accepted",
      },
      {
        id: "edit-me",
        text: "다음 주 수요일까지 운영팀이 기준표를 공유합니다.",
        status: "edited",
      },
    ]);
  });

  test("removes an accepted suggestion when it is rejected later", () => {
    const assistance = parseReportAssistPayload({
      status: "ready",
      suggestions: [
        {
          id: "accept-then-reject",
          finding_code: "missing_evidence",
          kind: "source_candidate",
          title: "근거 보완",
          proposed_text: "파일럿 재확인 건수가 31% 감소했습니다.",
          rationale: "source-backed",
          source_refs: [],
          requires_user_confirmation: true,
        },
      ],
    });

    const accepted = reportAssistSuggestionStateUpdate(createReportAssistSuggestionState(), {
      type: "accept",
      suggestionId: "accept-then-reject",
      text: "파일럿 재확인 건수가 31% 감소했습니다.",
    });
    const rejected = reportAssistSuggestionStateUpdate(accepted, {
      type: "reject",
      suggestionId: "accept-then-reject",
    });

    expect(acceptedReportAssistSuggestionIds(rejected)).toEqual([]);
    expect(editedReportAssistSuggestionIds(rejected)).toEqual([]);
    expect(rejected.rejectedIds).toEqual(["accept-then-reject"]);
    expect(selectedReportAssistSuggestions(assistance, rejected)).toEqual([]);
  });

  test("removes an edited suggestion when it is rejected later", () => {
    const assistance = parseReportAssistPayload({
      status: "ready",
      suggestions: [
        {
          id: "edit-then-reject",
          finding_code: "missing_next_action",
          kind: "next_action_candidate",
          title: "다음 액션",
          proposed_text: "다음 주에 공유합니다.",
          rationale: "source-backed",
          source_refs: [],
          requires_user_confirmation: true,
        },
      ],
    });

    const edited = reportAssistSuggestionStateUpdate(createReportAssistSuggestionState(), {
      type: "edit",
      suggestionId: "edit-then-reject",
      text: "다음 주 수요일까지 운영팀이 기준표를 공유합니다.",
    });
    const rejected = reportAssistSuggestionStateUpdate(edited, {
      type: "reject",
      suggestionId: "edit-then-reject",
    });

    expect(acceptedReportAssistSuggestionIds(rejected)).toEqual([]);
    expect(editedReportAssistSuggestionIds(rejected)).toEqual([]);
    expect(rejected.rejectedIds).toEqual(["edit-then-reject"]);
    expect(selectedReportAssistSuggestions(assistance, rejected)).toEqual([]);
  });

  test("uses stable suggestion kind labels", () => {
    expect(reportAssistSuggestionKindLabel("draft_text")).toBe("초안 문구");
    expect(reportAssistSuggestionKindLabel("source_candidate")).toBe("원문 근거 후보");
  });
});
