// === ANCHOR: USEDESIGNJOB_START ===
import { useCallback, useEffect, useRef, useState } from "react";
import type { StyleSpec } from "./styles";
import { synthesizeStyle, generateDesignMockup } from "../vib/design";
import { tokensToCssVars, replaceRootBlock } from "./customStyles";

export type DesignJobStatus = "idle" | "running" | "done" | "error";

export type RecolorKey = "bg" | "surface" | "primary" | "accent" | "text";

export type DesignRunParams =
  | { kind: "describe"; description: string; baseStyle?: StyleSpec }
  | { kind: "style"; style: StyleSpec; feedback?: string; previousHtml?: string };

export interface DesignJob {
  status: DesignJobStatus;
  phaseMsg: string;
  html: string | null;
  synth: StyleSpec | null;
  error: string | null;
  run: (params: DesignRunParams, planPath: string) => void;
  recolor: (key: RecolorKey, value: string) => void;
  clearSynth: () => void;
  reset: () => void;
}

// === ANCHOR: USEDESIGNJOB_USEDESIGNJOB_START ===
export function useDesignJob(projectDir: string): DesignJob {
  const [status, setStatus] = useState<DesignJobStatus>("idle");
  const [phaseMsg, setPhaseMsg] = useState("");
  const [html, setHtml] = useState<string | null>(null);
  const [synth, setSynth] = useState<StyleSpec | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seqRef = useRef(0);

  const reset = useCallback(() => {
    seqRef.current += 1; // 진행 중 잡 결과 무효화
    setStatus("idle");
    setPhaseMsg("");
    setHtml(null);
    setSynth(null);
    setError(null);
  }, []);

  // 프로젝트 전환/종료 시 이전 잡 잔여 제거
  useEffect(() => {
    reset();
  }, [projectDir, reset]);

  const run = useCallback(
    (params: DesignRunParams, planPath: string) => {
      const runSeq = ++seqRef.current;
      // === ANCHOR: USEDESIGNJOB_FRESH_START ===
      const fresh = () => seqRef.current === runSeq;
      setStatus("running");
      setError(null);
      void (async () => {
        try {
          if (params.kind === "describe") {
            setPhaseMsg("① AI가 스타일을 구상하는 중…");
            const spec = await synthesizeStyle({
              projectDir,
              planPath,
              description: params.description,
              baseStyle: params.baseStyle,
            });
            if (!fresh()) return;
            setSynth(spec);
            setPhaseMsg("② 화면 목업을 그리는 중… (최대 1~2분 걸려요)");
            const res = await generateDesignMockup({ projectDir, planPath, style: spec });
            if (!fresh()) return;
            setHtml(res.html);
          } else {
            setPhaseMsg("디자인을 그리는 중… (최대 1~2분 걸려요)");
            const res = await generateDesignMockup({
              projectDir,
              planPath,
              style: params.style,
              feedback: params.feedback,
              previousHtml: params.previousHtml,
            });
            if (!fresh()) return;
            setHtml(res.html);
          }
          if (!fresh()) return;
          setStatus("done");
        } catch (e) {
          if (!fresh()) return;
          setError(String(e));
          setStatus("error");
        }
      })();
      // === ANCHOR: USEDESIGNJOB_FRESH_END ===
    },
    [projectDir],
  );

  const recolor = useCallback(
    (key: RecolorKey, value: string) => {
      if (!synth) return;
      const tokens = { ...synth.tokens, [key]: value };
      const updated = { ...synth, tokens };
      setSynth(updated);
      if (html) setHtml(replaceRootBlock(html, tokensToCssVars(tokens, updated.motion)));
    },
    [synth, html],
  );

  const clearSynth = useCallback(() => setSynth(null), []);

// === ANCHOR: USEDESIGNJOB_USEDESIGNJOB_END ===
  return { status, phaseMsg, html, synth, error, run, recolor, clearSynth, reset };
}
// === ANCHOR: USEDESIGNJOB_END ===
