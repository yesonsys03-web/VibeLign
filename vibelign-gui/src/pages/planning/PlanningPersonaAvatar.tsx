// === ANCHOR: PLANNINGPERSONAAVATAR_START ===
import { planningPersonaMeta } from "./PlanningPersonas";

interface PlanningPersonaAvatarProps {
  readonly personaId: string;
  readonly label?: string;
  readonly decorative?: boolean;
  readonly size?: number;
}

// === ANCHOR: PLANNINGPERSONAAVATAR_PLANNINGPERSONAAVATAR_START ===
export function PlanningPersonaAvatar({ personaId, label, decorative = false, size = 22 }: PlanningPersonaAvatarProps) {
  const meta = planningPersonaMeta(personaId, label);
  const style = {
    width: size,
    height: size,
    border: `2px solid ${meta.avatarBorder}`,
    background: meta.avatarBackground,
    color: meta.avatarColor,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    flex: "0 0 auto",
    fontSize: Math.max(10, Math.round(size * 0.48)),
    fontWeight: 900,
    lineHeight: 1,
  };
  if (decorative) {
    return (
      <span aria-hidden="true" style={style}>
        {meta.initial}
      </span>
    );
  }
  return (
    <span role="img" aria-label={`${meta.label} 아바타`} style={style}>
      {meta.initial}
    </span>
  );
}
// === ANCHOR: PLANNINGPERSONAAVATAR_PLANNINGPERSONAAVATAR_END ===
// === ANCHOR: PLANNINGPERSONAAVATAR_END ===
