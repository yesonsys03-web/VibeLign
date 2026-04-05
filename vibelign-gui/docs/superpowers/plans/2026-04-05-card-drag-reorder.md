# Card Drag Reorder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈 화면 13개 카드를 드래그로 자유롭게 순서 변경하고, 앱 재시작 후에도 순서가 유지되도록 한다.

**Architecture:** dnd-kit으로 드래그 처리, tauri-plugin-store로 OS 표준 경로에 JSON 저장. 13개 카드를 하나의 flat `string[]` 배열로 관리하고 2열 CSS 그리드로 렌더링. `useCardOrder` 훅이 상태·저장을 캡슐화, Home.tsx는 배열 순서대로 카드를 렌더링.

**Tech Stack:** `@dnd-kit/core` `@dnd-kit/sortable` `@dnd-kit/utilities`, `@tauri-apps/plugin-store`, `tauri-plugin-store` (Rust crate v2)

---

## File Structure

| 파일 | 변경 | 역할 |
|------|------|------|
| `src/hooks/useCardOrder.ts` | 신규 | 카드 순서 상태 + store 읽기/쓰기 |
| `src/pages/Home.tsx` | 수정 | dnd-kit 래핑, 배열 기반 렌더링, 초기화 버튼 |
| `src-tauri/Cargo.toml` | 수정 | tauri-plugin-store crate 추가 |
| `src-tauri/src/lib.rs` | 수정 | 플러그인 등록 (.plugin 한 줄) |
| `package.json` | 수정 | npm 패키지 4개 추가 |

---

## Task 1: 의존성 설치

**Files:**
- Modify: `package.json`
- Modify: `src-tauri/Cargo.toml`

- [ ] **Step 1: npm 패키지 추가**

```bash
cd "vibelign-gui"
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities @tauri-apps/plugin-store
```

Expected: `package.json` dependencies에 4개 패키지 추가됨, `node_modules` 업데이트됨.

- [ ] **Step 2: Cargo.toml에 tauri-plugin-store 추가**

`src-tauri/Cargo.toml` 의 `[dependencies]` 섹션에 한 줄 추가:

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-opener = "2"
tauri-plugin-dialog = "2"
tauri-plugin-store = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

- [ ] **Step 3: Rust 의존성 다운로드 확인**

```bash
cd "vibelign-gui/src-tauri"
cargo fetch
```

Expected: 에러 없이 완료 (tauri-plugin-store crate 다운로드됨).

- [ ] **Step 4: TypeScript 컴파일 확인**

```bash
cd "vibelign-gui"
npm run build 2>&1 | head -20
```

Expected: dnd-kit 타입 인식됨, 빌드 에러 없음.

- [ ] **Step 5: 커밋**

```bash
cd "vibelign-gui"
git add package.json package-lock.json src-tauri/Cargo.toml src-tauri/Cargo.lock
git commit -m "chore: add dnd-kit and tauri-plugin-store dependencies"
```

---

## Task 2: Rust에 tauri-plugin-store 등록

**Files:**
- Modify: `src-tauri/src/lib.rs:699-701`

- [ ] **Step 1: lib.rs에 플러그인 등록**

`src-tauri/src/lib.rs` 의 `tauri::Builder::default()` 체인 (699번째 줄 근처)에 한 줄 추가:

```rust
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|_app| {
```

- [ ] **Step 2: Rust 컴파일 확인**

```bash
cd "vibelign-gui/src-tauri"
cargo check
```

Expected: `Compiling tauri-plugin-store ...` 가 나오고 최종적으로 에러 없이 완료.

- [ ] **Step 3: 커밋**

```bash
cd "vibelign-gui"
git add src-tauri/src/lib.rs
git commit -m "feat: register tauri-plugin-store plugin"
```

---

## Task 3: useCardOrder 훅 생성

**Files:**
- Create: `src/hooks/useCardOrder.ts`

- [ ] **Step 1: hooks 디렉토리 및 파일 생성**

`src/hooks/useCardOrder.ts` 를 아래 내용으로 생성:

```ts
// === ANCHOR: USE_CARD_ORDER_START ===
import { useEffect, useRef, useState } from "react";
import { load } from "@tauri-apps/plugin-store";

export const DEFAULT_CARD_ORDER = [
  "codemap", "guard", "checkpoint", "transfer",
  "history", "patch", "undo", "anchor",
  "explain", "ask", "export", "protect", "secrets",
] as const;

const STORE_PATH = "vibelign-gui.json";
const STORE_KEY = "card-order";

type StoreInstance = Awaited<ReturnType<typeof load>>;

export function useCardOrder() {
  const [cardOrder, setCardOrderState] = useState<string[]>([...DEFAULT_CARD_ORDER]);
  const storeRef = useRef<StoreInstance | null>(null);

  useEffect(() => {
    load(STORE_PATH, { autoSave: true }).then(async (s) => {
      storeRef.current = s;
      try {
        const saved = await s.get<string[]>(STORE_KEY);
        if (saved && Array.isArray(saved)) {
          const valid = saved.filter((id) => (DEFAULT_CARD_ORDER as readonly string[]).includes(id));
          const missing = DEFAULT_CARD_ORDER.filter((id) => !valid.includes(id));
          setCardOrderState([...valid, ...missing]);
        }
      } catch {
        // store 읽기 실패 시 기본 순서 유지
      }
    }).catch(() => {
      // store 열기 실패 시 기본 순서 유지
    });
  }, []);

  function saveOrder(order: string[]) {
    const s = storeRef.current;
    if (!s) return;
    s.set(STORE_KEY, order).catch(() => {});
  }

  function setCardOrder(order: string[]) {
    setCardOrderState(order);
    saveOrder(order);
  }

  function resetOrder() {
    setCardOrder([...DEFAULT_CARD_ORDER]);
  }

  return { cardOrder, setCardOrder, resetOrder };
}
// === ANCHOR: USE_CARD_ORDER_END ===
```

- [ ] **Step 2: TypeScript 컴파일 확인**

```bash
cd "vibelign-gui"
npx tsc --noEmit
```

Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
cd "vibelign-gui"
git add src/hooks/useCardOrder.ts
git commit -m "feat: add useCardOrder hook with tauri-plugin-store persistence"
```

---

## Task 4: Home.tsx 드래그 앤 드롭 적용

**Files:**
- Modify: `src/pages/Home.tsx`

이 태스크에서 Home.tsx의 홈 메인 뷰 전체를 교체한다. manual_list, manual_detail 뷰는 건드리지 않는다.

- [ ] **Step 1: Home.tsx 상단 import 교체**

파일 맨 위 import 블록을 아래로 교체:

```tsx
// === ANCHOR: HOME_START ===
import { type ReactNode, useState } from "react";
import {
  DndContext,
  DragEndEvent,
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
import { GuardResult } from "../lib/vib";
import { COMMANDS, GuideStep } from "../lib/commands";
import { useCardOrder } from "../hooks/useCardOrder";
import UndoCard from "../components/cards/backup/UndoCard";
import HistoryCard from "../components/cards/backup/HistoryCard";
import CheckpointCard from "../components/cards/backup/CheckpointCard";
import CodemapCard from "../components/cards/analysis/CodemapCard";
import GuardCard from "../components/cards/analysis/GuardCard";
import AnchorCard from "../components/cards/analysis/AnchorCard";
import PatchCard from "../components/cards/ai/PatchCard";
import ExplainCard from "../components/cards/ai/ExplainCard";
import AskCard from "../components/cards/ai/AskCard";
import TransferCard from "../components/cards/transfer/TransferCard";
import ExportCard from "../components/cards/transfer/ExportCard";
import ProtectCard from "../components/cards/security/ProtectCard";
import SecretsCard from "../components/cards/security/SecretsCard";
import pkg from "../../package.json";
```

- [ ] **Step 2: SortableCardWrapper 컴포넌트 추가**

`type View = ...` 선언 바로 위에 삽입:

```tsx
// ── 드래그 래퍼 ───────────────────────────────────────────────────────────────
function SortableCardWrapper({ id, children }: { id: string; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        cursor: isDragging ? "grabbing" : "grab",
        zIndex: isDragging ? 10 : undefined,
      }}
      {...attributes}
      {...listeners}
    >
      {children}
    </div>
  );
}
```

- [ ] **Step 3: renderCard 함수 추가**

`SortableCardWrapper` 아래, `type View` 위에 삽입:

```tsx
interface CardRenderProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey: boolean;
  aiKeyStatusLoaded: boolean;
  onNavigate: (page: "checkpoints") => void;
  onOpenSettings?: (reason?: string) => void;
  watchOn: boolean;
  setWatchOn: (v: boolean) => void;
  mapMode: "manual" | "auto";
  setMapMode: (v: "manual" | "auto") => void;
  onGuardResult: (r: GuardResult) => void;
}

function renderCard(id: string, p: CardRenderProps): ReactNode {
  switch (id) {
    case "codemap":    return <CodemapCard projectDir={p.projectDir} watchOn={p.watchOn} setWatchOn={p.setWatchOn} mapMode={p.mapMode} setMapMode={p.setMapMode} />;
    case "guard":      return <GuardCard projectDir={p.projectDir} onGuardResult={p.onGuardResult} />;
    case "checkpoint": return <CheckpointCard projectDir={p.projectDir} onNavigate={p.onNavigate} />;
    case "transfer":   return <TransferCard projectDir={p.projectDir} />;
    case "history":    return <HistoryCard projectDir={p.projectDir} />;
    case "patch":      return <PatchCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "undo":       return <UndoCard projectDir={p.projectDir} onNavigate={p.onNavigate} />;
    case "anchor":     return <AnchorCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "explain":    return <ExplainCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "ask":        return <AskCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "export":     return <ExportCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "protect":    return <ProtectCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    case "secrets":    return <SecretsCard projectDir={p.projectDir} apiKey={p.apiKey} providerKeys={p.providerKeys} hasAnyAiKey={p.hasAnyAiKey} aiKeyStatusLoaded={p.aiKeyStatusLoaded} onOpenSettings={p.onOpenSettings} />;
    default:           return null;
  }
}
```

- [ ] **Step 4: Home 컴포넌트 본문에 훅·핸들러 추가**

`Home` 함수 본문에서 기존 state 선언들 아래에 추가 (line 49 `setMapMode` 정의 바로 뒤):

```tsx
  const { cardOrder, setCardOrder, resetOrder } = useCardOrder();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = cardOrder.indexOf(String(active.id));
      const newIndex = cardOrder.indexOf(String(over.id));
      setCardOrder(arrayMove(cardOrder, oldIndex, newIndex));
    }
  }
```

- [ ] **Step 5: 홈 메인 뷰의 헤더에 초기화 버튼 추가**

Home.tsx 홈 메인 뷰 헤더 (line 284~307 근처)를 아래로 교체:

```tsx
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">HOME</span>
        <button
          className="btn btn-ghost btn-sm"
          onClick={resetOrder}
          style={{ fontSize: 10, padding: "2px 8px", border: "1.5px solid #ccc", color: "#888" }}
          title="카드 순서 초기화"
        >
          ↺
        </button>
        <div
          className="terminal"
          style={{
            padding: "6px 10px",
            fontSize: 10,
            fontWeight: 700,
            lineHeight: 1.4,
            flexShrink: 0,
          }}
          title="VibeLign GUI 버전"
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
            <div className="terminal-header" style={{ marginBottom: 0 }}>
              <div className="terminal-dot red" />
              <div className="terminal-dot yellow" />
              <div className="terminal-dot green" />
            </div>
            <span style={{ color: "#b8b4b0" }}>바이브라인</span>
            <span style={{ color: "#F5621E" }}>v{pkg.version}</span>
          </div>
        </div>
      </div>
```

- [ ] **Step 6: 홈 메인 뷰의 카드 그리드를 DndContext + 배열 렌더링으로 교체**

`<div className="page-content">` 안의 카드 그리드 전체 (line 310~370)를 아래로 교체:

```tsx
      <div className="page-content">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={cardOrder} strategy={rectSortingStrategy}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {cardOrder.map((id) => (
                <SortableCardWrapper key={id} id={id}>
                  {renderCard(id, {
                    projectDir,
                    apiKey,
                    providerKeys,
                    hasAnyAiKey,
                    aiKeyStatusLoaded,
                    onNavigate,
                    onOpenSettings,
                    watchOn,
                    setWatchOn,
                    mapMode,
                    setMapMode,
                    onGuardResult: (r) => { setGuardResult(r); setGuardModal(true); },
                  })}
                </SortableCardWrapper>
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
```

- [ ] **Step 7: TypeScript 컴파일 확인**

```bash
cd "vibelign-gui"
npx tsc --noEmit
```

Expected: 에러 없음.

- [ ] **Step 8: 린트 확인**

```bash
cd "vibelign-gui"
npm run lint
```

Expected: 에러 없음 (CodemapCard의 pre-existing react-hooks/exhaustive-deps 외).

- [ ] **Step 9: 커밋**

```bash
cd "vibelign-gui"
git add src/pages/Home.tsx src/hooks/useCardOrder.ts
git commit -m "feat: card drag-and-drop reorder with persistent store"
```

---

## Task 5: 빌드 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 전체 빌드 확인**

```bash
cd "vibelign-gui"
npm run build
```

Expected: TypeScript 컴파일 에러 없음, Vite 번들링 성공.

- [ ] **Step 2: 수동 동작 검증 체크리스트**

`npm run tauri dev` 실행 후 아래를 확인:

1. 홈 화면 카드가 정상 렌더링됨 (13개)
2. 카드를 드래그하면 다른 위치로 이동됨
3. 버튼 클릭(예: GUARD ▶)이 드래그 없이 정상 작동함 (`distance: 8` 덕분)
4. 앱을 재시작하면 변경된 순서가 유지됨
5. 헤더의 ↺ 버튼 클릭 시 기본 순서로 복원됨
6. ↺ 버튼 클릭 후 재시작해도 기본 순서 유지됨

- [ ] **Step 3: 최종 커밋**

변경 사항이 없으면 건너뜀. 있으면:

```bash
cd "vibelign-gui"
git add -p
git commit -m "fix: post-verification adjustments"
```
