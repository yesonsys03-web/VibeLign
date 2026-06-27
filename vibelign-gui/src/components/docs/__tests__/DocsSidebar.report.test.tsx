import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DocsSidebar from "../DocsSidebar";
import type { DocsIndexEntry } from "../../../lib/vib";

const DOCS: DocsIndexEntry[] = [
  { category: "Docs", path: "notes/plan.md", title: "내 노트", modified_at_ms: 0 },
];

function renderSidebar(onGenerateReport = vi.fn()) {
  render(
    <DocsSidebar
      docs={DOCS}
      query="plan"
      selectedPath={null}
      onQueryChange={() => {}}
      onSelect={() => {}}
      onGenerateReport={onGenerateReport}
    />,
  );
  return onGenerateReport;
}

describe("DocsSidebar 보고서 작성 컨텍스트 메뉴", () => {
  it("md 문서 우클릭 시 '보고서 작성' 메뉴가 뜨고 콜백이 경로를 넘긴다", () => {
    const onGenerateReport = renderSidebar();
    const docBtn = screen.getByTitle("notes/plan.md");
    fireEvent.contextMenu(docBtn);
    const item = screen.getByText("보고서 작성");
    fireEvent.click(item);
    expect(onGenerateReport).toHaveBeenCalledWith("notes/plan.md");
  });
});
