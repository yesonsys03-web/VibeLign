import { describe, it, expect } from "vitest";
import { TUTORIALS, getTutorial } from "../scripts";

describe("tutorial scripts", () => {
  it("todo 대본이 존재하고 단계가 있다", () => {
    const todo = getTutorial("todo");
    expect(todo).toBeDefined();
    expect(todo!.steps.length).toBeGreaterThan(0);
  });

  it("모든 단계 id가 대본 안에서 유일하다", () => {
    for (const t of TUTORIALS) {
      const ids = t.steps.map((s) => s.id);
      expect(new Set(ids).size).toBe(ids.length);
    }
  });

  it("copy·pasteSend 단계는 copyText를, click 단계는 target을 가진다", () => {
    for (const t of TUTORIALS) {
      for (const s of t.steps) {
        if (s.kind === "copy" || s.kind === "pasteSend")
          expect(s.copyText, `${t.id}/${s.id}`).toBeTruthy();
        else if (s.kind === "click")
          expect(s.target, `${t.id}/${s.id}`).toBeTruthy();
        // confirm 단계는 target 선택사항 — 강제하지 않음
      }
    }
  });

  it("todo 대본은 안전 절반(체크포인트·guard검사·되돌리기 인지)을 포함한다", () => {
    const todo = getTutorial("todo")!;
    const dones = todo.steps.map((s) => s.done);
    expect(dones).toContain("checkpoint");
    expect(dones).toContain("guardChecked");
    // 되돌리기 인지: restore 버튼을 가리키는 단계가 있다
    expect(todo.steps.some((s) => s.target === "checkpoint-restore")).toBe(true);
  });

  it("3종 대본이 모두 등록돼 있다", () => {
    expect(TUTORIALS.map((t) => t.id).sort()).toEqual(["guestbook", "quiz", "todo"]);
  });

  it("모든 대본이 안전 절반을 포함한다", () => {
    for (const t of TUTORIALS) {
      const dones = t.steps.map((s) => s.done);
      expect(dones, t.id).toContain("checkpoint");
      expect(dones, t.id).toContain("guardChecked");
      expect(t.steps.some((s) => s.target === "checkpoint-restore"), t.id).toBe(true);
    }
  });
});
