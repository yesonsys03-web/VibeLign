// === ANCHOR: CLAUDE_HOOK_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "claude-hook")!;

export default function ClaudeHookCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: CLAUDE_HOOK_CARD_END ===
