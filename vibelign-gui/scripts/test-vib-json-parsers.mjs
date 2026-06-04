import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const source = [
  "src/lib/vib/memory.ts",
  "src/lib/vib/recovery.ts",
  "src/lib/vib/normalizers.ts",
]
  .map((path) => readFileSync(resolve(path), "utf8"))
  .join("\n");

const requiredSnippets = [
  "function parseMemorySummaryPayload",
  "function parseRecoveryPreviewJson",
  "function parseRecoveryRecommendationJson",
  "function requireRecordArray",
  "function requireOptionalRecord",
  "throw new Error(`${field}: expected array`)",
  "requireRecord(item, `${field}[${index}]`)",
  "requireString((data.active_intent as Record<string, unknown>).text",
  "requireRecord(item.evidence_score",
];

for (const snippet of requiredSnippets) {
  if (!source.includes(snippet)) {
    throw new Error(`missing parser contract snippet: ${snippet}`);
  }
}

console.log("vib JSON parser contract checks passed");
