export default function StatCard({ label, value, accent }) {
  const getAccentStyle = () => {
    switch (accent) {
      case "success":
        return { color: "#34d399", borderTop: "2px solid #10b981" };
      case "primary":
        return { color: "#38bdf8", borderTop: "2px solid #2563eb" };
      case "warning":
        return { color: "#fbbf24", borderTop: "2px solid #f59e0b" };
      case "danger":
        return { color: "#f87171", borderTop: "2px solid #ef4444" };
      default:
        return { color: "#fff", borderTop: "2px solid rgba(255, 255, 255, 0.08)" };
    }
  };

  const accentStyle = getAccentStyle();

  return (
    <div
      className={`stat-card ${accent ? `stat-card--${accent}` : ""}`}
      style={{
        background: "rgba(11, 17, 32, 0.8)",
        border: "1px solid var(--border-subtle)",
        borderTop: accentStyle.borderTop,
        borderRadius: "8px",
        padding: "0.85rem 1rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.2rem",
        transition: "all 0.15s ease",
      }}
    >
      <div
        className="stat-card__value"
        style={{
          fontSize: "1.65rem",
          fontWeight: 800,
          color: accentStyle.color,
          lineHeight: 1.1,
          fontFamily: "monospace",
        }}
      >
        {value}
      </div>
      <div
        className="stat-card__label"
        style={{
          fontSize: "0.72rem",
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </div>
    </div>
  );
}
