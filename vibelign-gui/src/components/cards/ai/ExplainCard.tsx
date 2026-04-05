// === ANCHOR: EXPLAIN_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "explain")!;

export default function ExplainCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: EXPLAIN_CARD_END ===
