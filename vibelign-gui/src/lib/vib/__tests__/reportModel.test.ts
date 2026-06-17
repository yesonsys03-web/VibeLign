import { test, expect } from "vitest";
import { rejectPairs, type ReviewDecisions } from "../reportModel";

test("rejectPairs collects only rejected coordinates", () => {
  const decisions: ReviewDecisions = { "0:0": "accept", "0:1": "reject", "1:0": "reject" };
  expect(rejectPairs(decisions).sort()).toEqual([[0, 1], [1, 0]]);
});

test("rejectPairs empty when all accepted", () => {
  expect(rejectPairs({ "0:0": "accept" })).toEqual([]);
});
