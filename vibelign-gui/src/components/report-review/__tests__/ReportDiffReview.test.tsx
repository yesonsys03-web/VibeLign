// === ANCHOR: REPORTDIFFREVIEW_TEST_START ===
import { test, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ReportDiffReview } from "../ReportDiffReview";
import type { EmitPayload } from "../../../lib/vib/reportModel";

afterEach(cleanup);

const payload: EmitPayload = {
  ok: true, report_type: "work", slug: "s", key: "k", guards: [], vague_warnings: [],
  base: { title: "t", report_type: "work", date: "d", source_plan_path: "", sections: [
    { heading: "개요", blocks: [{ kind: "summary", text: "원본요약", items: [] }] }] },
  polished: { title: "t", report_type: "work", date: "d", source_plan_path: "", sections: [
    { heading: "개요", blocks: [{ kind: "summary", text: "다듬요약", items: [] }] }] },
};

test("거부 시 onConfirm 이 해당 좌표를 reject 로 전달", () => {
  const onConfirm = vi.fn();
  render(<ReportDiffReview payload={payload} onConfirm={onConfirm} onCancel={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "거부" }));
  fireEvent.click(screen.getByRole("button", { name: /저장|내보내기/ }));
  expect(onConfirm).toHaveBeenCalledWith([[0, 0]]);
});

test("기본은 모두 수락 → reject 빈 배열", () => {
  const onConfirm = vi.fn();
  render(<ReportDiffReview payload={payload} onConfirm={onConfirm} onCancel={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /저장|내보내기/ }));
  expect(onConfirm).toHaveBeenCalledWith([]);
});
// === ANCHOR: REPORTDIFFREVIEW_TEST_END ===
