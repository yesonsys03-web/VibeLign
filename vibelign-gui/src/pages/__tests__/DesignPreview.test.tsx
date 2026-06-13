import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";
import DesignPreview from "../DesignPreview";

const mocks = vi.hoisted(() => ({ generateMock: vi.fn(), saveMock: vi.fn() }));
vi.mock("../../lib/vib/design", () => ({
  generateDesignMockup: mocks.generateMock,
  saveDesignMockup: mocks.saveMock,
}));

afterEach(() => { cleanup(); mocks.generateMock.mockReset(); mocks.saveMock.mockReset(); });

describe("DesignPreview", () => {
  test("스타일 선택·생성 시 목업을 sandbox iframe에 렌더", async () => {
    mocks.generateMock.mockResolvedValue({ html: "<!doctype html><h1>MOCK</h1>", cached: false });
    render(<DesignPreview projectDir="/tmp/demo" planPath="plans/x.md" isLikelyWeb onBack={vi.fn()} onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /네오브루탈리즘/ }));
    fireEvent.click(screen.getByRole("button", { name: "이 스타일로 그려보기" }));
    await waitFor(() => {
      const frame = screen.getByTitle("디자인 목업") as HTMLIFrameElement;
      expect(frame.getAttribute("srcdoc")).toContain("MOCK");
      expect(frame.getAttribute("sandbox")).toBe("");
    });
    expect(mocks.generateMock).toHaveBeenCalledWith(
      expect.objectContaining({ projectDir: "/tmp/demo", planPath: "plans/x.md" }),
    );
  });

  test("피드백 재생성은 직전 HTML + feedback과 함께 호출", async () => {
    mocks.generateMock
      .mockResolvedValueOnce({ html: "<!doctype html><h1>V1</h1>", cached: false })
      .mockResolvedValueOnce({ html: "<!doctype html><h1>V2</h1>", cached: false });
    render(<DesignPreview projectDir="/tmp/demo" planPath="plans/x.md" isLikelyWeb onBack={vi.fn()} onConfirm={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /네오브루탈리즘/ }));
    fireEvent.click(screen.getByRole("button", { name: "이 스타일로 그려보기" }));
    await waitFor(() => expect((screen.getByTitle("디자인 목업") as HTMLIFrameElement).getAttribute("srcdoc")).toContain("V1"));
    fireEvent.change(screen.getByLabelText("수정 요청"), { target: { value: "버튼 크게" } });
    fireEvent.click(screen.getByRole("button", { name: "다시 그리기" }));
    await waitFor(() => expect((screen.getByTitle("디자인 목업") as HTMLIFrameElement).getAttribute("srcdoc")).toContain("V2"));
    expect(mocks.generateMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ feedback: "버튼 크게", previousHtml: expect.stringContaining("V1") }),
    );
  });

  test("비웹이면 경고 배너를 보이되 차단하지 않음", () => {
    render(<DesignPreview projectDir="/tmp/demo" planPath="plans/x.md" isLikelyWeb={false} onBack={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByText(/웹 UI 프로젝트가 아닐 수 있어요/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이 스타일로 그려보기" })).toBeInTheDocument(); // 여전히 가능
  });
});
