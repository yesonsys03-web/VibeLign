// === ANCHOR: CODEFILETREE_REVIEW_MENU_TEST_START ===
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import CodeFileTree from "../CodeFileTree";
import type { CodeFileEntry, ChangeStatus } from "../../../lib/vib";

const files: CodeFileEntry[] = [
  { path: "docs/plan.md", category: "docs", imports: [] },
];
const noChanges = new Map<string, ChangeStatus>();

describe("CodeFileTree review menu", () => {
  afterEach(() => {
    cleanup();
  });

  test("right_click_md_file_opens_review_in_planning", () => {
    const onReviewInPlanning = vi.fn();
    render(
      <CodeFileTree
        files={files}
        selectedPath={null}
        onSelect={vi.fn()}
        autoExpandAll={true}
        changes={noChanges}
        onReviewInPlanning={onReviewInPlanning}
      />,
    );

    fireEvent.contextMenu(screen.getByTitle("docs/plan.md"));
    fireEvent.click(screen.getByRole("button", { name: "기획방에서 검토" }));

    expect(onReviewInPlanning).toHaveBeenCalledWith("docs/plan.md");
  });
});
// === ANCHOR: CODEFILETREE_REVIEW_MENU_TEST_END ===
