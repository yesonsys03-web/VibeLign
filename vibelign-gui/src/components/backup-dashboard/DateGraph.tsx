import { useRef, useState, type PointerEvent } from "react";
import BackupCard from "./BackupCard";
import type { TimelinePoint } from "./model";

interface DateGraphProps {
  points: TimelinePoint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

interface DragState {
  pointerX: number;
  scrollLeft: number;
}

const ZOOM_LEVELS = [1, 1.5, 2.25, 3.25];
const TRACK_HEIGHT = 214;
const PLOT_INSET = 26;
const BASELINE_BOTTOM = 64;

export default function DateGraph({ points, selectedId, onSelect }: DateGraphProps) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const [activeId, setActiveId] = useState(points[points.length - 1]?.id ?? "");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const zoom = ZOOM_LEVELS[zoomIndex];
  const activePoint = points.find((point) => point.id === selectedId) ?? points.find((point) => point.id === activeId) ?? points[points.length - 1];
  const tickEvery = points.length > 18 ? 6 : points.length > 10 ? 4 : points.length > 5 ? 2 : 1;

  function handleSelect(id: string) {
    setActiveId(id);
    onSelect(id);
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!scrollRef.current) return;
    dragRef.current = { pointerX: event.clientX, scrollLeft: scrollRef.current.scrollLeft };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!scrollRef.current || !dragRef.current) return;
    scrollRef.current.scrollLeft = dragRef.current.scrollLeft - (event.clientX - dragRef.current.pointerX);
  }

  function handlePointerEnd() {
    dragRef.current = null;
  }

  return (
    <BackupCard
      icon="📅"
      title="타임라인 저장"
      subtitle="저장한 순간을 날짜와 시간 순서로 보여 줘요."
      headerStyle={{ background: "#E7F0FF", padding: "12px 14px" }}
      iconStyle={{ background: "#3D7DFF", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gap: 8 }}
      actions={
        <>
          <button className="btn btn-ghost btn-sm" onClick={() => setZoomIndex((value) => Math.max(0, value - 1))} disabled={zoomIndex === 0}>-</button>
          <button className="btn btn-ghost btn-sm" onClick={() => setZoomIndex((value) => Math.min(ZOOM_LEVELS.length - 1, value + 1))} disabled={zoomIndex === ZOOM_LEVELS.length - 1}>+</button>
        </>
      }
    >
      {points.length === 0 ? <span style={{ fontSize: 12, color: "#666" }}>아직 그릴 내용이 없어요.</span> : (
        <div
          ref={scrollRef}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerEnd}
          onPointerCancel={handlePointerEnd}
          style={{ overflowX: "auto", cursor: "grab", touchAction: "pan-y", userSelect: "none", paddingBottom: 4 }}
        >
          <div style={{ minWidth: `${Math.round(560 * zoom)}px`, height: TRACK_HEIGHT, position: "relative", background: "#DDF4FF", border: "2px solid #1A1A1A", boxShadow: "4px 4px 0 #1A1A1A", overflow: "hidden" }}>
            <div style={trackPanelStyle} />
            <div style={baselineStyle} />
            {points.map((point, index) => (
              <TimelineTick key={`tick-${point.id}`} point={point} index={index} tickEvery={tickEvery} />
            ))}
            {points.map((point, index) => (
              <TimelineMark key={point.id} point={point} index={index} active={point.id === activePoint?.id} onSelect={() => handleSelect(point.id)} />
            ))}
            <div style={axisTitleStyle}>오래된 저장본 → 최신 저장본</div>
          </div>
        </div>
      )}
      {activePoint ? (
        <div style={summaryStyle}>
          <span style={{ fontWeight: 900 }}>선택된 저장</span>
          <span>{activePoint.dateLabel} {activePoint.timeLabel}</span>
          <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{activePoint.detailLabel}</span>
        </div>
      ) : null}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#555", fontWeight: 700 }}>
        <span>점을 클릭하면 저장 정보를 고정해요</span>
        <span>드래그 이동 · + / - 확대</span>
      </div>
    </BackupCard>
  );
}

function TimelineMark({ point, index, active, onSelect }: { point: TimelinePoint; index: number; active: boolean; onSelect: () => void }) {
  const color = active ? "#FFD84D" : point.sourceKind === "auto" ? "#FFFFFF" : "#FFD84D";
  const laneOffset = index % 2 === 0 ? 0 : 28;
  function handlePointerDown(event: PointerEvent<HTMLButtonElement>) {
    event.stopPropagation();
  }

  return (
    <button
      type="button"
      title={point.detailLabel}
      aria-label={point.detailLabel}
      onPointerDown={handlePointerDown}
      onClick={onSelect}
      style={{
        position: "absolute",
        left: `${point.position}%`,
        bottom: BASELINE_BOTTOM + laneOffset,
        transform: "translateX(-50%)",
        display: "grid",
        justifyItems: "center",
        gap: 4,
        border: 0,
        background: "transparent",
        padding: 0,
        cursor: "pointer",
      }}
    >
      <span style={{ width: 2, height: 40 + laneOffset, background: "#1A1A1A", opacity: 0.55 }} />
      <span style={{ width: active ? 18 : 13, height: active ? 18 : 13, background: color, border: "2px solid #1A1A1A", boxShadow: active ? "3px 3px 0 #1A1A1A" : "2px 2px 0 rgba(26, 26, 26, 0.75)", borderRadius: 999 }} />
      <span style={{ fontSize: 10, fontWeight: 900, color: "#1A1A1A", background: active ? "#FFD84D" : "#FEFBF0", border: "1px solid #1A1A1A", padding: "1px 4px", whiteSpace: "nowrap" }}>{point.timeLabel}</span>
    </button>
  );
}

function TimelineTick({ point, index, tickEvery }: { point: TimelinePoint; index: number; tickEvery: number }) {
  if (index % tickEvery !== 0) return null;
  return (
    <div style={{ position: "absolute", left: `${point.position}%`, bottom: 28, transform: "translateX(-50%)", display: "grid", justifyItems: "center", gap: 4 }}>
      <span style={{ width: 2, height: 12, background: "#1A1A1A" }} />
      <span style={{ fontSize: 10, fontWeight: 900, color: "#1A1A1A", background: "#FEFBF0", border: "1px solid #1A1A1A", padding: "1px 5px", whiteSpace: "nowrap" }}>{point.dateLabel}</span>
    </div>
  );
}

const trackPanelStyle = {
  position: "absolute" as const,
  left: PLOT_INSET,
  right: PLOT_INSET,
  top: 18,
  bottom: 28,
  background: "repeating-linear-gradient(90deg, rgba(255,255,255,0.68) 0 1px, transparent 1px 56px), linear-gradient(180deg, #BFEAFF 0%, #8DD7F8 100%)",
  border: "2px solid #1A1A1A",
};

const baselineStyle = {
  position: "absolute" as const,
  left: PLOT_INSET + 8,
  right: PLOT_INSET + 8,
  bottom: BASELINE_BOTTOM,
  height: 4,
  background: "#1A1A1A",
};

const axisTitleStyle = {
  position: "absolute" as const,
  left: PLOT_INSET,
  right: PLOT_INSET,
  bottom: 8,
  textAlign: "center" as const,
  fontSize: 12,
  fontWeight: 900,
  color: "#1A1A1A",
};

const summaryStyle = {
  display: "grid",
  gridTemplateColumns: "auto auto minmax(0, 1fr)",
  gap: 8,
  alignItems: "center",
  border: "2px solid #1A1A1A",
  background: "#FEFBF0",
  boxShadow: "2px 2px 0 #1A1A1A",
  padding: "7px 9px",
  fontSize: 11,
};
