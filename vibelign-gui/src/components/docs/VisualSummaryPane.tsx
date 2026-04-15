import type { ReactNode } from "react";
import type { DocsTrustState } from "../../pages/DocsViewer";
import type { DocsVisualArtifact, DocsVisualSection } from "../../lib/vib";
import MermaidDiagram from "./MermaidDiagram";

interface VisualSummaryPaneProps {
  artifact: DocsVisualArtifact;
  trustState: DocsTrustState;
  onPhaseSelect?: (sectionId: string) => void;
}

function compact(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function sentenceSlice(text: string, count = 2): string {
  const parts = compact(text)
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
  return parts.slice(0, count).join(" ") || compact(text);
}

function topItems(items: string[], count = 3): string[] {
  return items.map(compact).filter(Boolean).slice(0, count);
}

function artifactWarnings(artifact: DocsVisualArtifact): string[] {
  const warnings = artifact.warnings;
  return warnings ? warnings : [];
}

function diagramProvenance(diagram: DocsVisualArtifact["diagram_blocks"][number]) {
  return diagram.provenance ?? "authored";
}

function diagramConfidence(diagram: DocsVisualArtifact["diagram_blocks"][number]) {
  return diagram.confidence ?? "high";
}

function diagramWarnings(diagram: DocsVisualArtifact["diagram_blocks"][number]): string[] {
  return diagram.warnings ?? [];
}

function provenanceLabel(diagram: DocsVisualArtifact["diagram_blocks"][number]) {
  const provenance = diagramProvenance(diagram);
  if (provenance === "heuristic") return { text: "AUTO GENERATED", bg: "#E8F5FF", color: "#165D8A" };
  if (provenance === "ai_draft") return { text: "AI DRAFT", bg: "#FFF0F0", color: "#A33A3A" };
  return { text: "AUTHORED", bg: "#ECF8E8", color: "#235C2B" };
}

function provenanceNote(diagram: DocsVisualArtifact["diagram_blocks"][number]): string | null {
  const provenance = diagramProvenance(diagram);
  const generator = diagram.generator ?? "";
  if (provenance === "heuristic") {
    return "이 다이어그램은 문서 구조를 바탕으로 자동 생성된 보조 시각화입니다. 기준 원문은 왼쪽 markdown 입니다.";
  }
  if (generator.startsWith("component-flow")) {
    return "이 다이어그램은 dependency graph가 아니라 구조 요약입니다.";
  }
  return null;
}

function getTrustPill(trustState: DocsTrustState) {
  if (trustState === "enhanced-synced") return { text: "SYNCED", bg: "#4DFF91", fg: "#1A1A1A" };
  if (trustState === "enhanced-stale") return { text: "STALE", bg: "#FFD166", fg: "#1A1A1A" };
  if (trustState === "enhanced-failed") return { text: "FAILED", bg: "#FF6B6B", fg: "#1A1A1A" };
  return { text: "MD ONLY", bg: "#E8E4D8", fg: "#1A1A1A" };
}

function sectionSummary(section: DocsVisualSection): string {
  return sentenceSlice(section.summary || `${section.title}에 대한 핵심 요약 섹션입니다.`, 1);
}

function phaseSections(artifact: DocsVisualArtifact): DocsVisualSection[] {
  const explicit = artifact.sections.filter((section) => /^phase\s*\d+/i.test(section.title));
  if (explicit.length > 0) return explicit.slice(0, 12);
  return artifact.sections.filter((section) => section.level <= 2).slice(0, 12);
}

function docDiagrams(artifact: DocsVisualArtifact) {
  return artifact.diagram_blocks
    .filter((diagram) => diagram.kind === "mermaid" && compact(diagram.source ?? ""))
    .slice(0, 6);
}

function keyRules(artifact: DocsVisualArtifact): string[] {
  const rules = [
    "markdown 원문이 항상 진짜 기준이다.",
    "enhancement는 source_hash가 맞을 때만 현재 상태로 신뢰한다.",
    "파생 데이터가 깨져도 원문 읽기는 멈추지 않는다.",
  ];
  if (artifact.diagram_blocks.length > 0) {
    rules.push("다이어그램은 보조 설명일 뿐이고, 실패하면 code block으로 바로 돌아간다.");
  }
  return rules;
}

function successCriteria(artifact: DocsVisualArtifact): string[] {
  const items = [
    "문서를 바로 열 수 있다.",
    "trust state를 보고 enhancement가 최신인지 바로 알 수 있다.",
    "fancy layer가 실패해도 markdown 읽기는 계속 유지된다.",
  ];
  if (artifact.action_items.length > 0) {
    items.push(`현재 문서에서 바로 행동으로 옮길 후보가 ${artifact.action_items.length}개 보인다.`);
  }
  return items;
}

function edgeCases(artifact: DocsVisualArtifact): string[] {
  const items = [
    "artifact missing / corrupt / stale 이어도 markdown-only fallback이 가능해야 한다.",
    "문서가 길어도 enhancement만 축약되고 reading은 유지되어야 한다.",
  ];
  if (artifactWarnings(artifact).length > 0) {
    items.push(`현재 artifact warning ${artifactWarnings(artifact).length}개도 함께 보여서 위험 신호를 놓치지 않게 한다.`);
  }
  return items;
}

function easyActionSummary(artifact: DocsVisualArtifact): string {
  const pending = artifact.action_items.filter((item) => !item.checked).map((item) => item.text);
  if (pending.length === 0) {
    return "급하게 처리해야 할 미완료 항목이 많지 않아 보여서, 큰 흐름을 먼저 읽는 데 집중하면 됩니다.";
  }
  return `당장 먼저 볼 일은 ${topItems(pending, 2).join(" 그리고 ")} 입니다. 즉, 이 문서는 설명문이면서 동시에 실행 체크리스트 역할도 합니다.`;
}

function glossarySummary(artifact: DocsVisualArtifact): string {
  const first = artifact.glossary[0];
  if (!first) {
    return "어려운 용어 사전이 따로 많지는 않지만, 섹션 제목과 원문을 같이 보면 뜻을 따라가기 쉽게 구성되어 있습니다.";
  }
  return `${first.term}는 ${compact(first.definition)}라는 뜻입니다. 기술 용어를 바로 옆에서 쉬운 말로 풀어주는 메모라고 보면 됩니다.`;
}

function sequenceSummary(artifact: DocsVisualArtifact): string {
  const steps = phaseSections(artifact).slice(0, 4).map((section) => section.title);
  if (steps.length < 2) {
    return "단계가 복잡하게 갈라지지는 않아서, 위에서 아래로 차례대로 읽는 방식이 가장 안전합니다.";
  }
  return `큰 흐름은 ${steps.join(" → ")} 순서입니다. 세부 문장을 다 기억하기보다 이 단계 이동만 잡고 읽으면 이해가 빨라집니다.`;
}

function fileRows(artifact: DocsVisualArtifact): Array<{ area: string; role: string; kind: string }> {
  return [
    { area: artifact.source_path.split("/").slice(-2).join("/"), role: "현재 보고 있는 source markdown", kind: "Truth" },
    { area: `${artifact.sections.length} sections`, role: "heading tree 기반 구조 요약", kind: "Derived" },
    { area: `${artifact.action_items.length} actions`, role: "checklist / 할 일 추출", kind: "Derived" },
    { area: `${artifact.diagram_blocks.length} diagrams`, role: "mermaid 다이어그램 메타", kind: "Derived" },
  ];
}

function SmallPill({ children, bg = "#F1ECDF", color = "#444" }: { children: string; bg?: string; color?: string }) {
  return (
    <span style={{ display: "inline-block", padding: "4px 10px", border: "2px solid #1A1A1A", background: bg, color, fontSize: 11, fontWeight: 800 }}>
      {children}
    </span>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 12 }}>{title}</div>
      {children}
    </div>
  );
}

function Rule({ children, tone = "#4D9FFF" }: { children: ReactNode; tone?: string }) {
  return (
    <div style={{ borderLeft: `4px solid ${tone}`, background: "#F6F1E3", padding: "9px 12px", fontSize: 13, lineHeight: 1.65 }}>
      {children}
    </div>
  );
}

function PhaseBox({ num, title, body, onClick }: { num: number; title: string; body: string; onClick?: () => void }) {
  return (
    <button className="card" onClick={onClick} style={{ padding: "12px 14px", background: "#FBF8EE", textAlign: "left", cursor: onClick ? "pointer" : "default", width: "100%" }}>
      <div style={{ fontSize: 10, color: "#777", fontWeight: 800, marginBottom: 4 }}>PHASE {num}</div>
      <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 12, lineHeight: 1.6, color: "#444" }}>{body}</div>
    </button>
  );
}

function BulletList({ items, icon = "•" }: { items: string[]; icon?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map((item, index) => (
        <div key={`${icon}-${index}`} style={{ fontSize: 12, lineHeight: 1.65, color: "#333" }}>{icon} {item}</div>
      ))}
    </div>
  );
}

export default function VisualSummaryPane({ artifact, trustState, onPhaseSelect }: VisualSummaryPaneProps) {
  const trust = getTrustPill(trustState);
  const phases = phaseSections(artifact);
  const diagrams = docDiagrams(artifact);
  const warnings = artifactWarnings(artifact);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Card title="Docs Viewer Execution Summary">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <SmallPill>{artifact.generated_at.slice(0, 10)}</SmallPill>
          <SmallPill bg={trust.bg} color={trust.fg}>{trust.text}</SmallPill>
          <SmallPill>{`${artifact.sections.length} sections`}</SmallPill>
          <SmallPill>{`${artifact.action_items.length} actions`}</SmallPill>
          <SmallPill>{`${artifact.diagram_blocks.length} diagrams`}</SmallPill>
        </div>
        <div style={{ fontSize: 22, fontWeight: 900, marginBottom: 8, lineHeight: 1.3 }}>{artifact.title}</div>
        <div style={{ fontSize: 13, lineHeight: 1.8, color: "#333", marginBottom: 14 }}>
          {sentenceSlice(artifact.summary || `${artifact.title} 문서를 쉽게 이해하도록 재정리한 패널입니다.`, 3)}
        </div>
        <Rule>
          <strong>아키텍처 한 줄:</strong> GUI는 markdown 원문을 바로 보여주고, 오른쪽 패널은 hash로 연결된 파생 artifact를 읽어 이해를 돕는 보조 시각화만 제공합니다.
        </Rule>
      </Card>

      <Card title={diagrams.length > 0 ? "문서 다이어그램" : "다이어그램 상태"}>
        {diagrams.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {diagrams.map((diagram, index) => (
              <div key={diagram.id} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <SmallPill>{`diagram ${index + 1}`}</SmallPill>
                  <SmallPill bg={provenanceLabel(diagram).bg} color={provenanceLabel(diagram).color}>{provenanceLabel(diagram).text}</SmallPill>
                  <SmallPill bg="#F5F0FF" color="#5B35CC">{diagramConfidence(diagram).toUpperCase()}</SmallPill>
                  {diagram.title ? <SmallPill bg="#EEE7FF" color="#5B35CC">{diagram.title}</SmallPill> : null}
                </div>
                {provenanceNote(diagram) ? <Rule tone="#7B4DFF">{provenanceNote(diagram)}</Rule> : null}
                {diagramWarnings(diagram).map((warning, warnIndex) => (
                  <Rule key={`${diagram.id}-warning-${warnIndex}`} tone="#FFD166"><strong>주의:</strong> {warning}</Rule>
                ))}
                <MermaidDiagram chart={diagram.source ?? ""} />
              </div>
            ))}
          </div>
        ) : (
          <Rule>
            이 문서에는 지금 표시할 Mermaid 다이어그램이 없습니다. 왼쪽 markdown이 기준 원문이고, 오른쪽은 hash로 연결된 파생 시각화만 보조적으로 보여줍니다.
          </Rule>
        )}
      </Card>

      <Card title="핵심 실행 규칙">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {keyRules(artifact).map((rule, idx) => (
            <Rule key={`rule-${idx}`} tone={idx === 2 ? "#F5621E" : idx === 1 ? "#4DFF91" : "#4D9FFF"}>{rule}</Rule>
          ))}
          {topItems(warnings, 2).map((warning, idx) => (
            <Rule key={`warn-${idx}`} tone="#FFD166"><strong>주의:</strong> {warning}</Rule>
          ))}
        </div>
      </Card>

      <Card title="한 번에 이해하기">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div className="card" style={{ padding: "12px 14px", background: "#FBF8EE" }}>
            <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 6 }}>왜 중요한지</div>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>{artifact.action_items.length > 0 ? "이 문서는 실제 실행 순서를 잡는 데 쓰이는 계획 문서에 가깝습니다." : "이 문서는 큰 방향과 구조를 빠르게 파악하게 해주는 기준 문서입니다."}</div>
          </div>
          <div className="card" style={{ padding: "12px 14px", background: "#FBF8EE" }}>
            <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 6 }}>지금 해야 할 일</div>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>{easyActionSummary(artifact)}</div>
          </div>
          <div className="card" style={{ padding: "12px 14px", background: "#FBF8EE" }}>
            <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 6 }}>어려운 용어 풀이</div>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>{glossarySummary(artifact)}</div>
          </div>
          <div className="card" style={{ padding: "12px 14px", background: "#FBF8EE" }}>
            <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 6 }}>구현 순서</div>
            <div style={{ fontSize: 12, lineHeight: 1.7 }}>{sequenceSummary(artifact)}</div>
          </div>
        </div>
      </Card>

      <Card title="실행 단계">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
          {phases.map((section, index) => (
            <PhaseBox key={section.id} num={index + 1} title={section.title} body={sectionSummary(section)} onClick={() => onPhaseSelect?.(section.id)} />
          ))}
        </div>
      </Card>

      <Card title="주요 구성 요소">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "8px 10px", borderBottom: "2px solid #1A1A1A", color: "#666" }}>영역</th>
                <th style={{ textAlign: "left", padding: "8px 10px", borderBottom: "2px solid #1A1A1A", color: "#666" }}>역할</th>
                <th style={{ textAlign: "left", padding: "8px 10px", borderBottom: "2px solid #1A1A1A", color: "#666" }}>종류</th>
              </tr>
            </thead>
            <tbody>
              {fileRows(artifact).map((row, index) => (
                <tr key={`${row.area}-${index}`}>
                  <td style={{ padding: "8px 10px", borderBottom: "1px solid #DDD" }}>{row.area}</td>
                  <td style={{ padding: "8px 10px", borderBottom: "1px solid #DDD" }}>{row.role}</td>
                  <td style={{ padding: "8px 10px", borderBottom: "1px solid #DDD" }}>{row.kind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Card title="검증해야 할 Edge Cases">
          <BulletList items={edgeCases(artifact)} />
        </Card>
        <Card title="Final Success Criteria">
          <BulletList items={successCriteria(artifact)} icon="✅" />
        </Card>
      </div>
    </div>
  );
}
