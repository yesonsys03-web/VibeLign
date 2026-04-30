import { useState, type CSSProperties, type ReactNode } from "react";

interface BackupCardProps {
  icon: ReactNode;
  title: string;
  subtitle: string;
  children: ReactNode;
  headerStyle: CSSProperties;
  iconStyle: CSSProperties;
  actions?: ReactNode;
  bodyStyle?: CSSProperties;
  sectionStyle?: CSSProperties;
}

export default function BackupCard({ icon, title, subtitle, children, headerStyle, iconStyle, actions, bodyStyle, sectionStyle }: BackupCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <section className="feature-card" style={{ cursor: "default", ...sectionStyle }}>
      <div className="feature-card-header" style={headerStyle}>
        <div className="feature-card-icon" style={iconStyle}>{icon}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 900, fontSize: title === "안전하게 보관 중" || title === "첫 저장이 필요해요" ? 20 : 17 }}>{title}</div>
          <div style={{ fontSize: title === "안전하게 보관 중" || title === "첫 저장이 필요해요" ? 12 : 11, color: title === "안전하게 보관 중" || title === "첫 저장이 필요해요" ? "#3A3A3A" : "#555" }}>{subtitle}</div>
        </div>
        {actions ? <div style={{ display: "flex", gap: 4, alignItems: "center" }}>{actions}</div> : null}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((value) => !value)}
          title={collapsed ? "펼치기" : "접기"}
        >
          {collapsed ? "펼치기" : "접기"}
        </button>
      </div>
      {!collapsed ? <div className="feature-card-body" style={bodyStyle}>{children}</div> : null}
    </section>
  );
}
