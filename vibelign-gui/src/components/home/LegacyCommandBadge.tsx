type LegacyCommandBadgeProps = {
  readonly visibility?: string;
};

export default function LegacyCommandBadge({ visibility }: LegacyCommandBadgeProps) {
  if (visibility !== "legacy") return null;

  return (
    <span
      style={{
        fontSize: 9,
        fontWeight: 800,
        color: "#8A5A00",
        background: "#FFF2C2",
        border: "1px solid #E5C15A",
        borderRadius: 4,
        padding: "1px 4px",
      }}
    >
      legacy
    </span>
  );
}
