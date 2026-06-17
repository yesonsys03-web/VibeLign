import { test, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { BlockDiff } from "../BlockDiff";

afterEach(cleanup);

test("모호어가 하이라이트(mark)로 표시된다", () => {
  render(
    <BlockDiff
      heading="개요"
      base={{ kind: "summary", text: "성과가 대폭 좋아졌다", items: [] }}
      polished={{ kind: "summary", text: "성과가 대폭 좋아졌다", items: [] }}
      decision="accept"
      vague={[{ section: 0, block: 0, term: "대폭", offset: 4 }]}
      onAccept={() => {}}
      onReject={() => {}}
    />,
  );
  const mark = screen.getByText("대폭");
  expect(mark.tagName.toLowerCase()).toBe("mark");
});
