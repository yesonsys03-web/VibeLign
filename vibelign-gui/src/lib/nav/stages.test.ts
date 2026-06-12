import { describe, it, expect } from "vitest";
import { stageOf, pagesForStage, STAGE_DEFS, PAGE_LABELS } from "./stages";

describe("stageOf", () => {
  it("기획방은 기획 단계", () => {
    expect(stageOf("planning")).toBe("planning");
  });
  it("코드탐색·문서는 개발 단계", () => {
    expect(stageOf("code")).toBe("develop");
    expect(stageOf("docs")).toBe("develop");
  });
  it("진단·백업·에러로그는 유지보수 단계", () => {
    expect(stageOf("doctor")).toBe("maintain");
    expect(stageOf("backups")).toBe("maintain");
    expect(stageOf("logs")).toBe("maintain");
  });
  it("기획안은 기획 단계", () => {
    expect(stageOf("plan-doc")).toBe("planning");
  });
  it("홈·사용법·설정은 단계 없음(null)", () => {
    expect(stageOf("home")).toBeNull();
    expect(stageOf("manual")).toBeNull();
    expect(stageOf("settings")).toBeNull();
  });
});

describe("pagesForStage", () => {
  it("개발 단계는 코드탐색·문서·작업방·실행해보기 순서", () => {
    expect(pagesForStage("develop")).toEqual(["code", "docs", "work", "run"]);
  });
  it("유지보수 단계는 진단·백업·에러로그 순서", () => {
    expect(pagesForStage("maintain")).toEqual(["doctor", "backups", "logs"]);
  });
  it("기획 단계는 기획방·기획안 순서", () => {
    expect(pagesForStage("planning")).toEqual(["planning", "plan-doc"]);
  });
});

describe("STAGE_DEFS", () => {
  it("기획→개발→유지보수 순서", () => {
    expect(STAGE_DEFS.map((d) => d.key)).toEqual(["planning", "develop", "maintain"]);
  });
});

describe("PAGE_LABELS", () => {
  it("A안 한글 라벨 유지", () => {
    expect(PAGE_LABELS.docs).toBe("문서");
    expect(PAGE_LABELS.code).toBe("코드탐색");
    expect(PAGE_LABELS.doctor).toBe("진단");
    expect(PAGE_LABELS.backups).toBe("백업");
    expect(PAGE_LABELS.logs).toBe("에러로그");
  });
  it("모든 page 라벨 정의", () => {
    expect(PAGE_LABELS).toEqual({
      home: "홈",
      planning: "기획방",
      "plan-doc": "기획안",
      code: "코드탐색",
      docs: "문서",
      work: "작업방",
      run: "실행해보기",
      doctor: "진단",
      backups: "백업",
      logs: "에러로그",
      manual: "사용법",
      settings: "설정",
    });
  });
});
