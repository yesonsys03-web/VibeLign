// === ANCHOR: PATCH_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { PATCH_COMMAND } from "../../../lib/commands";

export default function PatchCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={PATCH_COMMAND} {...props} />;
}
// === ANCHOR: PATCH_CARD_END ===
