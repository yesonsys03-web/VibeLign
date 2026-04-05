// === ANCHOR: COMMANDS_START ===
export type CardState = "idle" | "loading" | "done" | "error";

export type { GuideLine, GuideStep, FlagDef } from "./commandData";
import { COMMANDS_CORE } from "./commandData";
import { COMMANDS_EXT } from "./commandData2";

export const COMMANDS = [...COMMANDS_CORE, ...COMMANDS_EXT];

export const PATCH_COMMAND = COMMANDS.find((c) => c.name === "patch")!;

/**
 * 커맨드 이름과 플래그 값으로 vib CLI 인수 배열을 만든다.
 * 필수 플래그가 누락되면 null을 반환한다.
 */
export function buildCmdArgs(
  name: string,
  cmdFlagValues: Record<string, Record<string, string | boolean>>
): string[] | null {
  const cmd = COMMANDS.find((c) => c.name === name);
  const flags = (cmd as any)?.flags as import("./commandData").FlagDef[] | undefined;
  if (!flags?.length) return [name];

  const fvals = cmdFlagValues[name] ?? {};
  const args: string[] = [name];
  let positional: string | null = null;

  for (const fd of flags) {
    const val: string | boolean =
      fvals[fd.key] ??
      (fd.type === "bool"
        ? false
        : fd.type === "select" && fd.options.length > 0
          ? fd.options[0].v
          : "");
    if (fd.key === "_mode" || fd.key === "_action") {
      if (val) args.push(...String(val).split(" ").filter(Boolean));
    } else if (fd.key === "_file" || fd.key === "_request" || fd.key === "_tool") {
      if (val) positional = String(val).trim();
    } else if (fd.key === "_question") {
      if (val) args.push(String(val).trim());
    } else if (fd.type === "bool" && val) {
      args.push(`--${fd.key}`);
    } else if (fd.type === "text" && val) {
      if (fd.numeric && isNaN(Number(String(val)))) continue;
      args.push(`--${fd.key}`, String(val));
    }
  }

  for (const fd of flags) {
    if ((fd as any).required) {
      const val = fvals[fd.key] ?? "";
      if (!val) return null;
    }
  }

  if (positional) args.splice(1, 0, positional);
  return args;
}
// === ANCHOR: COMMANDS_END ===
