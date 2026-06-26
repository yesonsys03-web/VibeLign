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

  it("copy 단계는 copyText를, click/pasteSend/confirm 단계는 target을 가진다", () => {
    for (const t of TUTORIALS) {
      for (const s of t.steps) {
        if (s.kind === "copy") expect(s.copyText, `${t.id}/${s.id}`).toBeTruthy();
        else expect(s.target, `${t.id}/${s.id}`).toBeTruthy();
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
});
