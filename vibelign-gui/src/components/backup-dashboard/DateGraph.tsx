import { useRef, useState, type PointerEvent } from "react";
import type { TimelinePoint } from "./model";

interface DateGraphProps {
  points: TimelinePoint[];
}

interface DragState {
  pointerX: number;
  scrollLeft: number;
}

const ZOOM_LEVELS = [1, 1.5, 2.25, 3.25];

export default function DateGraph({ points }: DateGraphProps) {
  const [zoomIndex, setZoomIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const zoom = ZOOM_LEVELS[zoomIndex];

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
    <section className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#E7F0FF", padding: "12px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#3D7DFF", borderColor: "#1A1A1A", color: "#fff" }}>📅</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 900, fontSize: 17 }}>타임라인 저장</div>
          <div style={{ fontSize: 11, color: "#555" }}>저장한 순간을 날짜와 시간 순서로 보여 줘요.</div>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setZoomIndex((value) => Math.max(0, value - 1))} disabled={zoomIndex === 0}>-</button>
          <button className="btn btn-ghost btn-sm" onClick={() => setZoomIndex((value) => Math.min(ZOOM_LEVELS.length - 1, value + 1))} disabled={zoomIndex === ZOOM_LEVELS.length - 1}>+</button>
        </div>
      </div>
      <div className="feature-card-body" style={{ display: "grid", gap: 8 }}>
        {points.length === 0 ? <span style={{ fontSize: 12, color: "#666" }}>아직 그릴 내용이 없어요.</span> : (
          <div
            ref={scrollRef}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerEnd}
            onPointerCancel={handlePointerEnd}
            style={{ overflowX: "auto", cursor: "grab", touchAction: "pan-y", userSelect: "none" }}
          >
            <div style={{ minWidth: `${Math.round(520 * zoom)}px`, height: 180, position: "relative", background: "#56BDEB", border: "2px solid #1A1A1A", boxShadow: "4px 4px 0 #1A1A1A" }}>
              <div style={{ position: "absolute", inset: "18px 24px 48px", borderBottom: "3px solid #FEFBF0" }} />
              {points.map((point) => <TimelineMark key={point.id} point={point} />)}
              <div style={{ position: "absolute", left: 0, right: 0, bottom: 10, textAlign: "center", fontSize: 18, fontWeight: 900 }}>날짜 · 시간</div>
            </div>
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#555", fontWeight: 700 }}>
          <span>드래그: 좌우 이동</span>
          <span>+ / -: 확대·축소</span>
        </div>
      </div>
    </section>
  );
}

function TimelineMark({ point }: { point: TimelinePoint }) {
  const color = point.sourceKind === "auto" ? "#FEFBF0" : "#FFD84D";
  return (
    <div title={point.detailLabel} style={{ position: "absolute", left: `${point.position}%`, bottom: 50, transform: "translateX(-50%)", display: "grid", justifyItems: "center", gap: 5 }}>
      <div style={{ width: 14, height: 96, background: color, border: "2px solid #1A1A1A", boxShadow: "2px 2px 0 #1A1A1A" }} />
      <div style={{ fontSize: 10, fontWeight: 900, color: "#1A1A1A", background: "#FEFBF0", border: "1px solid #1A1A1A", padding: "1px 4px" }}>{point.timeLabel}</div>
      <div style={{ fontSize: 10, fontWeight: 800 }}>{point.dateLabel}</div>
    </div>
  );
}
