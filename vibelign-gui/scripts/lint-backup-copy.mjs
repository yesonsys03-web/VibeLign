import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, relative } from "node:path";

const root = fileURLToPath(new URL("..", import.meta.url));
const targets = [
  join(root, "src/pages/BackupDashboard.tsx"),
  join(root, "src/components/backup-dashboard"),
];
const banned = [
  "SHA",
  "hash",
  "해시",
  "trigger",
  "트리거",
  "checkpoint",
  "체크포인트",
  "diff",
  "디프",
  "preview",
  "프리뷰",
  "ledger",
  "레저",
  "post_commit",
  "commit-backed",
];
const sourceExtensions = new Set([".ts", ".tsx"]);
const stringPattern = /(["'`])((?:\\.|(?!\1)[\s\S])*)\1/g;

function listFiles(path) {
  const info = statSync(path);
  if (info.isFile()) return [path];
  return readdirSync(path)
    .flatMap((name) => listFiles(join(path, name)))
    .filter((file) => sourceExtensions.has(file.slice(file.lastIndexOf("."))));
}

const problems = [];
for (const file of targets.flatMap(listFiles)) {
  const text = readFileSync(file, "utf8");
  for (const match of text.matchAll(stringPattern)) {
    const literal = match[2];
    if (literal.startsWith(".") || literal.startsWith("/")) continue;
    for (const token of banned) {
      const flags = token === "SHA" ? "" : "i";
      if (new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags).test(literal)) {
        problems.push(`${relative(root, file)} contains banned backup copy token: ${token}`);
      }
    }
  }
}

if (problems.length > 0) {
  console.error(problems.join("\n"));
  process.exit(1);
}
