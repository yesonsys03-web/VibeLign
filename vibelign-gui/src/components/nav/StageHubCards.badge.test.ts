import { describe, expect, it } from "vitest";
import { badgeText, type PlanningSummary } from "./StageHubCards";

const summary = (over: Partial<PlanningSummary>): PlanningSummary => ({
  total: 0,
  saved: 0,
  draft: 0,
  stale: 0,
  ...over,
});

describe("badgeText — planning (다중 기획안)", () => {
  it("'기획안'은 저장된 plan doc(saved)만 — 미저장 초안은 '초안'으로(탭과 일치)", () => {
    // 핵심 회귀: 미저장 4개를 '기획안 4개'로 부르면 기획안 탭(빈 목록)과 어긋난다.
    expect(badgeText("planning", "active", 0, summary({ total: 4, draft: 4 }))).toBe("기획 초안 4개");
  });

  it("저장본이 있으면 '기획안 N개'", () => {
    expect(badgeText("planning", "done", 0, summary({ total: 1, saved: 1 }))).toBe("기획안 1개");
  });

  it("저장본 + 초안 + 갱신필요를 함께 표기", () => {
    expect(badgeText("planning", "done", 0, summary({ total: 5, saved: 3, draft: 2, stale: 1 }))).toBe(
      "기획안 3개 · 1 갱신필요 · 초안 2개",
    );
  });

  it("저장본·초안 모두 없으면 단일 상태로 폴백", () => {
    expect(badgeText("planning", "none", 0, summary({}))).toBe("대기");
    expect(badgeText("planning", "active", 0, summary({}))).toBe("● 진행 중");
  });

  it("summary 미제공 시 기존 단일 상태", () => {
    expect(badgeText("planning", "done", 0, undefined)).toBe("완료");
  });
});

describe("badgeText — 그 외 단계", () => {
  it("maintain 은 백업 수", () => {
    expect(badgeText("maintain", "none", 3)).toBe("백업 3개");
  });
  it("develop 은 열기", () => {
    expect(badgeText("develop", "none", 0)).toBe("열기");
  });
});
