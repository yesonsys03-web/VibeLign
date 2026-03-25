// === ANCHOR: HOME_START ===
import { useState } from "react";
import { vibGuard, vibScan, vibTransfer, startWatch, stopWatch, openFolder } from "../lib/vib";

type CardState = "idle" | "loading" | "done" | "error";
type View = "home" | "manual_list" | "manual_detail";

interface HomeProps {
  projectDir: string;
  onNavigate: (page: "checkpoints") => void;
}

// ── 커맨드 데이터 ──────────────────────────────────────────────────────────────
const COMMANDS = [
  {
    name: "start", icon: "▶", color: "#F5621E",
    title: "시작하기",
    short: "처음 딱 한 번 실행하면 끝",
    desc: "새 프로젝트 폴더에서 처음 실행하는 커맨드예요. VibeLign이 필요한 파일을 자동으로 만들어줘요. 게임으로 치면 '새 게임 시작' 버튼이에요.",
    usage: "vib start",
    tips: ["프로젝트 폴더에서 딱 한 번만 실행해요", "AGENTS.md, .vibelign 폴더가 자동으로 생겨요", "AI한테 이 폴더 구조를 알려주는 파일도 만들어줘요"],
  },
  {
    name: "checkpoint", icon: "💾", color: "#7B4DFF",
    title: "체크포인트",
    short: "지금 상태를 저장 — 게임 세이브",
    desc: "지금 코드 상태를 저장해요. AI가 코드를 망가뜨리기 전에 미리 저장해두면, 나중에 그 시점으로 되돌릴 수 있어요. 마치 게임에서 중간 저장하는 것처럼요.",
    usage: "vib checkpoint \"기능 추가 전\"",
    tips: ["AI한테 뭔가 시키기 전에 꼭 저장하세요", "설명을 짧게 써두면 나중에 찾기 쉬워요", "여러 번 저장해도 괜찮아요"],
  },
  {
    name: "undo", icon: "↩", color: "#FF4D4D",
    title: "되돌리기",
    short: "저장했던 그 시점으로 되돌아가기",
    desc: "체크포인트로 저장했던 상태로 코드를 되돌려요. AI가 코드를 이상하게 바꿔놨을 때 '그냥 없던 일로 해줘!' 할 때 쓰는 커맨드예요.",
    usage: "vib undo",
    tips: ["실행하면 어느 시점으로 돌아갈지 고를 수 있어요", "저장 안 하고 undo하면 못 돌아가니까 checkpoint 먼저!"],
  },
  {
    name: "doctor", icon: "🩺", color: "#FF4D8B",
    title: "닥터",
    short: "프로젝트 건강 검진",
    desc: "프로젝트 상태가 괜찮은지 검사해줘요. 점수(0~100)랑 어떤 문제가 있는지 알려줘요. 병원 건강검진처럼 '지금 코드 상태가 어때요?'를 확인하는 거예요.",
    usage: "vib doctor",
    tips: ["점수가 낮으면 뭘 고쳐야 하는지 알려줘요", "--strict 붙이면 더 꼼꼼하게 검사해요", "GUI에서 Doctor 탭으로도 볼 수 있어요"],
  },
  {
    name: "guard", icon: "🛡", color: "#FF6B35",
    title: "가드",
    short: "AI가 코드 망가뜨렸는지 검사",
    desc: "AI가 코드를 수정한 후에 이상한 짓을 했는지 체크해요. pass(괜찮음), warn(조심), fail(위험) 중 하나로 알려줘요. 경호원처럼 코드를 지켜주는 거예요.",
    usage: "vib guard",
    tips: ["AI 작업 끝나고 꼭 실행해보세요", "--strict 붙이면 경고도 실패로 처리해요"],
  },
  {
    name: "anchor", icon: "⚓", color: "#4D9FFF",
    title: "앵커",
    short: "AI가 건드려도 되는 구역 표시",
    desc: "코드 파일에 'AI야, 여기 건드려도 돼!' 표시를 자동으로 달아줘요. 앵커가 있어야 AI가 정확한 위치를 찾아서 수정할 수 있어요. 지도의 위치 핀 같은 거예요.",
    usage: "vib anchor",
    tips: ["새 파일 만들면 꼭 실행해주세요", "파일 맨 위/아래에 주석 형태로 달려요", "AI한테 '앵커 범위 안에서만 수정해줘' 라고 하면 돼요"],
  },
  {
    name: "scan", icon: "🔍", color: "#F5621E",
    title: "스캔",
    short: "코드맵 갱신 — 구조 다시 분석",
    desc: "프로젝트 전체를 훑어서 코드맵을 새로 만들어요. 파일을 많이 바꿨거나 AI한테 새 파일을 알려주고 싶을 때 써요. 마치 내비게이션 지도를 업데이트하는 거예요.",
    usage: "vib scan",
    tips: ["파일 많이 바꾼 뒤에 실행하면 좋아요", "AI한테 project_map.json을 주면 전체 구조를 한 번에 파악해요"],
  },
  {
    name: "watch", icon: "👁", color: "#4DFF91",
    title: "워치",
    short: "실시간 자동 감시 모드",
    desc: "파일이 바뀔 때마다 자동으로 코드맵을 갱신해줘요. 켜두고 AI 작업하면 항상 최신 상태가 유지돼요. 자동으로 돌아가는 CCTV 같은 거예요.",
    usage: "vib watch",
    tips: ["AI 작업 중에 켜두면 편해요", "Ctrl+C로 끌 수 있어요", "GUI 홈 화면에서 버튼으로도 켤 수 있어요"],
  },
  {
    name: "transfer", icon: "📤", color: "#4D9FFF",
    title: "트랜스퍼",
    short: "다른 AI 툴로 이사갈 때",
    desc: "Claude에서 Cursor로, 또는 다른 AI 툴로 바꿀 때 '지금까지 뭘 했는지' 요약 파일을 만들어줘요. 새 AI한테 이 파일을 주면 처음부터 설명 안 해도 돼요.",
    usage: "vib transfer",
    tips: ["AI 툴 바꾸기 직전에 실행해요", "만들어진 PROJECT_CONTEXT.md를 새 AI에게 주세요"],
  },
  {
    name: "patch", icon: "🔧", color: "#FFD166",
    title: "패치",
    short: "말로 수정 요청 → 안전한 계획 생성",
    desc: "수정하고 싶은 걸 말로 설명하면, 어느 파일 어느 부분을 바꿔야 하는지 계획을 세워줘요. 직접 코드를 바꾸는 게 아니라 '여기 바꾸세요' 지시서를 만들어주는 거예요.",
    usage: "vib patch \"로그인 버튼 색깔 바꿔줘\"",
    tips: ["코드 수정 전에 뭘 바꿔야 하는지 확인할 수 있어요", "AI한테 그대로 전달하면 돼요"],
  },
  {
    name: "protect", icon: "🔒", color: "#FF4D4D",
    title: "프로텍트",
    short: "중요 파일 잠금 — AI 접근 금지",
    desc: "절대 건드리면 안 되는 파일을 잠가요. 잠긴 파일은 guard 검사에서 위반 사항으로 잡혀요. 소중한 파일에 자물쇠 채우는 거예요.",
    usage: "vib protect 파일경로",
    tips: ["설정 파일, 비밀 키 파일 등을 잠가두세요", "vib guard 실행할 때 잠긴 파일 건드리면 경고해줘요"],
  },
  {
    name: "secrets", icon: "🔑", color: "#FFE44D",
    title: "시크릿",
    short: "API 키가 실수로 올라가는 거 막기",
    desc: "API 키, 비밀번호 같은 걸 실수로 GitHub에 올리는 걸 막아줘요. 커밋하기 전에 자동으로 체크해서 '위험한 내용 발견!' 하고 알려줘요.",
    usage: "vib secrets",
    tips: ["git commit 전에 자동으로 실행되게 설정할 수 있어요", "비밀 정보가 발견되면 커밋을 막아줘요"],
  },
  {
    name: "explain", icon: "💬", color: "#7B4DFF",
    title: "익스플레인",
    short: "뭐가 바뀌었는지 쉽게 설명",
    desc: "최근에 바뀐 파일들을 분석해서 '이게 바뀌었어요'를 알기 쉽게 설명해줘요. AI가 뭘 했는지 한눈에 파악하고 싶을 때 써요.",
    usage: "vib explain",
    tips: ["AI 작업 후에 실행하면 뭐가 바뀌었는지 바로 알 수 있어요", "--since-minutes 30 하면 30분 이내 변경사항만 봐요"],
  },
];

// ── 컴포넌트 ──────────────────────────────────────────────────────────────────
export default function Home({ projectDir, onNavigate }: HomeProps) {
  const [view, setView]                   = useState<View>("home");
  const [selectedCmd, setSelectedCmd]     = useState<typeof COMMANDS[0] | null>(null);
  const [guardState, setGuardState]       = useState<CardState>("idle");
  const [guardResult, setGuardResult]     = useState<{ status: string; summary: string } | null>(null);
  const [scanState, setScanState]         = useState<CardState>("idle");
  const [watchOn, setWatchOn]             = useState(false);
  const [watchLoading, setWatchLoading]   = useState(false);
  const [mapMode, setMapMode]             = useState<"manual" | "auto">("manual");
  const [transferState, setTransferState] = useState<CardState>("idle");
  const [error, setError]                 = useState<string | null>(null);

  async function handleGuard() {
    setGuardState("loading"); setGuardResult(null); setError(null);
    try {
      const r = await vibGuard(projectDir);
      setGuardResult({ status: r.status, summary: r.summary });
      setGuardState("done");
    } catch (e) { setError(String(e)); setGuardState("error"); }
  }

  async function handleScan() {
    setScanState("loading"); setError(null);
    try {
      const r = await vibScan(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setScanState("done");
    } catch (e) { setError(String(e)); setScanState("error"); }
  }

  async function handleToggleWatch() {
    setWatchLoading(true); setError(null);
    try {
      if (watchOn) { await stopWatch(); setWatchOn(false); }
      else { await startWatch(projectDir); setWatchOn(true); }
    } catch (e) { setError(String(e)); }
    finally { setWatchLoading(false); }
  }

  async function handleTransfer() {
    setTransferState("loading"); setError(null);
    try {
      const r = await vibTransfer(projectDir);
      if (!r.ok) throw new Error(r.stderr || `exit ${r.exit_code}`);
      setTransferState("done");
    } catch (e) { setError(String(e)); setTransferState("error"); }
  }

  function guardColor(status: string) {
    if (status === "pass") return "#4DFF91";
    if (status === "warn") return "#FFD166";
    return "#FF4D4D";
  }

  // ── 메뉴얼 커맨드 상세 뷰 ────────────────────────────────────────────────────
  if (view === "manual_detail" && selectedCmd) {
    const cmd = selectedCmd;
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div className="page-header" style={{ padding: "12px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setView("manual_list")} style={{ fontSize: 11 }}>← 목록</button>
            <div style={{ width: 32, height: 32, background: cmd.color, border: "2px solid #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>
              {cmd.icon}
            </div>
            <div>
              <div style={{ fontWeight: 900, fontSize: 14 }}>{cmd.title}</div>
              <div style={{ fontSize: 10, color: "#666" }}>vib {cmd.name}</div>
            </div>
          </div>
        </div>

        <div className="page-content">
          {/* 한 줄 설명 배지 */}
          <div style={{ background: cmd.color + "22", border: `2px solid ${cmd.color}`, padding: "10px 14px", marginBottom: 12, fontWeight: 700, fontSize: 12 }}>
            {cmd.short}
          </div>

          {/* 본문 설명 */}
          <div className="card" style={{ marginBottom: 12, padding: "14px 16px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>어떤 기능이에요?</div>
            <div style={{ fontSize: 13, lineHeight: 1.8, color: "#1A1A1A" }}>{cmd.desc}</div>
          </div>

          {/* 사용법 */}
          <div className="terminal" style={{ marginBottom: 12 }}>
            <div className="terminal-header">
              <div className="terminal-dot red" />
              <div className="terminal-dot yellow" />
              <div className="terminal-dot green" />
            </div>
            <div style={{ marginTop: 4 }}>
              <span className="terminal-prompt">$ </span>
              <span style={{ color: "#FFD166", fontWeight: 700 }}>{cmd.usage}</span>
            </div>
          </div>

          {/* 팁 */}
          <div className="card" style={{ padding: "14px 16px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>💡 이렇게 써요</div>
            {cmd.tips.map((tip, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 12, lineHeight: 1.6 }}>
                <span style={{ color: cmd.color, fontWeight: 900, flexShrink: 0 }}>▸</span>
                <span>{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── 메뉴얼 커맨드 목록 뷰 ────────────────────────────────────────────────────
  if (view === "manual_list") {
    return (
      <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <div className="page-header" style={{ padding: "12px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setView("home")} style={{ fontSize: 11 }}>← 홈</button>
            <span className="page-title">MANUAL</span>
          </div>
          <div style={{ fontSize: 11, color: "#666", fontWeight: 600 }}>커맨드 {COMMANDS.length}개</div>
        </div>

        <div className="page-content">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            {COMMANDS.map((cmd) => (
              <div
                key={cmd.name}
                className="feature-card"
                style={{ cursor: "pointer" }}
                onClick={() => { setSelectedCmd(cmd); setView("manual_detail"); }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-2px)")}
                onMouseLeave={(e) => (e.currentTarget.style.transform = "")}
              >
                <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
                  <div className="feature-card-icon"
                    style={{ background: cmd.color, color: "#fff", borderColor: cmd.color, width: 26, height: 26, fontSize: 13, fontWeight: 900 }}>
                    {cmd.icon}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 11 }}>{cmd.title}</div>
                </div>
                <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
                  <div style={{ fontSize: 10, color: "#555", lineHeight: 1.5 }}>{cmd.short}</div>
                  <div style={{ marginTop: 4, fontSize: 9, fontFamily: "IBM Plex Mono, monospace", color: cmd.color, fontWeight: 700 }}>
                    vib {cmd.name}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── 홈 메인 뷰 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "14px 20px 12px" }}>
        <span className="page-title">HOME</span>
      </div>

      {error && <div className="alert alert-error" style={{ margin: "0 20px 8px" }}>{error}</div>}

      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>

          {/* ── 코드맵 생성 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#F5621E18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#F5621E", color: "#fff", borderColor: "#F5621E", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>MAP</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>코드맵</div>
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
                <button className="btn btn-sm" style={{ width: "100%", border: "2px solid #1A1A1A", background: watchOn ? "#FF4D4D" : "#F5621E", color: "#fff" }}
                  disabled={watchLoading} onClick={handleToggleWatch}>
                  {watchLoading ? <span className="spinner" /> : watchOn ? "STOP ■" : "WATCH ▶"}
                </button>
              )}
            </div>
          </div>

          {/* ── AI 폭주 방지 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#FF4D8B18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#FF4D8B", color: "#fff", borderColor: "#FF4D8B", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>♥</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>AI 방지</div>
              {guardState === "done" && guardResult && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: guardColor(guardResult.status), color: "#1A1A1A", border: "1px solid #1A1A1A" }}>
                  {guardResult.status.toUpperCase()}
                </span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
                {guardResult ? guardResult.summary.slice(0, 40) + "…" : "프로젝트 상태 점검"}
              </div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#FF4D8B", color: "#fff", border: "2px solid #1A1A1A" }}
                disabled={guardState === "loading"} onClick={handleGuard}>
                {guardState === "loading" ? <span className="spinner" /> : "GUARD ▶"}
              </button>
            </div>
          </div>

          {/* ── 원클릭 복구 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#7B4DFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>↺</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>복구</div>
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>체크포인트 목록</div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
                onClick={() => onNavigate("checkpoints")}>열기 ▶</button>
            </div>
          </div>

          {/* ── AI 이동 자유 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#4D9FFF18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#4D9FFF", color: "#fff", borderColor: "#4D9FFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}>⇄</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>AI 이동</div>
              {transferState === "done" && (
                <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>
              )}
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>PROJECT_CONTEXT 생성</div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A" }}
                disabled={transferState === "loading"} onClick={handleTransfer}>
                {transferState === "loading" ? <span className="spinner" /> : "TRANSFER ▶"}
              </button>
            </div>
          </div>

          {/* ── 폴더 열기 ── */}
          <div className="feature-card" style={{ cursor: "default" }}>
            <div className="feature-card-header" style={{ background: "#FFE44D18", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#FFE44D", color: "#1A1A1A", borderColor: "#FFE44D", width: 28, height: 28, fontSize: 14, fontWeight: 900 }}>⌂</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>폴더 열기</div>
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 10, color: "#888", marginBottom: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {projectDir.split("/").at(-1)}
              </div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#FFE44D", color: "#1A1A1A", border: "2px solid #1A1A1A", fontWeight: 700 }}
                onClick={() => openFolder(projectDir).catch((e) => setError(String(e)))}>
                Finder ▶
              </button>
            </div>
          </div>

          {/* ── 메뉴얼 ── */}
          <div className="feature-card" style={{ cursor: "pointer" }}
            onClick={() => setView("manual_list")}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#1A1A1A08")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "")}>
            <div className="feature-card-header" style={{ background: "#4DFF9118", padding: "10px 14px" }}>
              <div className="feature-card-icon"
                style={{ background: "#1A1A1A", color: "#4DFF91", borderColor: "#1A1A1A", width: 28, height: 28, fontSize: 14, fontWeight: 900 }}>?</div>
              <div style={{ fontWeight: 700, fontSize: 12, flex: 1 }}>메뉴얼</div>
              <span style={{ fontSize: 9, fontWeight: 700, color: "#888" }}>{COMMANDS.length}개</span>
            </div>
            <div className="feature-card-body" style={{ padding: "8px 14px 10px" }}>
              <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>모든 커맨드 보기</div>
              <button className="btn btn-sm" style={{ width: "100%", background: "#1A1A1A", color: "#4DFF91", border: "2px solid #1A1A1A" }}>
                열기 ▶
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
// === ANCHOR: HOME_END ===
