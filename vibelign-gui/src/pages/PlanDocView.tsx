// === ANCHOR: PLAN_DOC_VIEW_START ===
import { useEffect, useState } from "react";
import DocumentPane from "../components/docs/DocumentPane";
import { loadDoc } from "../lib/docs";
import type { ReadFileResult } from "../lib/vib";

interface PlanDocViewProps {
  projectDir: string;
  /** 기획방 세션이 저장한 기획안 경로. 없으면 빈 상태. */
  outputPath: string | null;
  /** 빈 상태에서 기획을 시작/이어가도록 이동(세션 유무는 호출부가 판단). */
  onStart?: () => void;
}

/**
 * 기획 단계 '기획안' 서브탭. 기획방에서 만든 기획안(outputPath)을 문서 탭과 동일한
 * 마크다운 렌더(DocumentPane)로 보여준다. 개발>문서와 달리 현재 기획안 하나에 집중한다.
 */
export default function PlanDocView({ projectDir, outputPath, onStart }: PlanDocViewProps) {
  const [doc, setDoc] = useState<ReadFileResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!outputPath) {
      setDoc(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    loadDoc(projectDir, outputPath)
      .then((result) => {
        if (!cancelled) setDoc(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : typeof err === "string" ? err : "기획안을 불러오지 못했어요.");
          setDoc(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectDir, outputPath]);

  if (!outputPath) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "#888" }}>
        <div style={{ fontSize: 32 }}>📋</div>
        <div style={{ fontSize: 14 }}>아직 기획안이 없어요.</div>
        <div style={{ fontSize: 12, color: "#666" }}>기획방에서 대화로 기획안을 만들면 여기에 표시됩니다.</div>
        {onStart && (
          <button className="nav-tab" style={{ marginTop: 4 }} onClick={onStart}>
            기획 시작하기 →
          </button>
        )}
      </div>
    );
  }

  if (loading) {
    return <div style={{ padding: 24, color: "#888", fontSize: 13 }}>기획안을 불러오는 중…</div>;
  }
  if (error) {
    return <div style={{ padding: 24, color: "#F87171", fontSize: 13 }}>오류: {error}</div>;
  }
  if (!doc) return null;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "8px 12px", fontSize: 12, color: "#555", borderBottom: "1px solid #1A1A1A" }}>
        기획안 · {outputPath}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        <DocumentPane path={doc.path} content={doc.content} />
      </div>
    </div>
  );
}
// === ANCHOR: PLAN_DOC_VIEW_END ===
