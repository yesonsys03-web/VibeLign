// === ANCHOR: ANCHOR_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "anchor")!;

export default function AnchorCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: ANCHOR_CARD_END ===
