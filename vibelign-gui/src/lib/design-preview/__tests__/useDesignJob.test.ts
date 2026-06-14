import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach } from "vitest";

const mocks = vi.hoisted(() => ({ synth: vi.fn(), gen: vi.fn() }));
vi.mock("../../vib/design", () => ({
  synthesizeStyle: mocks.synth,
  generateDesignMockup: mocks.gen,
}));

import { useDesignJob } from "../useDesignJob";
import { DESIGN_STYLES } from "../styles";

const STYLE = DESIGN_STYLES[0];

beforeEach(() => {
  mocks.synth.mockReset();
  mocks.gen.mockReset();
});

describe("useDesignJob", () => {
  test("describe 흐름: idle→running→done, synth·html 세팅, gen은 synth 스타일로 호출", async () => {
    mocks.synth.mockResolvedValue({ ...STYLE, id: "synth1", name: "합성" });
    mocks.gen.mockResolvedValue({ html: "<h1>MOCK</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    expect(result.current.status).toBe("idle");
    act(() => result.current.run({ kind: "describe", description: "귀엽게" }, "plans/x.md"));
    expect(result.current.status).toBe("running");
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.html).toContain("MOCK");
    expect(result.current.synth?.id).toBe("synth1");
    expect(mocks.synth).toHaveBeenCalledWith(
      expect.objectContaining({ projectDir: "/tmp/p", planPath: "plans/x.md", description: "귀엽게" }),
    );
    expect(mocks.gen).toHaveBeenCalledWith(
      expect.objectContaining({ projectDir: "/tmp/p", planPath: "plans/x.md", style: expect.objectContaining({ id: "synth1" }) }),
    );
  });

  test("style 흐름: feedback·previousHtml 전달, synth 미설정", async () => {
    mocks.gen.mockResolvedValue({ html: "<h1>V2</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "style", style: STYLE, feedback: "버튼 크게", previousHtml: "<h1>V1</h1>" }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.html).toContain("V2");
    expect(result.current.synth).toBeNull();
    expect(mocks.gen).toHaveBeenCalledWith(
      expect.objectContaining({ style: STYLE, feedback: "버튼 크게", previousHtml: "<h1>V1</h1>" }),
    );
  });

  test("에러: gen 실패 시 status=error, error 메시지", async () => {
    mocks.gen.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "style", style: STYLE }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.error).toContain("boom");
  });

  test("projectDir 변경 시 reset(idle)", async () => {
    mocks.gen.mockResolvedValue({ html: "<h1>X</h1>", cached: false });
    const { result, rerender } = renderHook(({ dir }) => useDesignJob(dir), { initialProps: { dir: "/tmp/a" } });
    act(() => result.current.run({ kind: "style", style: STYLE }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    rerender({ dir: "/tmp/b" });
    expect(result.current.status).toBe("idle");
    expect(result.current.html).toBeNull();
  });

  test("recolor: synth 토큰 변경 + html 갱신(gen 재호출 없음)", async () => {
    mocks.synth.mockResolvedValue({ ...STYLE, id: "s", name: "s" });
    mocks.gen.mockResolvedValue({ html: ":root{--x:1}\n<h1>M</h1>", cached: false });
    const { result } = renderHook(() => useDesignJob("/tmp/p"));
    act(() => result.current.run({ kind: "describe", description: "x" }, "plans/x.md"));
    await waitFor(() => expect(result.current.status).toBe("done"));
    const before = result.current.html;
    act(() => result.current.recolor("primary", "#abcdef"));
    expect(result.current.synth?.tokens.primary).toBe("#abcdef");
    expect(result.current.html).not.toBe(before);
    expect(mocks.gen).toHaveBeenCalledTimes(1); // 재호출 없음
  });
});
