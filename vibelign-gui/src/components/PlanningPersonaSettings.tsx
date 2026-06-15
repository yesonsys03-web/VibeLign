// === ANCHOR: PLANNINGPERSONASETTINGS_START ===
import { useEffect, useState } from "react";
import {
  getPlanningPersonas,
  setPlanningPersonas,
  probePlanningProviders,
  type PlanningPersonaConfigMap,
} from "../lib/vib";
import { PLANNING_PERSONAS } from "../pages/planning/PlanningPersonas";

export const PLANNING_ROLE_OPTIONS = [
  { id: "design", label: "설계" },
  { id: "review", label: "검토" },
  { id: "explore", label: "탐색" },
  { id: "assist", label: "조교" },
] as const;

// 페르소나 고정 모델(이름과 한 덩어리). 표시/설치확인용.
const PERSONA_MODEL: Record<string, string> = { chloe: "claude", gio: "codex", mina: "agy", deepseek: "opencode" };
const DEFAULT_ROLE: Record<string, string> = { chloe: "design", gio: "review", mina: "explore", deepseek: "assist" };

export interface EffectivePersona {
  enabled: boolean;
  role: string;
}

// === ANCHOR: PLANNINGPERSONASETTINGS_EFFECTIVEPERSONA_START ===
export function effectivePersona(map: PlanningPersonaConfigMap, id: string): EffectivePersona {
  const entry = map[id] ?? {};
  // 클로이(claude)는 claude -p 로 실행돼 구독 크레딧/API 가 차감될 수 있어 기본 OFF(opt-in).
  // 나머지 페르소나는 기본 ON. (Rust persona_default_enabled 와 일치)
  return { enabled: entry.enabled ?? id !== "chloe", role: entry.role ?? DEFAULT_ROLE[id] ?? "design" };
}
// === ANCHOR: PLANNINGPERSONASETTINGS_EFFECTIVEPERSONA_END ===

/** persona 에 newRole 을 주고, 그 역할을 갖고 있던 persona 와 1:1 맞교환. */
// === ANCHOR: PLANNINGPERSONASETTINGS_APPLYROLESWAP_START ===
export function applyRoleSwap(map: PlanningPersonaConfigMap, id: string, newRole: string): PlanningPersonaConfigMap {
  const current = effectivePersona(map, id);
  if (current.role === newRole) return map;
  const ids = PLANNING_PERSONAS.map((p) => p.id);
  const holder = ids.find((other) => other !== id && effectivePersona(map, other).role === newRole);
  const next: PlanningPersonaConfigMap = { ...map };
  next[id] = { ...effectivePersona(map, id), role: newRole };
  if (holder) {
    next[holder] = { ...effectivePersona(map, holder), role: current.role };
  }
  return next;
}
// === ANCHOR: PLANNINGPERSONASETTINGS_APPLYROLESWAP_END ===

// === ANCHOR: PLANNINGPERSONASETTINGS_PLANNINGPERSONASETTINGS_START ===
export function PlanningPersonaSettings() {
  const [map, setMap] = useState<PlanningPersonaConfigMap>({});
  const [installed, setInstalled] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getPlanningPersonas().then(setMap).catch(() => setMap({}));
    probePlanningProviders().then(setInstalled).catch(() => setInstalled([]));
  }, []);

  // === ANCHOR: PLANNINGPERSONASETTINGS_PERSIST_START ===
  async function persist(next: PlanningPersonaConfigMap) {
    setMap(next);
    setSaving(true);
    try {
      await setPlanningPersonas(next);
    } finally {
      setSaving(false);
    }
  }
  // === ANCHOR: PLANNINGPERSONASETTINGS_PERSIST_END ===

  // marginBottom: .page-content 의 마지막 카드라 뒤따르는 형제가 만들어 주던 여백이 없다.
  // WKWebView 는 컨테이너 padding-bottom 을 스크롤 영역에 안 넣어 테두리·그림자가 잘리므로
  // 카드 자체에 하단 여백을 줘서 전체가 보이게 한다.
  return (
    <div className="card" style={{ marginTop: 16, marginBottom: 40 }}>
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
        기획방 페르소나
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 12 }}>
        각 AI가 어떤 역할을 맡을지 고르세요. 역할을 바꾸면 그 역할을 갖고 있던 AI와 서로 맞바뀝니다.
        모델이 없거나 로그인이 안 되어 있으면 다른 모델로 자동 대체돼요. {saving && <span style={{ color: "#4DFF91" }}>저장 중…</span>}
      </div>
      {PLANNING_PERSONAS.map((persona) => {
        const eff = effectivePersona(map, persona.id);
        const model = PERSONA_MODEL[persona.id] ?? "";
        const modelOk = installed ? installed.includes(model) : true;
        return (
          <div key={persona.id} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 700, fontSize: 12, minWidth: 64 }}>{persona.label}</span>
            <span title={modelOk ? "설치됨" : "미설치 — 다른 모델로 자동 대체"} style={{ fontSize: 11, color: modelOk ? "#2f6f46" : "#A14B00", minWidth: 78 }}>
              {model}{modelOk ? "" : " (미설치)"}
            </span>
            {PERSONA_MODEL[persona.id] === "claude" && (
              <span
                title="클로이는 claude -p 로 실행돼요. 구독을 써도 별도 월 크레딧에서 차감되고, 크레딧 소진 후엔 API 요금이 청구될 수 있어요. 기본은 꺼져 있고, 켤 때만 호출됩니다."
                style={{ fontSize: 9, fontWeight: 800, padding: "1px 5px", background: "#FEF3C7", color: "#92400E", borderRadius: 3, whiteSpace: "nowrap" }}
              >
                ⚠ 크레딧 차감 가능
              </span>
            )}
            <select
              value={eff.role}
              onChange={(e) => void persist(applyRoleSwap(map, persona.id, e.target.value))}
              style={{ background: "#1A1A1A", color: "#7DFF6B", border: "1px solid #333", borderRadius: 4, padding: "3px 8px", fontSize: 11 }}
            >
              {PLANNING_ROLE_OPTIONS.map((r) => (
                <option key={r.id} value={r.id}>{r.label}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => void persist({ ...map, [persona.id]: { ...eff, enabled: !eff.enabled } })}
              style={{ background: eff.enabled ? "#4DFF91" : "#1A1A1A", color: eff.enabled ? "#1A1A1A" : "#888", border: "2px solid #1A1A1A", fontWeight: 700, minWidth: 52 }}
            >
              {eff.enabled ? "ON" : "OFF"}
            </button>
          </div>
        );
      })}
    </div>
// === ANCHOR: PLANNINGPERSONASETTINGS_PLANNINGPERSONASETTINGS_END ===
  );
}
// === ANCHOR: PLANNINGPERSONASETTINGS_END ===
