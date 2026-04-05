# Card Drag Reorder Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈 화면의 카드를 드래그로 자유롭게 순서 변경하고, 앱 재시작 후에도 순서가 유지되도록 한다.

**Architecture:** 12개 카드를 하나의 플랫 배열(`cardOrder: string[]`)로 관리. dnd-kit으로 드래그 처리, tauri-plugin-store로 순서 영구 저장. 2열 CSS 그리드 레이아웃 유지.

**Tech Stack:** dnd-kit (`@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`), `@tauri-apps/plugin-store`, `tauri-plugin-store` (Rust crate)

---

## Scope

- 12개 카드 전체 자유 이동 (구역 구분 없음)
- 앱 재시작 후 순서 유지 (tauri-plugin-store)
- 초기화 버튼으로 기본 순서 복원
- Mac / Windows / Linux 동일 동작

## Files

### New
- `src/hooks/useCardOrder.ts` — 카드 순서 상태 관리 + tauri-plugin-store 읽기/쓰기

### Modified
- `src/pages/Home.tsx` — dnd-kit DndContext + SortableContext 래핑, 배열 기반 렌더링, 초기화 버튼 추가
- `src-tauri/Cargo.toml` — `tauri-plugin-store = "2"` 추가
- `src-tauri/src/lib.rs` — `.plugin(tauri_plugin_store::Builder::default().build())` 등록
- `package.json` — dnd-kit 3개 패키지 + @tauri-apps/plugin-store 추가

## Card ID Mapping

```ts
const DEFAULT_CARD_ORDER = [
  "codemap", "guard", "checkpoint", "transfer",
  "history", "patch", "undo", "anchor",
  "explain", "ask", "export", "protect", "secrets",
];
```

각 ID는 Home.tsx 내 컴포넌트 매핑 테이블(`CARD_COMPONENTS`)로 카드 컴포넌트에 연결.

## Data Flow

```
앱 시작
  → useCardOrder: tauri-plugin-store에서 "card-order" 키 읽기
  → 없으면 DEFAULT_CARD_ORDER 사용
  → cardOrder 상태 초기화

카드 드래그 완료 (onDragEnd)
  → arrayMove()로 cardOrder 배열 재정렬
  → setCardOrder() 호출
  → tauri-plugin-store에 저장 (키: "card-order")

초기화 버튼 클릭
  → setCardOrder(DEFAULT_CARD_ORDER)
  → tauri-plugin-store에 DEFAULT_CARD_ORDER 저장
```

저장 파일: OS 표준 앱 데이터 경로의 `vibelign-gui.json`
- macOS: `~/Library/Application Support/{bundle_id}/vibelign-gui.json`
- Windows: `%APPDATA%\{bundle_id}\vibelign-gui.json`
- Linux: `~/.config/{bundle_id}/vibelign-gui.json`

## Component Structure

### `useCardOrder` hook

```ts
// 반환값
{
  cardOrder: string[],
  setCardOrder: (order: string[]) => void,
  resetOrder: () => void,
  isLoaded: boolean,
}
```

- 마운트 시 store에서 읽기 (비동기)
- `isLoaded`가 false인 동안 Home.tsx는 기본 순서로 렌더링 (깜빡임 방지)
- store 읽기/쓰기 실패 시 조용히 폴백 (에러 표시 없음)

### Home.tsx 변경

- `DndContext` (onDragEnd 핸들러 포함) + `SortableContext`로 카드 그리드 감싸기
- 각 카드를 `SortableCardWrapper` (id prop 받는 얇은 래퍼)로 감싸기
- 드래그 중 오버레이: 반투명 + 살짝 들린 효과 (dnd-kit DragOverlay)
- 상단 헤더 오른쪽에 "↺ 순서 초기화" 고스트 버튼 추가

## Error Handling

| 상황 | 처리 |
|------|------|
| store 읽기 실패 | DEFAULT_CARD_ORDER로 폴백, 에러 표시 없음 |
| store 쓰기 실패 | 무시 (드래그는 정상 동작) |
| 저장된 배열에 알 수 없는 카드 ID | 필터링 후 누락된 카드를 기본 순서 뒤에 추가 |

## Non-Goals

- 카드 추가/삭제 기능 없음
- 모바일 터치 최적화 없음 (데스크탑 앱)
- 그리드 컬럼 수 변경 기능 없음
