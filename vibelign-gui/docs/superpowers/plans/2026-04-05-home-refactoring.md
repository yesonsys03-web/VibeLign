# Home.tsx 리팩토링 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Home.tsx (1954줄)를 레이아웃 셸 + 13개 카드 컴포넌트로 분리한다.

**Architecture:** 공유 유틸리티(COMMANDS 데이터, GuiCliOutputBlock)를 먼저 추출하고, 카드를 하나씩 순차 추출한다. 각 카드는 자신의 상태(loading/output/error)를 직접 관리한다. Home.tsx는 watchOn/mapMode 등 앱 레벨 상태와 레이아웃만 유지한다.

**Tech Stack:** React 19, TypeScript, Tauri 2, Vite

**검증 명령어:**
```bash
cd vibelign-gui
npm run build   # TypeScript 컴파일 + Vite 빌드
npm run lint    # ESLint
```
빌드 오류 0개, 린트 오류 0개가 각 태스크의 완료 기준이다.

---

## 파일 구조 (완료 후)

```
src/
  lib/
    commands.ts                       # COMMANDS 배열, 타입, buildCmdArgs (신규)
    vib.ts                            # 기존 유지
  components/
    GuiCliOutputBlock.tsx             # CLI 출력 블록 (신규)
    cards/
      backup/
        CheckpointCard.tsx
        HistoryCard.tsx
        UndoCard.tsx
      analysis/
        GuardCard.tsx
        CodemapCard.tsx
        AnchorCard.tsx
      ai/
        PatchCard.tsx
        AskCard.tsx
        ExplainCard.tsx
      transfer/
        TransferCard.tsx
        ExportCard.tsx
      security/
        SecretsCard.tsx
        ProtectCard.tsx
  pages/
    Home.tsx                          # 레이아웃·뷰 전환만 (~200줄로 축소)
```

---

## Task 1: 공유 타입·COMMANDS 데이터 추출

**Files:**
- Create: `src/lib/commands.ts`
- Modify: `src/pages/Home.tsx` (import 교체)

### 배경
`FlagDef`, `GuideLine`, `GuideStep`, `COMMANDS`, `PATCH_COMMAND`, `buildCmdArgs` 가 현재 Home.tsx 상단에 있다. 카드들이 이를 import해야 하므로 먼저 분리한다.

- [ ] **Step 1: `src/lib/commands.ts` 생성**

```typescript
// === ANCHOR: COMMANDS_START ===
import { runVib, pickFile, buildGuiAiEnv } from "./vib";

export type CardState = "idle" | "loading" | "done" | "error";

export type FlagDef =
  | { type: "bool"; key: string; label: string }
  | { type: "text"; key: string; label: string; placeholder?: string; required?: boolean; numeric?: boolean }
  | { type: "select"; key: string; label: string; required?: boolean; options: { v: string; l: string }[] };

export type GuideLine = { t: "info" | "code" | "label" | "error" | "warn"; v: string };
export type GuideStep = { step: string; title: string; subtitle?: string; optional?: boolean; warn?: string; lines: GuideLine[] };

export const COMMANDS = [
  // ── 이 배열 전체를 Home.tsx의 COMMANDS 배열에서 그대로 복사한다 ──
  // Home.tsx line 32 ~ line 963 의 COMMANDS 배열 내용을 붙여넣기
];

export const PATCH_COMMAND = COMMANDS.find((c) => c.name === "patch")!;

/**
 * 커맨드 이름과 플래그 값으로 vib CLI 인수 배열을 만든다.
 * 필수 플래그가 누락되면 null을 반환한다.
 */
export function buildCmdArgs(
  name: string,
  cmdFlagValues: Record<string, Record<string, string | boolean>>
): string[] | null {
  const cmd = COMMANDS.find((c) => c.name === name);
  const flags = (cmd as any)?.flags as FlagDef[] | undefined;
  if (!flags?.length) return [name];

  const fvals = cmdFlagValues[name] ?? {};
  const args: string[] = [name];
  let positional: string | null = null;

  for (const fd of flags) {
    const val: string | boolean =
      fvals[fd.key] ??
      (fd.type === "bool"
        ? false
        : fd.type === "select" && fd.options.length > 0
          ? fd.options[0].v
          : "");
    if (fd.key === "_mode" || fd.key === "_action") {
      if (val) args.push(...String(val).split(" ").filter(Boolean));
    } else if (fd.key === "_file" || fd.key === "_request" || fd.key === "_tool") {
      if (val) positional = String(val).trim();
    } else if (fd.key === "_question") {
      if (val) args.push(String(val).trim());
    } else if (fd.type === "bool" && val) {
      args.push(`--${fd.key}`);
    } else if (fd.type === "text" && val) {
      if (fd.numeric && isNaN(Number(String(val)))) continue;
      args.push(`--${fd.key}`, String(val));
    }
  }

  for (const fd of flags) {
    if ((fd as any).required) {
      const val = fvals[fd.key] ?? "";
      if (!val) return null;
    }
  }

  if (positional) args.splice(1, 0, positional);
  return args;
}
// === ANCHOR: COMMANDS_END ===
```

> **주의:** `COMMANDS` 배열 내용은 Home.tsx line 32~963에서 그대로 복사한다. 수정하지 않는다.

- [ ] **Step 2: Home.tsx 상단 import에 commands.ts 추가**

Home.tsx line 2 import 구문에 추가:
```typescript
import { COMMANDS, PATCH_COMMAND, FlagDef, GuideLine, GuideStep, CardState, buildCmdArgs } from "../lib/commands";
```

그리고 Home.tsx에서 다음을 제거한다:
- `type CardState = ...` (line 7)
- `type FlagDef = ...` (line 9~12)
- `type GuideLine = ...` (line 13)
- `type GuideStep = ...` (line 14)
- `const COMMANDS = [...]` (line 32~963)
- `const PATCH_COMMAND = ...` (line 965)
- `function buildCmdArgs(...)` (line 1139~1179)

- [ ] **Step 3: 빌드 검증**

```bash
cd vibelign-gui && npm run build
```
예상: 오류 없이 성공. 실패 시 타입 불일치 확인 후 수정.

- [ ] **Step 4: 린트 검증**

```bash
cd vibelign-gui && npm run lint
```
예상: 오류 없이 통과.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/lib/commands.ts src/pages/Home.tsx
git commit -m "refactor: COMMANDS·타입·buildCmdArgs를 lib/commands.ts로 분리"
```

---

## Task 2: GuiCliOutputBlock 컴포넌트 추출

**Files:**
- Create: `src/components/GuiCliOutputBlock.tsx`
- Modify: `src/pages/Home.tsx` (import 교체)

### 배경
`GuiCliOutputBlock`은 여러 카드에서 공통으로 사용한다. 먼저 분리해야 카드 컴포넌트들이 import할 수 있다.

- [ ] **Step 1: `src/components/GuiCliOutputBlock.tsx` 생성**

Home.tsx line 967~1031의 함수를 그대로 복사한다:

```typescript
// === ANCHOR: GUI_CLI_OUTPUT_BLOCK_START ===
import { useState, useEffect } from "react";

/** CLI stdout/stderr와 동일한 본문을 그대로 보여 주는 터미널 스타일 블록 (줄바꿈·공백 유지). */
export default function GuiCliOutputBlock({
  text,
  placeholder,
  variant = "default",
}: {
  text: string;
  placeholder: string;
  variant?: "default" | "error" | "warn";
}) {
  const [folded, setFolded] = useState(false);
  const trimmed = text.trim();

  useEffect(() => {
    setFolded(false);
  }, [text]);

  if (!trimmed) {
    if (!placeholder) return null;
    return (
      <div style={{ fontSize: 15, color: "#555", marginBottom: 6, lineHeight: 1.35 }}>
        {placeholder}
      </div>
    );
  }
  const color = variant === "error" ? "#FF4D4D" : variant === "warn" ? "#A05A00" : "#1A1A1A";
  return (
    <div style={{ margin: "0 0 8px 0" }}>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setFolded((f) => !f)}
          style={{ fontSize: 9, fontWeight: 700, padding: "2px 10px", border: "2px solid #1A1A1A", cursor: "pointer" }}
        >
          {folded ? "펼치기" : "접기"}
        </button>
      </div>
      {!folded && (
        <pre
          style={{
            margin: 0,
            padding: "8px 10px",
            maxHeight: 280,
            overflowY: "auto",
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 10,
            lineHeight: 1.45,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            background: "#fff",
            border: "2px solid #1A1A1A",
            color,
            boxSizing: "border-box",
          }}
        >
          {text}
        </pre>
      )}
      {folded && (
        <div style={{ fontSize: 10, color: "#888", fontWeight: 600, padding: "4px 2px 0" }}>결과가 접혀 있어요.</div>
      )}
    </div>
  );
}
// === ANCHOR: GUI_CLI_OUTPUT_BLOCK_END ===
```

- [ ] **Step 2: Home.tsx에서 GuiCliOutputBlock import 교체**

Home.tsx 상단 import에 추가:
```typescript
import GuiCliOutputBlock from "../components/GuiCliOutputBlock";
```

Home.tsx에서 `function GuiCliOutputBlock` 정의 블록(line 967~1031)을 삭제한다.

- [ ] **Step 3: 빌드 검증**

```bash
cd vibelign-gui && npm run build
```
예상: 오류 없이 성공.

- [ ] **Step 4: 커밋**

```bash
cd vibelign-gui
git add src/components/GuiCliOutputBlock.tsx src/pages/Home.tsx
git commit -m "refactor: GuiCliOutputBlock을 독립 컴포넌트로 분리"
```

---

## Task 3: UndoCard 추출 (backup/)

**Files:**
- Create: `src/components/cards/backup/UndoCard.tsx`
- Modify: `src/pages/Home.tsx`

### 배경
undo 카드는 `handleRunCmd("undo")`를 호출하면 체크포인트 탭으로 이동만 한다. 가장 단순한 카드.

- [ ] **Step 1: `src/components/cards/backup/UndoCard.tsx` 생성**

```typescript
// === ANCHOR: UNDO_CARD_START ===
import { useState } from "react";
import { runVib } from "../../../lib/vib";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";
import { COMMANDS, CardState } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "undo")!;

interface UndoCardProps {
  projectDir: string;
  onNavigate: (page: "checkpoints") => void;
}

export default function UndoCard({ onNavigate }: UndoCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [out, setOut] = useState("");
  const hasWarning = false;

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: CMD.color + "18", padding: "8px 12px" }}>
        <div className="feature-card-icon" style={{
          background: CMD.color, color: "#fff", borderColor: CMD.color,
          width: 22, height: 22, fontSize: 11, fontWeight: 900,
        }}>{CMD.icon}</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{CMD.title}</span>
          <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{CMD.short}</span>
        </div>
        {(st === "done" || (st === "idle" && out)) && !hasWarning && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
        {st === "error" && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
        <GuiCliOutputBlock text={out} placeholder={CMD.short} variant={st === "error" ? "error" : "default"} />
        <button
          className="btn btn-sm"
          style={{ width: "100%", background: CMD.color, color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
          disabled={st === "loading"}
          onClick={() => onNavigate("checkpoints")}
        >
          UNDO ▶
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: UNDO_CARD_END ===
```

- [ ] **Step 2: Home.tsx 커맨드 섹션 EXCLUDE 목록에 "undo" 추가**

Home.tsx의 EXCLUDE 배열을 찾아 `"undo"`를 추가한다:
```typescript
const EXCLUDE = ["scan","watch","guard","checkpoint","transfer","history","patch","start","doctor","config","rules","install","manual","policy","undo"];
```

- [ ] **Step 3: Home.tsx에 UndoCard import 후 커맨드 그리드 앞에 삽입**

```typescript
import UndoCard from "../components/cards/backup/UndoCard";
```

커맨드 섹션 `<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>` 안에 첫 번째로 삽입:
```tsx
<UndoCard key="undo" projectDir={projectDir} onNavigate={onNavigate} />
```

- [ ] **Step 4: 빌드 검증**

```bash
cd vibelign-gui && npm run build
```
예상: 오류 없이 성공.

- [ ] **Step 5: 런타임 검증**

```bash
cd vibelign-gui && npm run dev
```
홈 화면에서 "되돌리기" 카드가 정상 렌더링되고, 버튼 클릭 시 Checkpoints 탭으로 이동하는지 확인.

- [ ] **Step 6: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/backup/UndoCard.tsx src/pages/Home.tsx
git commit -m "refactor: UndoCard 컴포넌트 추출 (backup/)"
```

---

## Task 4: GenericCommandCard 추출 (나머지 단순 카드)

**Files:**
- Create: `src/components/cards/GenericCommandCard.tsx`
- Create: `src/components/cards/analysis/AnchorCard.tsx`
- Create: `src/components/cards/ai/ExplainCard.tsx`
- Create: `src/components/cards/ai/AskCard.tsx`
- Create: `src/components/cards/transfer/ExportCard.tsx`
- Create: `src/components/cards/security/ProtectCard.tsx`
- Create: `src/components/cards/security/SecretsCard.tsx`
- Modify: `src/pages/Home.tsx`

### 배경
anchor, explain, ask, export, protect, secrets 카드는 모두 동일한 GenericCommandCard 패턴을 사용한다. 먼저 재사용 가능한 GenericCommandCard를 만들고, 각 카드는 이를 래핑하는 얇은 파일로 만든다.

- [ ] **Step 1: `src/components/cards/GenericCommandCard.tsx` 생성**

```typescript
// === ANCHOR: GENERIC_COMMAND_CARD_START ===
import { useRef, useState } from "react";
import { runVib, pickFile, buildGuiAiEnv } from "../../lib/vib";
import GuiCliOutputBlock from "../GuiCliOutputBlock";
import { CardState, FlagDef, buildCmdArgs } from "../../lib/commands";

export interface GenericCmdDef {
  name: string;
  icon: string;
  color: string;
  title: string;
  short: string;
  flags?: FlagDef[];
}

export interface GenericCommandCardProps {
  cmd: GenericCmdDef;
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onOpenSettings?: (reason?: string) => void;
}

export default function GenericCommandCard({
  cmd,
  projectDir,
  apiKey,
  providerKeys,
  hasAnyAiKey = false,
  aiKeyStatusLoaded = false,
  onOpenSettings,
}: GenericCommandCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [out, setOut] = useState("");
  const [hasWarning, setHasWarning] = useState(false);
  const [flagValues, setFlagValues] = useState<Record<string, string | boolean>>({});
  const [showModal, setShowModal] = useState(false);
  const idleTimer = useRef<number | undefined>(undefined);

  async function handleRun() {
    const args = buildCmdArgs(cmd.name, { [cmd.name]: flagValues });
    if (!args) {
      setSt("error");
      setOut("필수 항목을 입력해주세요");
      return;
    }
    if (args.includes("--ai") && aiKeyStatusLoaded && !hasAnyAiKey) {
      setSt("error");
      setOut("API 키를 먼저 설정해주세요");
      if (onOpenSettings) onOpenSettings("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      return;
    }
    setSt("loading");
    setOut("");
    if (idleTimer.current !== undefined) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = undefined;
    }
    try {
      const env = args.includes("--ai") ? buildGuiAiEnv(providerKeys, apiKey) : undefined;
      const r = await runVib(args, projectDir, env);
      const stdoutContent = r.stdout.trim();
      const stderrContent = r.stderr.trim();
      const combined = [stderrContent, stdoutContent].filter(Boolean).join("\n\n");
      const output = combined || (r.ok ? "완료" : `exit ${r.exit_code}`);
      const warn = Boolean(stderrContent);
      setSt(r.ok ? "done" : "error");
      setOut(output);
      setHasWarning(warn);
      if (!r.ok || warn) setShowModal(true);
      if (r.ok && !warn) {
        idleTimer.current = window.setTimeout(() => {
          setSt("idle");
          idleTimer.current = undefined;
        }, 3000);
      }
    } catch (e) {
      setSt("error");
      setOut(String(e));
      setHasWarning(false);
    }
  }

  const hasTextOrSelect = cmd.flags?.some((f) => f.type === "text" || f.type === "select") ?? false;
  const textColor = cmd.color === "#FFD166" || cmd.color === "#FFE44D" ? "#1A1A1A" : "#fff";

  return (
    <>
      {showModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 480, maxHeight: "70vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>{cmd.name.toUpperCase()} 결과</span>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <pre style={{ margin: 0, padding: 16, overflowY: "auto", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", color: st === "error" ? "#FF4D4D" : "#1A1A1A" }}>
              {out}
            </pre>
          </div>
        </div>
      )}
      <div className="feature-card" style={{ cursor: "default" }}>
        <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
          <div className="feature-card-icon" style={{
            background: cmd.color, color: "#fff", borderColor: cmd.color,
            width: 22, height: 22, fontSize: 11, fontWeight: 900,
          }}>{cmd.icon}</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
            <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{cmd.title}</span>
            <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{cmd.short}</span>
          </div>
          {(st === "done" || (st === "idle" && out)) && !hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
          {hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>}
          {st === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
        </div>
        <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
          {!hasTextOrSelect && (
            <GuiCliOutputBlock text={out} placeholder={cmd.short} variant={st === "error" ? "error" : hasWarning ? "warn" : "default"} />
          )}
          {cmd.flags?.map((fd, fi) => {
            const val: string | boolean = flagValues[fd.key] ?? (fd.type === "bool" ? false : fd.type === "select" && fd.options.length > 0 ? fd.options[0].v : "");
            if (fd.type === "bool") return (
              <button key={fi} onClick={() => setFlagValues((m) => ({ ...m, [fd.key]: !val }))} style={{
                fontSize: 9, fontWeight: 700, padding: "2px 6px", marginRight: 4, marginBottom: 4,
                border: "2px solid #1A1A1A",
                background: val ? "#1A1A1A" : "#fff",
                color: val ? "#fff" : "#1A1A1A", cursor: "pointer",
              }}>{fd.label}</button>
            );
            if (fd.type === "text") return (
              <div key={fi} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <input value={String(val)} onChange={(e) => setFlagValues((m) => ({ ...m, [fd.key]: e.target.value }))} placeholder={(fd as any).placeholder} style={{
                  flex: 1, fontSize: 10, padding: "3px 6px",
                  border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                  fontFamily: "IBM Plex Mono, monospace", background: "#fff", minWidth: 0,
                }} />
                {fd.key === "_file" && (
                  <button onClick={async () => {
                    const picked = await pickFile(projectDir);
                    if (picked) {
                      const rel = picked.startsWith(projectDir + "/") ? picked.slice(projectDir.length + 1) : picked;
                      setFlagValues((m) => ({ ...m, [fd.key]: rel }));
                    }
                  }} style={{ padding: "2px 6px", border: "2px solid #1A1A1A", background: "#fff", cursor: "pointer", fontSize: 13, flexShrink: 0 }}>📁</button>
                )}
              </div>
            );
            if (fd.type === "select") return (
              <select key={fi} value={String(val)} onChange={(e) => setFlagValues((m) => ({ ...m, [fd.key]: e.target.value }))} style={{
                width: "100%", fontSize: 10, padding: "3px 6px", marginBottom: 4,
                border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                fontFamily: "IBM Plex Mono, monospace", cursor: "pointer", background: "#fff",
              }}>
                {fd.options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
              </select>
            );
            return null;
          })}
          {out && hasTextOrSelect && (
            <GuiCliOutputBlock text={out} placeholder="" variant={st === "error" ? "error" : hasWarning ? "warn" : "default"} />
          )}
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="btn btn-sm"
              style={{ flex: 1, background: cmd.color, color: textColor, border: "2px solid #1A1A1A", fontSize: 10 }}
              disabled={st === "loading"}
              onClick={handleRun}
            >
              {st === "loading" ? <span className="spinner" /> : `${cmd.name.toUpperCase()} ▶`}
            </button>
            {out && (
              <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                onClick={() => setShowModal(true)}>결과</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
// === ANCHOR: GENERIC_COMMAND_CARD_END ===
```

- [ ] **Step 2: 각 단순 카드 파일 생성 (anchor, explain, ask, export, protect, secrets)**

`src/components/cards/analysis/AnchorCard.tsx`:
```typescript
// === ANCHOR: ANCHOR_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "anchor")!;

export default function AnchorCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: ANCHOR_CARD_END ===
```

`src/components/cards/ai/ExplainCard.tsx`:
```typescript
// === ANCHOR: EXPLAIN_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "explain")!;

export default function ExplainCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: EXPLAIN_CARD_END ===
```

`src/components/cards/ai/AskCard.tsx`:
```typescript
// === ANCHOR: ASK_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "ask")!;

export default function AskCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: ASK_CARD_END ===
```

`src/components/cards/transfer/ExportCard.tsx`:
```typescript
// === ANCHOR: EXPORT_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "export")!;

export default function ExportCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: EXPORT_CARD_END ===
```

`src/components/cards/security/ProtectCard.tsx`:
```typescript
// === ANCHOR: PROTECT_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "protect")!;

export default function ProtectCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: PROTECT_CARD_END ===
```

`src/components/cards/security/SecretsCard.tsx`:
```typescript
// === ANCHOR: SECRETS_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "secrets")!;

export default function SecretsCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: SECRETS_CARD_END ===
```

- [ ] **Step 3: Home.tsx EXCLUDE 목록에 6개 커맨드 추가, 카드 컴포넌트 import 및 삽입**

EXCLUDE에 추가: `"anchor"`, `"explain"`, `"ask"`, `"export"`, `"protect"`, `"secrets"`

```typescript
const EXCLUDE = ["scan","watch","guard","checkpoint","transfer","history","patch","start","doctor","config","rules","install","manual","policy","undo","anchor","explain","ask","export","protect","secrets"];
```

Home.tsx 상단에 import 추가:
```typescript
import AnchorCard from "../components/cards/analysis/AnchorCard";
import ExplainCard from "../components/cards/ai/ExplainCard";
import AskCard from "../components/cards/ai/AskCard";
import ExportCard from "../components/cards/transfer/ExportCard";
import ProtectCard from "../components/cards/security/ProtectCard";
import SecretsCard from "../components/cards/security/SecretsCard";
```

커맨드 섹션 그리드 안에 UndoCard 아래에 삽입:
```tsx
<AnchorCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
<ExplainCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
<AskCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
<ExportCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
<ProtectCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
<SecretsCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={aiKeyStatusLoaded} onOpenSettings={onOpenSettings} />
```

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: `npm run dev` 실행 후 홈 화면에서 anchor, explain, ask, export, protect, secrets 카드 렌더링 확인. 각 카드 버튼 클릭 시 로딩 스피너 동작 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/ src/pages/Home.tsx
git commit -m "refactor: GenericCommandCard + 6개 단순 카드 컴포넌트 추출"
```

---

## Task 5: HistoryCard 추출 (backup/)

**Files:**
- Create: `src/components/cards/backup/HistoryCard.tsx`
- Modify: `src/pages/Home.tsx`

- [ ] **Step 1: Home.tsx에서 히스토리 카드 JSX 확인**

Home.tsx line 1695~1738의 히스토리 카드 JSX를 읽는다. `cmdStates["history"]`, `cmdOutputs["history"]`, `cmdHasWarnings["history"]`를 사용한다.

- [ ] **Step 2: `src/components/cards/backup/HistoryCard.tsx` 생성**

```typescript
// === ANCHOR: HISTORY_CARD_START ===
import { useRef, useState } from "react";
import { runVib } from "../../../lib/vib";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";
import { CardState } from "../../../lib/commands";

interface HistoryCardProps {
  projectDir: string;
}

export default function HistoryCard({ projectDir }: HistoryCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [out, setOut] = useState("");
  const [hasWarning, setHasWarning] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const idleTimer = useRef<number | undefined>(undefined);

  async function handleRun() {
    setSt("loading");
    setOut("");
    if (idleTimer.current !== undefined) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = undefined;
    }
    try {
      const r = await runVib(["history"], projectDir);
      const stdoutContent = r.stdout.trim();
      const stderrContent = r.stderr.trim();
      const combined = [stderrContent, stdoutContent].filter(Boolean).join("\n\n");
      const output = combined || (r.ok ? "완료" : `exit ${r.exit_code}`);
      const warn = Boolean(stderrContent);
      setSt(r.ok ? "done" : "error");
      setOut(output);
      setHasWarning(warn);
      if (!r.ok || warn) setShowModal(true);
      if (r.ok && !warn) {
        idleTimer.current = window.setTimeout(() => {
          setSt("idle");
          idleTimer.current = undefined;
        }, 3000);
      }
    } catch (e) {
      setSt("error");
      setOut(String(e));
      setHasWarning(false);
    }
  }

  return (
    <>
      {showModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 480, maxHeight: "70vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>HISTORY 결과</span>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <pre style={{ margin: 0, padding: 16, overflowY: "auto", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", color: st === "error" ? "#FF4D4D" : "#1A1A1A" }}>
              {out}
            </pre>
          </div>
        </div>
      )}
      <div className="feature-card" style={{ cursor: "default" }}>
        <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
          <div className="feature-card-icon"
            style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 14, fontWeight: 900 }}>🕓</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>히스토리</span>
            <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
              저장이 언제 찍혔는지 시간 순으로 보여 줘요
            </span>
          </div>
          {(st === "done" || (st === "idle" && out)) && !hasWarning && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
          )}
          {hasWarning && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>
          )}
          {st === "error" && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
          )}
        </div>
        <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
          <GuiCliOutputBlock
            text={out}
            placeholder="체크포인트 변경 이력 보기"
            variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
          />
          <div style={{ display: "flex", gap: 4 }}>
            <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
              disabled={st === "loading"} onClick={handleRun}>
              {st === "loading" ? <span className="spinner" /> : "HISTORY ▶"}
            </button>
            {out && (
              <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                onClick={() => setShowModal(true)}>결과</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
// === ANCHOR: HISTORY_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 히스토리 카드 JSX를 HistoryCard로 교체**

```typescript
import HistoryCard from "../components/cards/backup/HistoryCard";
```

Home.tsx line 1695~1738의 히스토리 카드 `<div className="feature-card" ...>` 블록 전체를:
```tsx
<HistoryCard projectDir={projectDir} />
```
로 교체한다.

Home.tsx에서 `cmdStates["history"]`, `cmdOutputs["history"]`, `cmdHasWarnings["history"]` 참조가 더 없는지 확인한다.

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: `npm run dev` → HISTORY 버튼 클릭 → 로딩 스피너 → 결과 출력 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/backup/HistoryCard.tsx src/pages/Home.tsx
git commit -m "refactor: HistoryCard 컴포넌트 추출 (backup/)"
```

---

## Task 6: GuardCard 추출 (analysis/)

**Files:**
- Create: `src/components/cards/analysis/GuardCard.tsx`
- Modify: `src/pages/Home.tsx`

### 배경
Guard 카드는 결과 모달이 Home.tsx에 fixed overlay로 렌더링된다. GuardCard는 실행 완료 후 결과를 `onGuardResult` 콜백으로 넘기고, 모달은 Home.tsx에서 계속 관리한다.

- [ ] **Step 1: Home.tsx에서 가드 카드 JSX 확인**

Home.tsx line 1568~1612의 guard 카드 JSX와, line 1037~1039의 상태, line 1058의 guardStrict 상태, line 1072~1080의 handleGuard를 확인한다.

- [ ] **Step 2: `src/components/cards/analysis/GuardCard.tsx` 생성**

```typescript
// === ANCHOR: GUARD_CARD_START ===
import { useState } from "react";
import { vibGuard, GuardResult } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface GuardCardProps {
  projectDir: string;
  onGuardResult: (result: GuardResult) => void;
}

export default function GuardCard({ projectDir, onGuardResult }: GuardCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [guardStrict, setGuardStrict] = useState(false);

  async function handleGuard() {
    setSt("loading");
    try {
      const r = await vibGuard(projectDir, { strict: guardStrict });
      onGuardResult(r);
      setSt("done");
    } catch (e) {
      setSt("error");
    }
  }

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#FF6B3518", padding: "10px 14px" }}>
        <div className="feature-card-icon"
          style={{ background: "#FF6B35", color: "#fff", borderColor: "#FF6B35", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>🛡</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>AI 폭주 방지</span>
          <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            AI가 건드리면 안 되는 곳을 건드렸는지 검사해요
          </span>
        </div>
        {st === "done" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
        {st === "error" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
          <button
            onClick={() => setGuardStrict((v) => !v)}
            style={{
              fontSize: 9, fontWeight: 700, padding: "2px 6px",
              border: "2px solid #1A1A1A",
              background: guardStrict ? "#1A1A1A" : "#fff",
              color: guardStrict ? "#fff" : "#1A1A1A", cursor: "pointer",
            }}
          >strict</button>
        </div>
        <button
          className="btn btn-sm"
          style={{ width: "100%", background: "#FF6B35", color: "#fff", border: "2px solid #1A1A1A" }}
          disabled={st === "loading"}
          onClick={handleGuard}
        >
          {st === "loading" ? <span className="spinner" /> : "GUARD ▶"}
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: GUARD_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 guard 카드 JSX를 GuardCard로 교체**

```typescript
import GuardCard from "../components/cards/analysis/GuardCard";
```

Home.tsx에서 guard 카드 JSX를 교체:
```tsx
<GuardCard
  projectDir={projectDir}
  onGuardResult={(r) => { setGuardResult(r); setGuardModal(true); setGuardState("done"); }}
/>
```

Home.tsx에서 `guardState`, `guardStrict`, `handleGuard` 를 제거한다. `guardResult`, `guardModal`, `setGuardModal`은 모달 렌더링에 계속 필요하므로 유지한다.

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: GUARD 버튼 클릭 → 로딩 → 결과 모달 팝업 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/analysis/GuardCard.tsx src/pages/Home.tsx
git commit -m "refactor: GuardCard 컴포넌트 추출 (analysis/)"
```

---

## Task 7: PatchCard 추출 (ai/)

**Files:**
- Create: `src/components/cards/ai/PatchCard.tsx`
- Modify: `src/pages/Home.tsx`

- [ ] **Step 1: Home.tsx에서 패치 카드 JSX 확인**

Home.tsx line 1739~1835의 패치 카드 JSX를 확인한다. `PATCH_COMMAND`, `cmdStates["patch"]`, `cmdOutputs["patch"]`, `cmdHasWarnings["patch"]`, AI 환경변수(`buildGuiAiEnv`)를 사용한다.

- [ ] **Step 2: `src/components/cards/ai/PatchCard.tsx` 생성**

```typescript
// === ANCHOR: PATCH_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { PATCH_COMMAND } from "../../../lib/commands";

export default function PatchCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={PATCH_COMMAND} {...props} />;
}
// === ANCHOR: PATCH_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 패치 카드 JSX를 PatchCard로 교체**

```typescript
import PatchCard from "../components/cards/ai/PatchCard";
```

Home.tsx line 1739~1835의 패치 카드 `{(() => { const cmd = PATCH_COMMAND; ... })()}` 블록 전체를:
```tsx
<PatchCard
  projectDir={projectDir}
  apiKey={apiKey}
  providerKeys={providerKeys}
  hasAnyAiKey={hasAnyAiKey}
  aiKeyStatusLoaded={aiKeyStatusLoaded}
  onOpenSettings={onOpenSettings}
/>
```
로 교체한다.

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: PATCH 버튼 클릭 → 로딩 스피너 확인. API 키 없을 때 설정 화면으로 이동 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/ai/PatchCard.tsx src/pages/Home.tsx
git commit -m "refactor: PatchCard 컴포넌트 추출 (ai/)"
```

---

## Task 8: TransferCard 추출 (transfer/)

**Files:**
- Create: `src/components/cards/transfer/TransferCard.tsx`
- Modify: `src/pages/Home.tsx`

- [ ] **Step 1: Home.tsx에서 트랜스퍼 카드 JSX 확인**

Home.tsx line 1648~1685의 "AI 이동 자유" 카드 JSX를 확인한다. `transferState`, `transferHandoff`, `transferCompact`, `handleTransfer`를 사용한다.

- [ ] **Step 2: `src/components/cards/transfer/TransferCard.tsx` 생성**

```typescript
// === ANCHOR: TRANSFER_CARD_START ===
import { useState } from "react";
import { vibTransfer } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface TransferCardProps {
  projectDir: string;
}

export default function TransferCard({ projectDir }: TransferCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [handoff, setHandoff] = useState(false);
  const [compact, setCompact] = useState(false);

  async function handleTransfer() {
    setSt("loading");
    try {
      const r = await vibTransfer(projectDir, { handoff, compact });
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setSt("done");
    } catch {
      setSt("error");
    }
  }

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#4D9FFF18", padding: "10px 14px" }}>
        <div className="feature-card-icon"
          style={{ background: "#4D9FFF", color: "#fff", borderColor: "#4D9FFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>⇄</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>AI 이동 자유</span>
          <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            프로젝트 컨텍스트를 다른 AI로 넘겨요
          </span>
        </div>
        {st === "done" && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
        {st === "error" && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
          {([{ key: "handoff", label: "handoff", val: handoff, set: setHandoff }, { key: "compact", label: "compact", val: compact, set: setCompact }] as const).map(({ key, label, val, set }) => (
            <button key={key} onClick={() => set((v) => !v)} style={{
              fontSize: 9, fontWeight: 700, padding: "2px 6px",
              border: "2px solid #1A1A1A",
              background: val ? "#1A1A1A" : "#fff",
              color: val ? "#fff" : "#1A1A1A", cursor: "pointer",
            }}>{label}</button>
          ))}
        </div>
        <button className="btn btn-sm" style={{ width: "100%", background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A" }}
          disabled={st === "loading"} onClick={handleTransfer}>
          {st === "loading" ? <span className="spinner" /> : "TRANSFER ▶"}
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: TRANSFER_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 트랜스퍼 카드 JSX를 TransferCard로 교체**

```typescript
import TransferCard from "../components/cards/transfer/TransferCard";
```

Home.tsx line 1648~1685의 카드 `<div className="feature-card" ...>` 블록 전체를:
```tsx
<TransferCard projectDir={projectDir} />
```
로 교체한다.

Home.tsx에서 `transferState`, `transferHandoff`, `transferCompact`, `handleTransfer` 제거.

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: TRANSFER 버튼 + handoff/compact 토글 동작 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/transfer/TransferCard.tsx src/pages/Home.tsx
git commit -m "refactor: TransferCard 컴포넌트 추출 (transfer/)"
```

---

## Task 9: CheckpointCard 추출 (backup/)

**Files:**
- Create: `src/components/cards/backup/CheckpointCard.tsx`
- Modify: `src/pages/Home.tsx`

- [ ] **Step 1: Home.tsx에서 체크포인트 카드 JSX 확인**

Home.tsx line 1613~1646의 체크포인트 카드 JSX를 확인한다. `cpMsg`, `cpState`, `handleCheckpoint`, `onNavigate`를 사용한다.

- [ ] **Step 2: `src/components/cards/backup/CheckpointCard.tsx` 생성**

```typescript
// === ANCHOR: CHECKPOINT_CARD_START ===
import { useState } from "react";
import { checkpointCreate } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface CheckpointCardProps {
  projectDir: string;
  onNavigate: (page: "checkpoints") => void;
}

export default function CheckpointCard({ projectDir, onNavigate }: CheckpointCardProps) {
  const [cpMsg, setCpMsg] = useState("");
  const [st, setSt] = useState<CardState>("idle");

  async function handleCheckpoint() {
    if (!cpMsg.trim()) return;
    setSt("loading");
    try {
      await checkpointCreate(projectDir, cpMsg.trim());
      setCpMsg("");
      setSt("done");
      setTimeout(() => setSt("idle"), 2000);
    } catch {
      setSt("error");
    }
  }

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
        <div className="feature-card-icon"
          style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>💾</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>체크포인트</span>
          <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            지금 코드 모습을 저장해 두면 나중에 그때로 되돌릴 수 있어요 (게임 세이브 같아요)
          </span>
        </div>
        {st === "done" && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>저장됨</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <input
          className="input-field"
          value={cpMsg}
          onChange={(e) => setCpMsg(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCheckpoint()}
          placeholder="메시지 입력..."
          style={{ width: "100%", marginBottom: 6, fontSize: 11, padding: "4px 8px", boxSizing: "border-box" }}
        />
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
            disabled={st === "loading" || !cpMsg.trim()} onClick={handleCheckpoint}>
            {st === "loading" ? <span className="spinner" /> : "저장 ▶"}
          </button>
          <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
            onClick={() => onNavigate("checkpoints")}>목록</button>
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: CHECKPOINT_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 체크포인트 카드 JSX를 CheckpointCard로 교체**

```typescript
import CheckpointCard from "../components/cards/backup/CheckpointCard";
```

Home.tsx line 1613~1646의 블록 전체를:
```tsx
<CheckpointCard projectDir={projectDir} onNavigate={onNavigate} />
```
로 교체한다.

Home.tsx에서 `cpMsg`, `setCpMsg`, `cpState`, `setCpState`, `handleCheckpoint` 제거.

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: 메시지 입력 → 저장 버튼 클릭 → "저장됨" 뱃지 → 2초 후 idle 복귀 확인. "목록" 버튼 클릭 → Checkpoints 탭 이동 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/backup/CheckpointCard.tsx src/pages/Home.tsx
git commit -m "refactor: CheckpointCard 컴포넌트 추출 (backup/)"
```

---

## Task 10: CodemapCard 추출 (analysis/) — 마지막, 가장 복잡

**Files:**
- Create: `src/components/cards/analysis/CodemapCard.tsx`
- Modify: `src/pages/Home.tsx`

### 배경
`watch_log` Tauri 이벤트 리스너, watch 프로세스 상태, scan 상태를 모두 포함하는 가장 복잡한 카드. `watchOn`/`mapMode`는 App.tsx 레벨에서 관리되므로 props로 받는다.

- [ ] **Step 1: Home.tsx에서 코드맵 카드 JSX 확인**

Home.tsx line 1514~1566의 코드맵 카드 JSX와, line 1040~1045의 상태, line 1091~1118의 핸들러를 확인한다.

- [ ] **Step 2: `src/components/cards/analysis/CodemapCard.tsx` 생성**

```typescript
// === ANCHOR: CODEMAP_CARD_START ===
import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { vibScan, startWatch, stopWatch, watchStatus } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface CodemapCardProps {
  projectDir: string;
  watchOn: boolean;
  setWatchOn: (v: boolean) => void;
  mapMode: "manual" | "auto";
  setMapMode: (v: "manual" | "auto") => void;
}

export default function CodemapCard({ projectDir, watchOn, setWatchOn, mapMode, setMapMode }: CodemapCardProps) {
  const [scanState, setScanState] = useState<CardState>("idle");
  const [watchLoading, setWatchLoading] = useState(false);
  const [watchLogs, setWatchLogs] = useState<string[]>([]);
  const watchLogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    watchStatus().then((running) => {
      if (running !== watchOn) setWatchOn(running);
    }).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const unlisten = listen<string>("watch_log", (e) => {
      setWatchLogs((prev) => {
        const next = [...prev, e.payload].slice(-200);
        return next;
      });
      setTimeout(() => {
        if (watchLogRef.current) watchLogRef.current.scrollTop = watchLogRef.current.scrollHeight;
      }, 0);
    });
    return () => { unlisten.then((f) => f()); };
  }, []);

  async function handleScan() {
    setScanState("loading");
    try {
      const r = await vibScan(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setScanState("done");
    } catch {
      setScanState("error");
    }
  }

  async function handleToggleWatch() {
    setWatchLoading(true);
    try {
      if (watchOn) { await stopWatch(); setWatchOn(false); }
      else { setWatchLogs([]); await startWatch(projectDir); setWatchOn(true); }
    } catch {
      // 오류 무시 (상위에서 처리 불필요)
    } finally {
      setWatchLoading(false);
    }
  }

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#F5621E18", padding: "10px 14px" }}>
        <div className="feature-card-icon"
          style={{ background: "#F5621E", color: "#fff", borderColor: "#F5621E", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>MAP</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 18, flexShrink: 0 }}>코드맵</span>
          <span style={{ fontSize: 10, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            복잡한 코드가 서로 어떻게 연결되어 있는지 한눈에 보여주는 지도
          </span>
        </div>
        {watchOn && <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>감시 중</span>}
        {mapMode === "manual" && scanState === "done" && !watchOn && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
          {(["manual", "auto"] as const).map((m) => (
            <button key={m} onClick={() => setMapMode(m)} style={{
              flex: 1, fontSize: 10, fontWeight: 700, padding: "3px 0",
              border: "2px solid #1A1A1A",
              background: mapMode === m ? "#1A1A1A" : "#fff",
              color: mapMode === m ? "#fff" : "#1A1A1A", cursor: "pointer",
            }}>{m === "manual" ? "수동" : "자동"}</button>
          ))}
        </div>
        {mapMode === "manual" ? (
          <button className="btn btn-sm" style={{ width: "100%", background: "#F5621E", color: "#fff", border: "2px solid #1A1A1A" }}
            disabled={scanState === "loading"} onClick={handleScan}>
            {scanState === "loading" ? <span className="spinner" /> : "SCAN ▶"}
          </button>
        ) : (
          <>
            <button className="btn btn-sm" style={{ width: "100%", border: "2px solid #1A1A1A", background: watchOn ? "#FF4D4D" : "#F5621E", color: "#fff" }}
              disabled={watchLoading} onClick={handleToggleWatch}>
              {watchLoading ? <span className="spinner" /> : watchOn ? "STOP ■" : "WATCH ▶"}
            </button>
            {watchOn && (
              <div ref={watchLogRef} style={{
                marginTop: 6, height: 80, overflowY: "auto", background: "#0D0D0D",
                border: "1px solid #333", padding: "4px 6px", fontFamily: "monospace",
                fontSize: 9, color: "#4DFF91", lineHeight: 1.5,
              }}>
                {watchLogs.length === 0
                  ? <span style={{ color: "#666" }}>감시 중… 로그 대기</span>
                  : watchLogs.map((l, i) => <div key={i}>{l}</div>)
                }
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
// === ANCHOR: CODEMAP_CARD_END ===
```

- [ ] **Step 3: Home.tsx에서 코드맵 카드 JSX를 CodemapCard로 교체**

```typescript
import CodemapCard from "../components/cards/analysis/CodemapCard";
```

Home.tsx line 1514~1566의 코드맵 카드 `<div className="feature-card" ...>` 블록 전체를:
```tsx
<CodemapCard
  projectDir={projectDir}
  watchOn={watchOn}
  setWatchOn={setWatchOn}
  mapMode={mapMode}
  setMapMode={setMapMode}
/>
```
로 교체한다.

Home.tsx에서 제거:
- `scanState`, `setScanState`
- `watchOnLocal`, `setWatchOnLocal`
- `watchLoading`, `setWatchLoading`
- `watchLogs`, `setWatchLogs`
- `watchLogRef`
- `handleScan`, `handleToggleWatch`
- `useEffect` for watch_log (line 1098~1109)
- `useEffect` for watchStatus (line 1091~1096)
- `listen` import (사용처 없으면)

- [ ] **Step 4: 빌드 + 런타임 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```

런타임: SCAN 버튼 클릭 → 스피너 → 완료 뱃지 확인. 자동 모드 전환 → WATCH 시작 → 로그 표시 → STOP 확인.

- [ ] **Step 5: 커밋**

```bash
cd vibelign-gui
git add src/components/cards/analysis/CodemapCard.tsx src/pages/Home.tsx
git commit -m "refactor: CodemapCard 컴포넌트 추출 (analysis/)"
```

---

## Task 11: Home.tsx 정리 및 최종 검증

**Files:**
- Modify: `src/pages/Home.tsx`

### 배경
모든 카드 추출이 완료되면 Home.tsx에 남은 불필요한 상태·임포트를 정리한다.

- [ ] **Step 1: 미사용 상태 정리**

Home.tsx에서 더 이상 사용하지 않는 상태 변수 제거:
- `cmdStates`, `setCmdStates` (제너릭 카드들이 자체 관리)
- `cmdOutputs`, `setCmdOutputs`
- `cmdHasWarnings`, `setCmdHasWarnings`
- `cmdFlagValues`, `setCmdFlagValues`
- `cmdIdleTimers`
- `outputModal`, `setOutputModal` (카드별로 이동됨)
- `handleRunCmd` (모든 카드가 추출됨)
- `guardColor` (Guard 모달에서만 사용, 모달 코드가 있으면 유지)

- [ ] **Step 2: 미사용 import 정리**

Home.tsx에서 사용하지 않는 import 제거:
```typescript
// 사용처 없으면 제거
import { listen } from "@tauri-apps/api/event";
import { vibGuard, vibScan, vibTransfer, startWatch, stopWatch, watchStatus, checkpointCreate, runVib, pickFile, buildGuiAiEnv } from "../lib/vib";
```
실제 사용 여부를 확인 후 제거. Guard 모달이 `guardColor` 함수를 사용하면 유지.

- [ ] **Step 3: 빌드 검증**

```bash
cd vibelign-gui && npm run build && npm run lint
```
예상: 오류 없이 성공.

- [ ] **Step 4: 전체 기능 런타임 검증**

```bash
cd vibelign-gui && npm run dev
```

다음을 순서대로 확인한다:

| 검증 항목 | 기대 결과 |
|-----------|-----------|
| 홈 화면 전체 렌더링 | 모든 카드 정상 표시 |
| 체크포인트 저장 (메시지 입력 → 저장) | "저장됨" 뱃지 2초 표시 |
| "목록" 버튼 클릭 | Checkpoints 탭 이동 |
| Guard 실행 | 결과 모달 팝업 |
| HISTORY 실행 | 출력 결과 표시 |
| SCAN 실행 | 스피너 → "완료" 뱃지 |
| WATCH 시작/중지 | 감시 로그 표시 / 중지 |
| TRANSFER 실행 | 로딩 → 완료 |
| anchor 카드 실행 | 로딩 → 출력 |
| undo 카드 클릭 | Checkpoints 탭 이동 |
| 앱 재시동 후 홈 화면 | 정상 렌더링, 상태 초기화 |

- [ ] **Step 5: Home.tsx 라인 수 확인**

```bash
wc -l vibelign-gui/src/pages/Home.tsx
```
목표: 500줄 이하 (COMMANDS 배열 제거로 대폭 축소).

- [ ] **Step 6: 최종 커밋**

```bash
cd vibelign-gui
git add src/pages/Home.tsx
git commit -m "refactor: Home.tsx 정리 완료 — 불필요한 상태·임포트 제거"
```

---

## 스펙 커버리지 체크

| 스펙 요구사항 | 구현 태스크 |
|---------------|------------|
| backup/: Checkpoint, History, Undo | Task 3, 5, 9 |
| analysis/: Guard, Codemap, Anchor | Task 4, 6, 10 |
| ai/: Patch, Ask, Explain | Task 4, 7 |
| transfer/: Transfer, Export | Task 4, 8 |
| security/: Secrets, Protect | Task 4 |
| 카드가 자신의 상태 관리 | GenericCommandCard + 각 전용 카드 |
| ANCHOR 포함 | 모든 카드 파일에 포함 |
| 로직 이동 금지 | 각 태스크 주의사항 명시 |
| 추출 후 검증 | 각 태스크 Step 4 |
| CodemapCard watchOn/mapMode props | Task 10 |
| GuardCard onGuardResult 콜백 | Task 6 |
| CheckpointCard onNavigate | Task 9 |
