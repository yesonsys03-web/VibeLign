// === ANCHOR: SESSION_MEMORY_CARD_START ===
import { useEffect, useState } from "react";
import { CardState } from "../../lib/commands";
import { MemorySummaryResult, memorySummary } from "../../lib/vib";

interface SessionMemoryCardProps {
  projectDir: string;
}

export default function SessionMemoryCard({ projectDir }: SessionMemoryCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [summary, setSummary] = useState<MemorySummaryResult | null>(null);

  async function refresh() {
    setState("loading");
    try {
      const nextSummary = await memorySummary(projectDir);
      setSummary(nextSummary);
      setState("done");
    } catch {
      setState("error");
    }
  }

  useEffect(() => {
    void refresh();
  }, [projectDir]);

  const decisions = (summary?.decisions.slice(-2) ?? []).map(plainMemoryText);
  const relevantFiles = (summary?.relevantFiles.slice(-3) ?? []).map(plainRelevantFile);
  const verification = plainVerification(summary?.verification.slice(-1)[0]);

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#4DFF9118", padding: "10px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#4DFF91", color: "#1A1A1A", borderColor: "#4DFF91", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>🧠</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>세션 메모리</div>
          <div style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>AI가 지금 작업을 어디까지 기억하는지 쉽게 보여줘요</div>
        </div>
        {state === "error" && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <MemoryLine label="지금 하던 일" value={friendlyValue(summary?.activeIntent, "아직 기록된 목표가 없어요.")} help="새 AI에게 '무슨 작업 중이었는지' 알려주는 메모예요." />
        <MemoryLine label="다음에 할 일" value={friendlyValue(summary?.nextAction, "다음 행동이 아직 정해지지 않았어요.")} help="이어서 작업할 때 가장 먼저 보면 되는 한 줄이에요." />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6, fontSize: 10 }}>
          <span style={{ fontWeight: 900, color: "#777", letterSpacing: 0.8 }}>확인 상태</span>
          <span style={{ fontWeight: 900, padding: "2px 6px", border: "1.5px solid #1A1A1A", background: freshnessColor(summary?.verificationFreshness) }}>
            {freshnessLabel(summary?.verificationFreshness)}
          </span>
        </div>
        <div style={{ fontSize: 10, color: "#555", lineHeight: 1.35, marginBottom: 6 }}>
          {freshnessHint(summary?.verificationFreshness)}
        </div>
        {verification && <div style={{ fontSize: 10, color: "#555", lineHeight: 1.35, marginBottom: 6 }}>마지막 확인 기록: {verification}</div>}
        {decisions.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 10, color: "#555", lineHeight: 1.45 }}>
            <div style={{ fontWeight: 900, color: "#777", marginBottom: 3 }}>중요하게 정한 것</div>
            {decisions.map((item, index) => <div key={index}>• {item}</div>)}
          </div>
        )}
        {relevantFiles.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 10, color: "#555", lineHeight: 1.45 }}>
            <div style={{ fontWeight: 900, color: "#777", marginBottom: 3 }}>최근 작업 파일</div>
            {relevantFiles.map((item, index) => <div key={index}>• {item}</div>)}
          </div>
        )}
        <button className="btn btn-sm" style={{ width: "100%", marginTop: 8, background: "#4DFF91", color: "#1A1A1A", border: "2px solid #1A1A1A" }} disabled={state === "loading"} onClick={refresh}>
          {state === "loading" ? <span className="spinner" /> : "메모리 새로고침"}
        </button>
      </div>
    </div>
  );
}

function MemoryLine({ label, value, help }: { label: string; value: string; help: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 9, fontWeight: 900, color: "#777", letterSpacing: 0.8 }}>{label}</div>
      <div style={{ fontSize: 11, color: "#1A1A1A", lineHeight: 1.45, border: "1.5px solid #1A1A1A", background: "#fff", padding: "5px 7px" }}>{value}</div>
      <div style={{ fontSize: 9, color: "#777", lineHeight: 1.35, marginTop: 2 }}>{help}</div>
    </div>
  );
}

function friendlyValue(value: string | undefined, fallback: string): string {
  if (!value || value === "(none)") return fallback;
  return plainMemoryText(value);
}

function plainMemoryText(value: string): string {
  const text = compact(value);
  if (!text) return text;
  if (isVerificationRecord(text)) return plainVerification(text) ?? "안전 점검 기록이에요. 계속하기 전에 최신 상태인지 다시 확인하면 좋아요.";
  return easySentence(text);
}

function plainVerification(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const text = compact(value);
  const stale = isStale(text) ? " 이 기록은 오래됐을 수 있어서 최신 점검을 다시 하는 게 좋아요." : "";
  if (isVerificationRecord(text)) {
    if (looksRisky(text)) {
      return `최근 안전 점검에서 조심해야 한다는 신호가 나왔어요. 계속하기 전에 다시 점검하는 게 안전합니다.${stale}`;
    }
    return `최근 안전 점검 기록이에요. 문제가 없어 보여도 오래된 기록이면 다시 확인하는 게 좋아요.${stale}`;
  }
  const passed = text.match(/(\d+)\s+passed/i);
  if (passed) return `테스트 ${passed[1]}개가 통과했다는 기록이에요.${stale}`;
  if (looksTechnical(text)) return `전문가용 확인 기록이 있어요. 계속하기 전 최신 점검을 다시 보면 안전합니다.${stale}`;
  return `${easySentence(text)}${stale}`;
}

function plainRelevantFile(value: string): string {
  const [path] = value.split(" — ");
  const fileName = path.split(/[\\/]/).filter(Boolean).pop() || path;
  return `${fileName} 파일이 최근 작업과 관련 있어요.`;
}

function compact(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function isVerificationRecord(value: string): boolean {
  return /guard[_ -]?check|doctor|pytest|passed|failed|project[_ -]?status|project[_ -]?score|blocked/i.test(value);
}

function isStale(value: string): boolean {
  return /stale|old|outdated/i.test(value);
}

function looksRisky(value: string): boolean {
  return /fail|blocked"?:\s*true|high\s+risk|risk|score"?:\s*0/i.test(value);
}

function looksTechnical(value: string): boolean {
  const text = compact(value);
  const symbolCount = (text.match(/[{}[\]_=/>\\|]/g) ?? []).length;
  const codeWords = (text.match(/\b[A-Za-z]+[_-][A-Za-z0-9_-]+\b|\b[A-Za-z]+[A-Z][A-Za-z0-9]*\b/g) ?? []).length;
  const pathLike = /\.?[\w-]+\/[\w./-]+/.test(text);
  const jsonLike = /"\w+"\s*:|\{.*\}/.test(text);
  return symbolCount >= 3 || codeWords >= 2 || pathLike || jsonLike || text.length > 140;
}

function easySentence(value: string): string {
  const text = compact(value);
  if (text.length <= 180) return text;
  return `${text.slice(0, 177)}...`;
}

function freshnessLabel(value: MemorySummaryResult["verificationFreshness"] | undefined): string {
  if (value === "fresh") return "최근 확인됨";
  if (value === "stale") return "다시 확인 필요";
  if (value === "missing") return "확인 기록 없음";
  return "불러오는 중";
}

function freshnessHint(value: MemorySummaryResult["verificationFreshness"] | undefined): string {
  if (value === "fresh") return "테스트나 점검 결과가 최근 상태라 이어서 작업하기 비교적 안전해요.";
  if (value === "stale") return "이전 확인 결과가 오래됐을 수 있어요. 계속하기 전에 다시 점검하는 게 좋아요.";
  if (value === "missing") return "아직 테스트나 점검 기록이 없어요. 작업 전 한 번 확인하는 게 안전해요.";
  return "세션 메모리를 불러오는 중이에요.";
}

function freshnessColor(value: MemorySummaryResult["verificationFreshness"] | undefined): string {
  if (value === "fresh") return "#4DFF91";
  if (value === "stale") return "#FFD166";
  return "#EEE";
}
// === ANCHOR: SESSION_MEMORY_CARD_END ===
