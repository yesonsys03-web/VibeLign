// === ANCHOR: ERROR_LOGS_PAGE_START ===
import { useState, useEffect, useCallback } from "react";
import { confirm as tauriConfirm } from "@tauri-apps/plugin-dialog";
import { openUrl } from "@tauri-apps/plugin-opener";
import { clearErrorLogs, readErrorLogs, type ErrorLogEntry } from "../lib/vib";

const GITHUB_NEW_ISSUE_URL = "https://github.com/yesonsys03-web/VibeLign/issues/new";
// GitHub 의 GET 요청 URL 길이 한계 (~8KB) 안에 들도록 본문 안전 한도.
const GITHUB_BODY_MAX = 6000;

function buildGithubIssueUrl(entry: ErrorLogEntry): string {
  const messageHead = entry.message.slice(0, 80).replace(/\s+/g, " ");
  const titleParts = [`[${entry.kind.toUpperCase()}]`];
  if (entry.error_class) titleParts.push(entry.error_class);
  if (messageHead) titleParts.push(messageHead);
  const title = titleParts.join(" ").slice(0, 240);

  const bodyLines = [
    "## 환경",
    `- 발생 시각: ${entry.ts}`,
    `- 종류: ${entry.kind.toUpperCase()}`,
  ];
  if (entry.error_class) bodyLines.push(`- 에러 클래스: \`${entry.error_class}\``);
  if (entry.context) bodyLines.push(`- 컨텍스트: \`${entry.context}\``);
  bodyLines.push("");
  bodyLines.push("## 에러 내용 (자동 redacted: 시크릿/경로 마스킹 적용)");
  bodyLines.push("```json");
  bodyLines.push(entry.raw_json);
  bodyLines.push("```");
  bodyLines.push("");
  bodyLines.push("## 추가 정보");
  bodyLines.push("- 어떤 동작 중 발생했는지:");
  bodyLines.push("- 재현 방법 (있다면):");
  bodyLines.push("- 다른 의견:");

  let body = bodyLines.join("\n");
  if (body.length > GITHUB_BODY_MAX) {
    body = body.slice(0, GITHUB_BODY_MAX) + "\n\n_(URL 길이 한계로 일부 잘림)_";
  }

  const params = new URLSearchParams({ title, body });
  return `${GITHUB_NEW_ISSUE_URL}?${params.toString()}`;
}

function buildBulkGithubIssueUrl(entries: ErrorLogEntry[]): string {
  const cliCount = entries.filter((entry) => entry.kind === "cli").length;
  const guiCount = entries.length - cliCount;
  const summary = [
    cliCount > 0 ? `CLI ${cliCount}` : null,
    guiCount > 0 ? `GUI ${guiCount}` : null,
  ]
    .filter(Boolean)
    .join(" + ");
  const title = `[Bulk] ${entries.length}개 에러 보고 (${summary})`.slice(0, 240);

  const bodyParts = [
    `## 요약`,
    `- 총 ${entries.length}개의 에러를 한 이슈로 묶어서 보고합니다.`,
    `- 같은 root cause 가 의심되거나 관련된 항목들을 모은 형태입니다.`,
    "",
    "## 사용자 추가 정보",
    "- 어떤 동작 중 발생했는지:",
    "- 재현 방법 (있다면):",
    "- 다른 의견:",
    "",
    "---",
  ];
  entries.forEach((entry, index) => {
    bodyParts.push("");
    bodyParts.push(`## ${index + 1}. ${entry.kind.toUpperCase()} — ${entry.error_class ?? "(no class)"}`);
    bodyParts.push(`- 발생 시각: ${entry.ts}`);
    if (entry.context) bodyParts.push(`- 컨텍스트: \`${entry.context}\``);
    bodyParts.push("");
    bodyParts.push("```json");
    bodyParts.push(entry.raw_json);
    bodyParts.push("```");
  });

  let body = bodyParts.join("\n");
  if (body.length > GITHUB_BODY_MAX) {
    body = body.slice(0, GITHUB_BODY_MAX) + "\n\n_(URL 길이 한계로 일부 잘림 — 나머지 항목은 따로 보고해 주세요)_";
  }
  const params = new URLSearchParams({ title, body });
  return `${GITHUB_NEW_ISSUE_URL}?${params.toString()}`;
}

function entryKey(entry: ErrorLogEntry, index: number): string {
  return `${entry.ts}-${index}`;
}

interface ErrorLogsPageProps {
  projectDir: string;
}

type KindFilter = "all" | "cli" | "gui";

const KIND_LABEL: Record<"cli" | "gui", string> = {
  cli: "CLI",
  gui: "GUI",
};

function formatTimestamp(ts: string): string {
  if (!ts) return "-";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return ts;
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function ErrorLogs({ projectDir }: ErrorLogsPageProps) {
  const [entries, setEntries] = useState<ErrorLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<KindFilter>("all");
  const [selected, setSelected] = useState<ErrorLogEntry | null>(null);
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await readErrorLogs(projectDir, 500);
      setEntries(next);
      setChecked(new Set());
    } catch (exc) {
      setError(String(exc));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  const toggleChecked = useCallback((key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const handleClear = useCallback(async () => {
    if (entries.length === 0) return;
    const confirmed = await tauriConfirm(
      `현재 ${entries.length}건의 에러 로그를 모두 정리합니다.\n` +
        `수정 완료된 에러를 정리해두면 새로 발생하는 에러가 눈에 띄어요.\n\n` +
        `정말 정리할까요?`,
      { title: "에러 로그 정리", kind: "warning" },
    );
    if (!confirmed) return;
    setLoading(true);
    setError(null);
    try {
      const result = await clearErrorLogs(projectDir);
      if (result.kept > 0) {
        setError(`${result.removed}건 정리. ${result.kept}건은 권한 문제로 남았어요.`);
      }
      setEntries([]);
      setSelected(null);
    } catch (exc) {
      setError(String(exc));
    } finally {
      setLoading(false);
    }
  }, [entries.length, projectDir]);

  useEffect(() => {
    load();
  }, [load]);

  const visible = filter === "all" ? entries : entries.filter((entry) => entry.kind === filter);
  const visibleKeys = visible.map((entry, index) => entryKey(entry, index));
  const allVisibleSelected = visibleKeys.length > 0 && visibleKeys.every((key) => checked.has(key));
  const checkedEntries = visible
    .map((entry, index) => ({ entry, key: entryKey(entry, index) }))
    .filter(({ key }) => checked.has(key))
    .map(({ entry }) => entry);

  const toggleAllVisible = useCallback(() => {
    setChecked((prev) => {
      const next = new Set(prev);
      const allSelected = visibleKeys.every((key) => next.has(key));
      if (allSelected) {
        visibleKeys.forEach((key) => next.delete(key));
      } else {
        visibleKeys.forEach((key) => next.add(key));
      }
      return next;
    });
  }, [visibleKeys]);

  const handleBulkSeparate = useCallback(async () => {
    if (checkedEntries.length === 0) return;
    if (
      checkedEntries.length > 5 &&
      !(await tauriConfirm(
        `${checkedEntries.length}개의 GitHub 이슈 탭을 순차적으로 엽니다.\n` +
          `각 탭에서 검토 후 직접 Submit 해야 합니다.\n\n` +
          `진행할까요?`,
        { title: "이슈 탭 열기" },
      ))
    ) {
      return;
    }
    // 브라우저가 다중 탭 오픈을 차단하는 경우가 있어 짧은 간격으로 순차 호출.
    for (const entry of checkedEntries) {
      await openUrl(buildGithubIssueUrl(entry)).catch(() => {});
      await new Promise((resolve) => setTimeout(resolve, 120));
    }
  }, [checkedEntries]);

  const handleBulkSingle = useCallback(() => {
    if (checkedEntries.length === 0) return;
    void openUrl(buildBulkGithubIssueUrl(checkedEntries)).catch(() => {});
  }, [checkedEntries]);

  return (
    <div style={{ padding: "16px 16px 0", height: "100%", overflow: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>에러 로그</h2>
        <span style={{ fontSize: 12, color: "#777" }}>
          .vibelign/logs/{`{cli,gui}`}-error-&lt;date&gt;.jsonl 통합
        </span>
        <div style={{ flex: 1 }} />
        <button
          className="btn btn-sm btn-ghost"
          onClick={handleClear}
          disabled={loading || entries.length === 0}
          title="수정 완료된 에러를 정리해 새로 발생하는 항목이 눈에 띄게 합니다."
          style={{ fontSize: 11 }}
        >
          🗑 정리
        </button>
        <button className="btn btn-sm" onClick={load} disabled={loading}>
          {loading ? "불러오는 중…" : "새로 고침"}
        </button>
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        {(["all", "cli", "gui"] as const).map((value) => (
          <button
            key={value}
            className={`btn btn-sm ${filter === value ? "" : "btn-ghost"}`}
            onClick={() => setFilter(value)}
            style={{ fontSize: 11 }}
          >
            {value === "all" ? `전체 (${entries.length})` : `${KIND_LABEL[value]} (${entries.filter((e) => e.kind === value).length})`}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ background: "#FEE", border: "1px solid #C33", padding: 8, marginBottom: 8, fontSize: 12 }}>
          {error}
        </div>
      )}

      {!loading && visible.length === 0 && (
        <div style={{ padding: 24, textAlign: "center", color: "#777", fontSize: 13 }}>
          기록된 에러가 없어요.
        </div>
      )}

      {checkedEntries.length > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 10px",
            marginBottom: 6,
            border: "2px solid #1A1A1A",
            background: "#FFF8DC",
            fontSize: 12,
          }}
        >
          <strong>{checkedEntries.length}개 선택됨.</strong>
          <span style={{ color: "#555" }}>
            관련 있는 항목이면 한 이슈로, 서로 다른 버그면 각각 보고하세요.
          </span>
          <div style={{ flex: 1 }} />
          <button
            className="btn btn-sm"
            onClick={handleBulkSingle}
            style={{ background: "#24292f", color: "#fff", border: "2px solid #1A1A1A" }}
            title="선택한 항목들을 하나의 GitHub 이슈로 묶어서 보고합니다."
          >
            🐛 한 이슈로 묶기
          </button>
          <button
            className="btn btn-sm"
            onClick={handleBulkSeparate}
            style={{ background: "#24292f", color: "#fff", border: "2px solid #1A1A1A" }}
            title="선택한 항목마다 별도 GitHub 이슈 탭을 엽니다."
          >
            🐛 각각 보고 ({checkedEntries.length} tabs)
          </button>
          <button className="btn btn-sm btn-ghost" onClick={() => setChecked(new Set())} style={{ fontSize: 11 }}>
            선택 해제
          </button>
        </div>
      )}

      {visible.length > 0 && (
        <div style={{ border: "1px solid #1A1A1A", maxHeight: "70vh", overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead style={{ position: "sticky", top: 0, background: "#1A1A1A", color: "#FEFBF0" }}>
              <tr>
                <th style={{ textAlign: "left", padding: "6px 4px", width: 28 }}>
                  <input
                    type="checkbox"
                    checked={allVisibleSelected}
                    onChange={toggleAllVisible}
                    title={allVisibleSelected ? "전체 선택 해제" : "보이는 항목 전체 선택"}
                    style={{ cursor: "pointer" }}
                  />
                </th>
                <th style={{ textAlign: "left", padding: "6px 8px", width: 160 }}>시간</th>
                <th style={{ textAlign: "left", padding: "6px 8px", width: 60 }}>종류</th>
                <th style={{ textAlign: "left", padding: "6px 8px", width: 180 }}>분류</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>메시지</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((entry, index) => {
                const key = entryKey(entry, index);
                const isChecked = checked.has(key);
                return (
                <tr
                  key={key}
                  onClick={() => setSelected(entry)}
                  style={{
                    cursor: "pointer",
                    background: isChecked ? "#FFF1B8" : (index % 2 === 0 ? "#FEFBF0" : "#F5F0E0"),
                    borderBottom: "1px solid #E0DACE",
                  }}
                >
                  <td
                    onClick={(event) => event.stopPropagation()}
                    style={{ padding: "6px 4px", textAlign: "center" }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleChecked(key)}
                      style={{ cursor: "pointer" }}
                    />
                  </td>
                  <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{formatTimestamp(entry.ts)}</td>
                  <td style={{ padding: "6px 8px" }}>
                    <span
                      style={{
                        background: entry.kind === "cli" ? "#4D9FFF" : "#F5621E",
                        color: "#fff",
                        padding: "1px 6px",
                        fontSize: 10,
                        fontWeight: 700,
                      }}
                    >
                      {KIND_LABEL[entry.kind]}
                    </span>
                  </td>
                  <td style={{ padding: "6px 8px", fontFamily: "monospace", color: "#555" }}>
                    {entry.error_class ?? entry.context ?? "-"}
                  </td>
                  <td style={{ padding: "6px 8px", maxWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {entry.message || <span style={{ color: "#999" }}>(빈 메시지)</span>}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div
          onClick={() => setSelected(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#FEFBF0",
              border: "3px solid #1A1A1A",
              boxShadow: "8px 8px 0 #1A1A1A",
              width: "92%",
              maxWidth: 720,
              maxHeight: "82vh",
              display: "flex",
              flexDirection: "column",
              padding: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <strong style={{ fontSize: 14 }}>에러 상세</strong>
              <span style={{ fontSize: 11, color: "#666" }}>{formatTimestamp(selected.ts)}</span>
              <div style={{ flex: 1 }} />
              <button
                className="btn btn-sm"
                onClick={() => { openUrl(buildGithubIssueUrl(selected)).catch(() => {}); }}
                title="GitHub 에 새 이슈로 보고합니다. 본문은 미리 채워져 있고, 사용자가 검토 후 직접 제출합니다."
                style={{ background: "#24292f", color: "#fff", border: "2px solid #1A1A1A" }}
              >
                🐛 GitHub 이슈로 보고
              </button>
              <button className="btn btn-sm" onClick={() => setSelected(null)}>
                닫기
              </button>
            </div>
            <pre
              style={{
                background: "#fff",
                border: "1px solid #1A1A1A",
                padding: 12,
                overflow: "auto",
                fontSize: 11,
                lineHeight: 1.45,
                margin: 0,
                flex: 1,
              }}
            >
              {(() => {
                try {
                  const parsed = JSON.parse(selected.raw_json);
                  return JSON.stringify(parsed, null, 2);
                } catch {
                  return selected.raw_json;
                }
              })()}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
// === ANCHOR: ERROR_LOGS_PAGE_END ===
