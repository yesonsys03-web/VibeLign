// === ANCHOR: PATCH_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { getPatchCommand } from "../../../lib/commands";

export default function PatchCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={getPatchCommand()} {...props} />;
}
// === ANCHOR: PATCH_CARD_END ===
