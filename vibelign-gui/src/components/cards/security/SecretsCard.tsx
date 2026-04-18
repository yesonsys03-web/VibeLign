// === ANCHOR: SECRETS_CARD_START ===
import GenericCommandCard, { GenericCommandCardProps } from "../GenericCommandCard";
import { COMMANDS } from "../../../lib/commands";

const CMD = COMMANDS.find((c) => c.name === "secrets")!;

export default function SecretsCard(props: Omit<GenericCommandCardProps, "cmd">) {
  return <GenericCommandCard cmd={CMD} {...props} />;
}
// === ANCHOR: SECRETS_CARD_END ===
