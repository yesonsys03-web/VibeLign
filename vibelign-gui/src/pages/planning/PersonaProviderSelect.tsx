import {
  PLANNING_PROVIDER_OPTIONS,
  effectivePersona,
} from "../../components/PlanningPersonaSettings";
import type { PlanningPersonaConfigMap } from "../../lib/vib";

export function providerOptionLabel(provider: string, installed: string[] | null): string {
  if (installed && !installed.includes(provider)) {
    return `${provider} (미설치)`;
  }
  return provider;
}

interface PersonaProviderSelectProps {
  readonly personaId: string;
  readonly map: PlanningPersonaConfigMap;
  readonly installed: string[] | null;
  readonly onChange: (provider: string) => void;
}

export function PersonaProviderSelect({ personaId, map, installed, onChange }: PersonaProviderSelectProps) {
  const eff = effectivePersona(map, personaId);
  return (
    <select
      aria-label={`${personaId} 모델`}
      value={eff.provider}
      onChange={(e) => onChange(e.target.value)}
      title="이 역할이 쓸 AI를 바꿔요. 없으면 다른 AI로 자동 대체돼요."
      style={{ border: "2px solid #1A1A1A", background: "#FFFFFF", color: "#1A1A1A", fontSize: 10, fontWeight: 700, padding: "2px 4px", cursor: "pointer" }}
    >
      {PLANNING_PROVIDER_OPTIONS.map((p) => (
        <option key={p} value={p}>
          {providerOptionLabel(p, installed)}
        </option>
      ))}
    </select>
  );
}
