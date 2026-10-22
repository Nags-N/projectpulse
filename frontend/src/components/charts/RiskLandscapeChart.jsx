import { useState } from "react";

export default function RiskLandscapeChart({ risks = [], onSelectRisk }) {
  const [selectedSeverity, setSelectedSeverity] = useState("ALL");

  const criticalRisks = risks.filter((r) => r.severity === "CRITICAL");
  const highRisks = risks.filter((r) => r.severity === "HIGH");
  const mediumRisks = risks.filter((r) => r.severity === "MEDIUM");
  const lowRisks = risks.filter((r) => r.severity === "LOW");

  const severityTiers = [
    {
      level: "CRITICAL",
      label: "Critical Risks",
      count: criticalRisks.length,
      color: "#ef4444",
      trend: criticalRisks.length > 0 ? "↑ Active" : "● Stable",
      trendColor: criticalRisks.length > 0 ? "#f87171" : "#34d399",
      items: criticalRisks,
    },
    {
      level: "HIGH",
      label: "High Risks",
      count: highRisks.length,
      color: "#f59e0b",
      trend: highRisks.length > 0 ? "↑ Review" : "● Clear",
      trendColor: highRisks.length > 0 ? "#fbbf24" : "#34d399",
      items: highRisks,
    },
    {
      level: "MEDIUM",
      label: "Medium Risks",
      count: mediumRisks.length,
      color: "#38bdf8",
      trend: "● Monitored",
      trendColor: "#38bdf8",
      items: mediumRisks,
    },
    {
      level: "LOW",
      label: "Low Risks",
      count: lowRisks.length,
      color: "#10b981",
      trend: "● Low Impact",
      trendColor: "#34d399",
      items: lowRisks,
    },
  ];

  const maxCount = Math.max(...severityTiers.map((t) => t.count), 1);
  const totalRisks = risks.length;

  const displayedRisks = selectedSeverity === "ALL"
    ? risks
    : risks.filter((r) => r.severity === selectedSeverity);

  return (
    <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="card__header-row">
        <div>
          <h2>🛡️ AI Risk Landscape</h2>
          <p className="card__subtitle">8 explainable rules assessing due dates & telemetry drift</p>
        </div>
        <span
          className={`badge ${
            totalRisks === 0
              ? "badge--success"
              : criticalRisks.length > 0
              ? "badge--danger"
              : "badge--warning"
          }`}
        >
          {totalRisks} Detected
        </span>
      </div>

      {/* Severity Distribution Bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem", marginBottom: "1.25rem" }}>
        {severityTiers.map((tier) => {
          const pct = Math.max(8, (tier.count / maxCount) * 100);
          const isSelected = selectedSeverity === tier.level;

          return (
            <div
              key={tier.level}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.25rem",
                cursor: "pointer",
                padding: "0.35rem 0.5rem",
                borderRadius: "6px",
                background: isSelected ? "rgba(255, 255, 255, 0.05)" : "transparent",
                transition: "all 0.15s ease",
              }}
              onClick={() => setSelectedSeverity(isSelected ? "ALL" : tier.level)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.78rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: tier.color }} />
                  <strong style={{ color: "#fff" }}>{tier.label}</strong>
                  <span style={{ fontSize: "0.72rem", color: tier.trendColor }}>{tier.trend}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#fff", fontSize: "0.9rem" }}>
                    {tier.count}
                  </span>
                </div>
              </div>

              <div style={{ width: "100%", height: "8px", background: "rgba(255, 255, 255, 0.06)", borderRadius: "999px", overflow: "hidden" }}>
                <div
                  style={{
                    width: tier.count > 0 ? `${pct}%` : "0%",
                    height: "100%",
                    background: tier.color,
                    borderRadius: "999px",
                    boxShadow: tier.count > 0 ? `0 0 8px ${tier.color}` : "none",
                    transition: "width 0.5s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Filtered Risk Cards / Empty State */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.65rem", maxHeight: "240px" }}>
        {displayedRisks.length === 0 ? (
          <div style={{ textAlign: "center", padding: "1.5rem 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            <span style={{ color: "#10b981", fontSize: "1.2rem", display: "block", marginBottom: "0.35rem" }}>✓</span>
            No {selectedSeverity !== "ALL" ? selectedSeverity.toLowerCase() : ""} risk discrepancies detected.
          </div>
        ) : (
          displayedRisks.map((risk, idx) => (
            <div
              key={idx}
              className={`risk-item risk-item--${(risk.severity || "medium").toLowerCase()}`}
              style={{ padding: "0.75rem", fontSize: "0.82rem", cursor: "pointer" }}
              onClick={() => onSelectRisk && onSelectRisk(risk)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", marginBottom: "0.35rem" }}>
                <strong style={{ color: "#fff" }}>{risk.title}</strong>
                {risk.task_id && (
                  <span className="badge badge--platform" style={{ fontSize: "0.7rem", flexShrink: 0 }}>
                    {risk.task_id}
                  </span>
                )}
              </div>
              <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.76rem" }}>
                {risk.explanation || risk.interpretation}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
