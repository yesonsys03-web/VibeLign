// === ANCHOR: ADVANCEDHOMECARDS_START ===
import type { ReactNode } from "react";
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { GuardResult } from "../../lib/vib";
import UndoCard from "../cards/backup/UndoCard";
import HistoryCard from "../cards/backup/HistoryCard";
import CheckpointCard from "../cards/backup/CheckpointCard";
import CodemapCard from "../cards/analysis/CodemapCard";
import GuardCard from "../cards/analysis/GuardCard";
import AnchorCard from "../cards/analysis/AnchorCard";
import ExplainCard from "../cards/ai/ExplainCard";
import AskCard from "../cards/ai/AskCard";
import TransferCard from "../cards/transfer/TransferCard";
import ExportCard from "../cards/transfer/ExportCard";
import ProtectCard from "../cards/security/ProtectCard";
import SecretsCard from "../cards/security/SecretsCard";
import SessionMemoryCard from "../agent-memory/SessionMemoryCard";
import RecoveryOptionsCard from "../agent-memory/RecoveryOptionsCard";

interface AdvancedHomeCardsProps {
  readonly projectDir: string;
  readonly apiKey?: string | null;
  readonly providerKeys?: Record<string, string>;
  readonly hasAnyAiKey: boolean;
  readonly aiKeyStatusLoaded: boolean;
  readonly cardOrder: readonly string[];
  readonly onCardOrderChange: (cardOrder: readonly string[]) => void;
  readonly onNavigate: (page: "backups") => void;
  readonly onOpenSettings?: (reason?: string) => void;
  readonly watchOn: boolean;
  readonly onWatchChange: (watchOn: boolean) => void;
  readonly mapMode: "manual" | "auto";
  readonly onMapModeChange: (mapMode: "manual" | "auto") => void;
  readonly onGuardResult: (guardResult: GuardResult) => void;
}

interface CardRenderProps extends AdvancedHomeCardsProps {
  readonly cardId: string;
}

const RENDERABLE_ADVANCED_CARD_IDS = new Set([
  "codemap", "guard", "checkpoint", "transfer",
  "session-memory", "recovery-options", "history", "undo", "anchor",
  "explain", "ask", "export", "protect", "secrets",
]);

// === ANCHOR: ADVANCEDHOMECARDS_SORTABLECARDWRAPPER_START ===
function SortableCardWrapper({ id, children }: { readonly id: string; readonly children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        zIndex: isDragging ? 10 : undefined,
        position: "relative",
        height: "100%",
        width: "100%",
        minWidth: 0,
      }}
      {...attributes}
    >
      <div
        {...listeners}
        style={{
          position: "absolute",
          top: 4,
          right: 4,
          width: 20,
          height: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: isDragging ? "grabbing" : "grab",
          color: isDragging ? "#1A1A1A" : "#bbb",
          fontSize: 12,
          fontWeight: 900,
          borderRadius: 3,
          background: isDragging ? "#FFD16644" : "transparent",
          zIndex: 5,
          userSelect: "none",
          touchAction: "none",
        }}
        title="드래그하여 카드 이동"
      >
        ⠿
      </div>
      {children}
    </div>
  );
}
// === ANCHOR: ADVANCEDHOMECARDS_SORTABLECARDWRAPPER_END ===

// === ANCHOR: ADVANCEDHOMECARDS_RENDERADVANCEDCARD_START ===
function renderAdvancedCard(props: CardRenderProps): ReactNode {
  switch (props.cardId) {
    case "codemap": return <CodemapCard projectDir={props.projectDir} watchOn={props.watchOn} setWatchOn={props.onWatchChange} mapMode={props.mapMode} setMapMode={props.onMapModeChange} apiKey={props.apiKey} providerKeys={props.providerKeys} />;
    case "guard": return <GuardCard projectDir={props.projectDir} onGuardResult={props.onGuardResult} />;
    case "checkpoint": return <CheckpointCard projectDir={props.projectDir} onNavigate={props.onNavigate} />;
    case "transfer": return <TransferCard projectDir={props.projectDir} />;
    case "session-memory": return <SessionMemoryCard projectDir={props.projectDir} />;
    case "recovery-options": return <RecoveryOptionsCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} />;
    case "history": return <HistoryCard projectDir={props.projectDir} />;
    case "undo": return <UndoCard projectDir={props.projectDir} onNavigate={props.onNavigate} />;
    case "anchor": return <AnchorCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    case "explain": return <ExplainCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    case "ask": return <AskCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    case "export": return <ExportCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    case "protect": return <ProtectCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    case "secrets": return <SecretsCard projectDir={props.projectDir} apiKey={props.apiKey} providerKeys={props.providerKeys} hasAnyAiKey={props.hasAnyAiKey} aiKeyStatusLoaded={props.aiKeyStatusLoaded} onOpenSettings={props.onOpenSettings} />;
    default: return null;
  }
}
// === ANCHOR: ADVANCEDHOMECARDS_RENDERADVANCEDCARD_END ===

// === ANCHOR: ADVANCEDHOMECARDS_ADVANCEDHOMECARDS_START ===
export function AdvancedHomeCards(props: AdvancedHomeCardsProps) {
  const cardOrder = props.cardOrder.filter((cardId) => RENDERABLE_ADVANCED_CARD_IDS.has(cardId));
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  // === ANCHOR: ADVANCEDHOMECARDS_HANDLEDRAGEND_START ===
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = props.cardOrder.indexOf(String(active.id));
      const newIndex = props.cardOrder.indexOf(String(over.id));
      props.onCardOrderChange(arrayMove([...props.cardOrder], oldIndex, newIndex));
    }
  }
  // === ANCHOR: ADVANCEDHOMECARDS_HANDLEDRAGEND_END ===

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={cardOrder} strategy={rectSortingStrategy}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {cardOrder.map((cardId) => (
            <SortableCardWrapper key={cardId} id={cardId}>
              {renderAdvancedCard({ ...props, cardId })}
            </SortableCardWrapper>
          ))}
        </div>
      </SortableContext>
    </DndContext>
// === ANCHOR: ADVANCEDHOMECARDS_ADVANCEDHOMECARDS_END ===
  );
}
// === ANCHOR: ADVANCEDHOMECARDS_END ===
