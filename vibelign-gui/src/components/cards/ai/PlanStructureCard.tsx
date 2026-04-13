// === ANCHOR: PLAN_STRUCTURE_CARD_START ===
import { useEffect, useMemo, useRef, useState } from "react";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";
import { buildGuiAiEnv, runVib } from "../../../lib/vib";
import type { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "plan-structure")!;

const FEATURE_KEYWORDS = [
  "oauth", "auth", "login", "token", "watch", "monitor", "scan", "mcp", "handler",
  "cli", "command", "test", "spec", "doc", "docs", "readme", "manual",
  "로그인", "인증", "토큰", "감시", "스캔", "핸들러", "명령", "테스트", "문서", "리드미", "매뉴얼",
];

const STRUCTURE_ONLY_HINTS = [
  "한 파일", "한곳", "몰아", "몰아넣", "분리", "나눠", "구조", "정리", "최소 수정", "새 파일", "연결만", "wiring",
];

type PlanSummary = {
  savedPath: string;
  summary: string;
  allowedFiles: string[];
  newFiles: string[];
  warnings: string[];
  forbiddenRules: string[];
};

type PlanJsonPayload = {
  plan_path?: string;
  plan?: {
    messages?: { summary?: string; warnings?: string[] };
    allowed_modifications?: Array<{ path?: string; anchor?: string }>;
    required_new_files?: Array<{ path?: string }>;
    forbidden?: Array<{ reason?: string; path?: string; anchor?: string }>;
  };
};

type ClarifyChoice = {
  id: string;
  label: string;
  description: string;
  buildRequest: (base: string) => string;
};

type ClarifyPrompt = {
  title: string;
  body: string;
  choices: ClarifyChoice[];
};

const LOG_DISPLAY_CHOICES: ClarifyChoice[] = [
  {
    id: "button-panel",
    label: "버튼 + 패널 열기",
    description: "상단 버튼을 누르면 실시간 로그 패널이 열려요.",
    buildRequest: () => "상단의 폴더열기 오른쪽에 실시간 로그 버튼 추가해줘. 누르면 로그 패널이 열리게 해줘.",
  },
  {
    id: "menu-dropdown",
    label: "메뉴 + 드롭다운 보기",
    description: "상단 메뉴를 누르면 watch 로그를 바로 펼쳐서 보여줘요.",
    buildRequest: () => "상단의 폴더열기 오른쪽에 실시간 로그 메뉴 추가해줘. 클릭하면 watch 로그를 드롭다운으로 보여줘.",
  },
  {
    id: "recommended",
    label: "추천 방식으로 진행",
    description: "현재 구조에 맞는 방식으로 VibeLign이 정해서 진행해요.",
    buildRequest: () => "상단의 폴더열기 오른쪽에 실시간 로그 버튼 추가해줘. 클릭하면 watch 로그를 볼 수 있는 패널이 열리게 해줘.",
  },
];

function summarizePlanPayload(payload: PlanJsonPayload): PlanSummary {
  const plan = payload.plan;
  const allowedFiles = (plan?.allowed_modifications ?? []).map((item) => {
    const path = item.path?.trim() || "";
    const anchor = item.anchor?.trim();
    return anchor ? `${path} (${anchor})` : path;
  }).filter(Boolean);
  const newFiles = (plan?.required_new_files ?? []).map((item) => item.path?.trim() || "").filter(Boolean);
  const warnings = (plan?.messages?.warnings ?? []).map((item) => String(item).trim()).filter(Boolean);
  const forbiddenRules = (plan?.forbidden ?? []).map((item) => {
    const reason = item.reason?.trim();
    if (reason) return reason;
    const path = item.path?.trim() || "알 수 없는 경로";
    const anchor = item.anchor?.trim();
    return anchor ? `${path} / ${anchor} 범위 밖 수정 금지` : `${path} 수정 금지`;
  }).filter(Boolean);
  return {
    savedPath: payload.plan_path?.trim() || "",
    summary: plan?.messages?.summary?.trim() || "",
    allowedFiles,
    newFiles,
    warnings,
    forbiddenRules,
  };
}

function getClarifyPrompt(request: string): ClarifyPrompt | null {
  const normalized = request.trim().toLowerCase();
  if (!normalized) return null;

  const hasFeatureKeyword = FEATURE_KEYWORDS.some((keyword) => normalized.includes(keyword));
  const hasStructureHint = STRUCTURE_ONLY_HINTS.some((keyword) => normalized.includes(keyword));
  const tokenCount = normalized.split(/\s+/).filter(Boolean).length;

  const mentionsLog = normalized.includes("로그") || normalized.includes("log");
  const mentionsDisplayIntent =
    normalized.includes("실시간") ||
    normalized.includes("보여") ||
    normalized.includes("볼 수") ||
    normalized.includes("메뉴") ||
    normalized.includes("버튼") ||
    normalized.includes("추가") ||
    normalized.includes("상단");

  if (mentionsLog && mentionsDisplayIntent && !normalized.includes("패널") && !normalized.includes("드롭다운")) {
    return {
      title: "실시간 로그를 어떻게 보여드릴까요?",
      body: "원하는 방식이 조금 더 필요해요. 아래에서 고르면 요청을 제가 완성해서 구조 계획을 만들게요.",
      choices: LOG_DISPLAY_CHOICES,
    };
  }

  if (!hasFeatureKeyword && (hasStructureHint || tokenCount <= 6)) {
    return {
      title: "무엇을 만들지는 아직 조금 모호해요",
      body: "'한 파일에 몰아넣지 마' 같은 구조 조건만으로는 정확한 계획이 어려워요. 예: 'OAuth 로그인 추가해줘. 한 파일에 몰아넣지 말아줘'처럼 기능과 구조 조건을 함께 적어주세요.",
      choices: [],
    };
  }

  return null;
}

async function runPlanStructure(
  requestText: string,
  projectDir: string,
  useAi: boolean,
  providerKeys: Record<string, string> | undefined,
  apiKey: string | null | undefined,
) {
  const args = ["plan-structure", requestText];
  if (useAi) args.push("--ai");
  args.push("--json");
  const env = useAi ? buildGuiAiEnv(providerKeys, apiKey) : undefined;
  return runVib(args, projectDir, env);
}

function buildAiImplementationPrompt(summary: PlanSummary, requestText: string): string {
  const allowedLines = summary.allowedFiles.length > 0
    ? summary.allowedFiles.map((file) => `- ${file}`).join("\n")
    : "- 기존 파일은 plan summary에 맞는 최소 범위만 수정하세요.";
  const newFileLines = summary.newFiles.length > 0
    ? summary.newFiles.map((file) => `- ${file}`).join("\n")
    : "- 신규 파일 생성은 필요하지 않거나 plan에 명시되지 않았습니다.";
  const warningLines = summary.warnings.length > 0
    ? summary.warnings.map((item) => `- ${item}`).join("\n")
    : "- 별도 경고 없음";
  const forbiddenLines = summary.forbiddenRules.length > 0
    ? summary.forbiddenRules.map((item) => `- ${item}`).join("\n")
    : "- 별도 금지 규칙 없음";

  return [
    "다음 구조 계획을 먼저 검토한 뒤, 허용된 범위 안에서만 구현하세요.",
    "",
    "[사용자 요청]",
    requestText,
    "",
    "[구조 계획 요약]",
    summary.summary || "기존 파일은 최소 수정하고 필요한 기능은 plan에 맞게 분리합니다.",
    summary.savedPath ? `계획 파일: ${summary.savedPath}` : "",
    "",
    "[수정 가능한 기존 파일]",
    allowedLines,
    "",
    "[생성 가능한 새 파일]",
    newFileLines,
    "",
    "[주의 / 제약]",
    "- plan에 없는 파일을 새로 만들지 마세요.",
    "- 기존 파일에는 허용된 범위를 넘는 큰 구현을 넣지 마세요.",
    "- 가능하면 기존 파일은 wiring/연결만 수정하고 기능 본문은 plan에 맞게 분리하세요.",
    forbiddenLines,
    warningLines,
    "",
    "[작업 방식]",
    "1. 먼저 이 plan이 구현에 충분한지 짧게 검토하세요.",
    "2. plan 범위 안에서만 구현하세요.",
    "3. 작업 후 vib guard 또는 동등한 검증으로 plan 이탈 여부를 확인하세요.",
  ].filter(Boolean).join("\n");
}

interface PlanStructureCardProps extends Omit<GenericCommandCardProps, "cmd"> {}

export default function PlanStructureCard({
  projectDir,
  apiKey,
  providerKeys,
  hasAnyAiKey = false,
  aiKeyStatusLoaded = false,
  onOpenSettings,
}: PlanStructureCardProps) {
  const [request, setRequest] = useState("");
  const [useAi, setUseAi] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [output, setOutput] = useState("");
  const [planSummary, setPlanSummary] = useState<PlanSummary | null>(null);
  const [clarifyPrompt, setClarifyPrompt] = useState<ClarifyPrompt | null>(null);
  const [resolvedRequest, setResolvedRequest] = useState("");
  const [handoffStatus, setHandoffStatus] = useState<"idle" | "copied" | "error">("idle");
  const [handoffPromptPreview, setHandoffPromptPreview] = useState("");
  const idleTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    return () => {
      if (idleTimer.current !== undefined) {
        window.clearTimeout(idleTimer.current);
      }
    };
  }, []);

  const parsed = useMemo(() => planSummary, [planSummary]);
  const hasParsedPlan = Boolean(parsed && (parsed.summary || parsed.allowedFiles.length > 0 || parsed.newFiles.length > 0));
  const textColor = CMD.color === "#FFD166" || CMD.color === "#FFE44D" ? "#1A1A1A" : "#fff";

  function clearTransientState() {
    setOutput("");
    setPlanSummary(null);
    setShowDetails(false);
    setHandoffStatus("idle");
    setHandoffPromptPreview("");
    if (idleTimer.current !== undefined) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = undefined;
    }
  }

  async function executePlanRequest(requestText: string) {
    setClarifyPrompt(null);
    setResolvedRequest(requestText);
    setStatus("loading");
    clearTransientState();

    try {
      const result = await runPlanStructure(requestText, projectDir, useAi, providerKeys, apiKey);
      const stdout = result.stdout.trim();
      if (!result.ok) {
        throw new Error(result.stderr || stdout || `exit ${result.exit_code}`);
      }
      const envelope = JSON.parse(stdout) as { ok?: boolean; data?: PlanJsonPayload; error?: string };
      if (envelope.ok === false || !envelope.data?.plan) {
        throw new Error(envelope.error || "구조 계획 JSON 결과를 읽지 못했어요.");
      }
      setPlanSummary(summarizePlanPayload(envelope.data));
      setStatus("done");
      setOutput("");
      if (result.ok) {
        idleTimer.current = window.setTimeout(() => {
          setStatus("idle");
          idleTimer.current = undefined;
        }, 3000);
      }
    } catch (error) {
      setStatus("error");
      setOutput(String(error));
    }
  }

  async function handleRun() {
    const trimmed = request.trim();
    if (!trimmed) {
      setClarifyPrompt(null);
      setResolvedRequest("");
      setStatus("error");
      setOutput("무엇을 만들고 싶은지 한 줄로 적어주세요.");
      return;
    }
    const nextClarifyPrompt = getClarifyPrompt(trimmed);
    if (nextClarifyPrompt) {
      setResolvedRequest("");
      setClarifyPrompt(nextClarifyPrompt);
      clearTransientState();
      setStatus(nextClarifyPrompt.choices.length > 0 ? "idle" : "error");
      setOutput(nextClarifyPrompt.choices.length > 0 ? "" : nextClarifyPrompt.body);
      return;
    }
    if (useAi && aiKeyStatusLoaded && !hasAnyAiKey) {
      setClarifyPrompt(null);
      setStatus("error");
      setOutput("AI 옵션을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      if (onOpenSettings) {
        onOpenSettings("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      }
      return;
    }
    await executePlanRequest(trimmed);
  }

  async function handleClarifyChoice(choice: ClarifyChoice) {
    if (useAi && aiKeyStatusLoaded && !hasAnyAiKey) {
      setStatus("error");
      setOutput("AI 옵션을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      if (onOpenSettings) {
        onOpenSettings("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      }
      return;
    }
    await executePlanRequest(choice.buildRequest(request.trim()));
  }

  async function handleCopyAiPrompt() {
    const finalRequest = resolvedRequest || request.trim();
    if (!parsed) return;
    const prompt = buildAiImplementationPrompt(parsed, finalRequest);
    try {
      await navigator.clipboard.writeText(prompt);
      setHandoffStatus("copied");
      setHandoffPromptPreview("");
    } catch {
      setHandoffStatus("error");
      setHandoffPromptPreview(prompt);
    }
  }

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: CMD.color + "18", padding: "8px 12px" }}>
        <div
          className="feature-card-icon"
          style={{
            background: CMD.color,
            color: "#fff",
            borderColor: CMD.color,
            width: 22,
            height: 22,
            fontSize: 11,
            fontWeight: 900,
          }}
        >
          {CMD.icon}
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>안전한 구조 계획</span>
          <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            하고 싶은 작업만 적으면 수정 위치와 파일 분리를 먼저 정리해요
          </span>
        </div>
        {status === "done" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
        {status === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
      </div>

      <div className="feature-card-body" style={{ padding: "10px 12px 12px" }}>
        <div style={{ fontSize: 12, color: "#333", lineHeight: 1.45, marginBottom: 8 }}>
          경로나 파일 이름은 직접 적지 않아도 돼요. VibeLign이 알아서 찾고, 큰 파일은 나눠야 하는지도 먼저 판단해요.
        </div>

        <textarea
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="예: OAuth 로그인 추가해줘"
          rows={3}
          style={{
            width: "100%",
            fontSize: 11,
            padding: "8px 10px",
            border: "2px solid #1A1A1A",
            boxSizing: "border-box",
            fontFamily: "IBM Plex Mono, monospace",
            background: "#fff",
            resize: "vertical",
            marginBottom: 8,
          }}
        />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 9, border: "2px solid #1A1A1A" }}
            onClick={() => setShowAdvanced((open) => !open)}
          >
            {showAdvanced ? "고급 옵션 숨기기" : "고급 옵션 보기"}
          </button>
          {hasParsedPlan && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 9, border: "2px solid #1A1A1A" }}
              onClick={() => setShowDetails((open) => !open)}
            >
              {showDetails ? "자세히 숨기기" : "자세히 보기"}
            </button>
          )}
        </div>

        {showAdvanced && (
          <div style={{ border: "2px solid #1A1A1A", background: "#fff", padding: "8px 10px", marginBottom: 8 }}>
            <div style={{ fontSize: 10, color: "#444", marginBottom: 6 }}>
              초보자라면 기본 설정 그대로 두는 걸 추천해요.
            </div>
            <button
              type="button"
              onClick={() => setUseAi((value) => !value)}
              style={{
                fontSize: 9,
                fontWeight: 700,
                padding: "2px 6px",
                border: "2px solid #1A1A1A",
                background: useAi ? "#1A1A1A" : "#fff",
                color: useAi ? "#fff" : "#1A1A1A",
                cursor: "pointer",
              }}
            >
              AI 보조 계획 {useAi ? "켜짐" : "꺼짐"}
            </button>
          </div>
        )}

        {!output && (
          <div style={{ fontSize: 11, color: "#555", lineHeight: 1.5, marginBottom: 8 }}>
            계획을 만들면 먼저 <strong>기존 파일은 얼마나 건드릴지</strong>, <strong>새 파일로 나눌지</strong>를 쉬운 말로 보여드릴게요.
          </div>
        )}

        {clarifyPrompt && clarifyPrompt.choices.length > 0 && (
          <div style={{ border: "2px solid #1A1A1A", background: "#FEFBF0", padding: "10px 12px", marginBottom: 8 }}>
            <div style={{ fontWeight: 800, fontSize: 13, marginBottom: 6 }}>{clarifyPrompt.title}</div>
            <div style={{ fontSize: 11, lineHeight: 1.5, color: "#222", marginBottom: 8 }}>{clarifyPrompt.body}</div>
            <div style={{ display: "grid", gap: 6 }}>
              {clarifyPrompt.choices.map((choice) => (
                <button
                  key={choice.id}
                  type="button"
                  className="btn btn-ghost btn-sm"
                  style={{ border: "2px solid #1A1A1A", textAlign: "left", justifyContent: "flex-start", padding: "8px 10px" }}
                  onClick={() => void handleClarifyChoice(choice)}
                >
                  <span style={{ display: "block", fontSize: 10.5, fontWeight: 800, color: "#1A1A1A" }}>{choice.label}</span>
                  <span style={{ display: "block", fontSize: 9.5, color: "#555", marginTop: 2 }}>{choice.description}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {resolvedRequest && !clarifyPrompt && !output && status === "loading" && (
          <div style={{ border: "2px solid #1A1A1A", background: "#fff", padding: "8px 10px", marginBottom: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 4 }}>이 요청으로 진행할게요</div>
            <div style={{ fontSize: 10, color: "#333", lineHeight: 1.5 }}>{resolvedRequest}</div>
          </div>
        )}

        {hasParsedPlan && status !== "error" && (
          <div style={{ border: "2px solid #1A1A1A", background: "#FEFBF0", padding: "10px 12px", marginBottom: 8 }}>
            <div style={{ fontWeight: 800, fontSize: 13, marginBottom: 6 }}>이렇게 하는 게 더 안전해요</div>
            <div style={{ fontSize: 11, lineHeight: 1.5, color: "#222", marginBottom: 8 }}>
              {parsed?.summary || "기존 파일은 조금만 수정하고, 필요한 기능은 새 파일로 나눠서 추가할게요."}
            </div>
            <div style={{ display: "grid", gap: 4, fontSize: 10.5, color: "#333" }}>
              <div>• 기존 파일: {parsed && parsed.allowedFiles.length > 0 ? `${parsed.allowedFiles.length}곳만 최소 수정` : "가능한 범위만 최소 수정"}</div>
              <div>• 새 파일: {parsed && parsed.newFiles.length > 0 ? `${parsed.newFiles.length}개로 분리 추가` : "새 파일 없이 진행 가능"}</div>
              <div>• 이유: 코드가 한 곳에 몰리지 않아 나중에 고치기 쉬워져요</div>
            </div>
            {parsed?.savedPath && (
              <div style={{ marginTop: 8, fontSize: 9, color: "#666" }}>계획 저장 위치: {parsed.savedPath}</div>
            )}
            <div style={{ display: "flex", gap: 6, marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
              <button
                type="button"
                className="btn btn-sm"
                style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
                onClick={() => void handleCopyAiPrompt()}
              >
                AI 검토용 프롬프트 복사
              </button>
              {handoffStatus === "copied" && (
                <span style={{ fontSize: 9, color: "#2f6f46", fontWeight: 700 }}>클립보드에 복사했어요. 사용하는 AI에 붙여넣어 시작하세요.</span>
              )}
              {handoffStatus === "error" && (
                <span style={{ fontSize: 9, color: "#b42318", fontWeight: 700 }}>자동 복사에 실패해서 아래 출력 영역에 프롬프트를 보여줬어요.</span>
              )}
            </div>
          </div>
        )}

        {showDetails && hasParsedPlan && parsed && (
          <div style={{ border: "2px solid #1A1A1A", background: "#fff", padding: "8px 10px", marginBottom: 8 }}>
            <div style={{ fontWeight: 700, fontSize: 11, marginBottom: 6 }}>자세한 계획</div>
            <div style={{ fontSize: 10, color: "#333", lineHeight: 1.5 }}>
              <div>수정할 기존 파일: {parsed.allowedFiles.length}개</div>
              <div>새로 만들 파일: {parsed.newFiles.length}개</div>
            </div>
            {parsed.allowedFiles.length > 0 && (
              <div style={{ marginTop: 6 }}>
                <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 4 }}>기존 파일</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 10, color: "#333" }}>
                  {parsed.allowedFiles.map((file) => (
                    <li key={file}>{file}</li>
                  ))}
                </ul>
              </div>
            )}
            {parsed.newFiles.length > 0 && (
              <div style={{ marginTop: 6 }}>
                <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 4 }}>새 파일</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 10, color: "#333" }}>
                  {parsed.newFiles.map((file) => (
                    <li key={file}>{file}</li>
                  ))}
                </ul>
              </div>
            )}
            {parsed.forbiddenRules.length > 0 && (
              <div style={{ marginTop: 6 }}>
                <div style={{ fontSize: 10, fontWeight: 700, marginBottom: 4 }}>금지 규칙</div>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 10, color: "#333" }}>
                  {parsed.forbiddenRules.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {handoffPromptPreview && (
          <GuiCliOutputBlock
            text={handoffPromptPreview}
            placeholder=""
            variant="default"
          />
        )}

        {output && (!hasParsedPlan || status === "error") && (
          <GuiCliOutputBlock
            text={output}
            placeholder=""
            variant={status === "error" ? "error" : "default"}
          />
        )}

        <button
          className="btn btn-sm"
          style={{ width: "100%", background: CMD.color, color: textColor, border: "2px solid #1A1A1A", fontSize: 10 }}
          disabled={status === "loading"}
          onClick={handleRun}
        >
          {status === "loading" ? <span className="spinner" /> : "계획 만들기"}
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: PLAN_STRUCTURE_CARD_END ===
