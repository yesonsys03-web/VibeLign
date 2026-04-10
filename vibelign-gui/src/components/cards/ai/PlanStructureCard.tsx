// === ANCHOR: PLAN_STRUCTURE_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "plan-structure")!;

export default function PlanStructureCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: PLAN_STRUCTURE_CARD_END ===
