import { useEffect, useState } from "react";
import {
  getPlanningPersonas,
  setPlanningPersonas,
  probePlanningProviders,
  type PlanningPersonaConfigMap,
} from "../lib/vib";
import { PLANNING_PERSONAS } from "../pages/planning/PlanningPersonas";

export const PLANNING_PROVIDER_OPTIONS = ["claude", "codex", "agy", "opencode"] as const;

const DEFAULT_PROVIDER: Record<string, string> = {
  chloe: "claude",
  gio: "codex",
  mina: "agy",
  deepseek: "opencode",
};

export interface EffectivePersona {
  enabled: boolean;
  provider: string;
}

/** 저장된 맵 + 기본값으로 페르소나의 실효 설정을 만든다. */
export function effectivePersona(map: PlanningPersonaConfigMap, id: string): EffectivePersona {
  const entry = map[id] ?? {};
  return {
    enabled: entry.enabled ?? true,
    provider: entry.provider ?? DEFAULT_PROVIDER[id] ?? "claude",
  };
}

/** 한 페르소나에 patch 를 적용해 완전한 엔트리로 기록(다른 페르소나는 보존). */
export function applyPersonaChange(
  map: PlanningPersonaConfigMap,
  id: string,
  patch: Partial<EffectivePersona>,
): PlanningPersonaConfigMap {
  const current = effectivePersona(map, id);
  return { ...map, [id]: { ...current, ...patch } };
}

export function PlanningPersonaSettings() {
  const [map, setMap] = useState<PlanningPersonaConfigMap>({});
  const [installed, setInstalled] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getPlanningPersonas().then(setMap).catch(() => setMap({}));
    probePlanningProviders().then(setInstalled).catch(() => setInstalled([]));
  }, []);

  async function persist(next: PlanningPersonaConfigMap) {
    setMap(next);
    setSaving(true);
    try {
      await setPlanningPersonas(next);
    } finally {
      setSaving(false);
    }
  }

  const change = (id: string, patch: Partial<EffectivePersona>) =>
    void persist(applyPersonaChange(map, id, patch));

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
        기획방 페르소나
      </div>
      <div style={{ fontSize: 11, color: "#777", lineHeight: 1.6, marginBottom: 12 }}>
        각 역할을 어떤 AI가 맡을지 고르고, 끄고 켤 수 있어요. 고른 AI가 없거나 로그인이 안 되어 있으면
        설치된 다른 AI로 자동 대체돼요. {saving && <span style={{ color: "#4DFF91" }}>저장 중…</span>}
      </div>
      {PLANNING_PERSONAS.map((persona) => {
        const eff = effectivePersona(map, persona.id);
        return (
          <div key={persona.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: 12, minWidth: 64 }}>{persona.label}</span>
            <span style={{ fontSize: 11, color: "#888", minWidth: 40 }}>{persona.role}</span>
            <select
              value={eff.provider}
              onChange={(e) => change(persona.id, { provider: e.target.value })}
              style={{ background: "#1A1A1A", color: "#7DFF6B", border: "1px solid #333", borderRadius: 4, padding: "3px 8px", fontSize: 11 }}
            >
              {PLANNING_PROVIDER_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                  {installed && !installed.includes(p) ? " (미설치)" : ""}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => change(persona.id, { enabled: !eff.enabled })}
              style={{
                background: eff.enabled ? "#4DFF91" : "#1A1A1A",
                color: eff.enabled ? "#1A1A1A" : "#888",
                border: "2px solid #1A1A1A",
                fontWeight: 700,
                minWidth: 52,
              }}
            >
              {eff.enabled ? "ON" : "OFF"}
            </button>
          </div>
        );
      })}
    </div>
  );
}
