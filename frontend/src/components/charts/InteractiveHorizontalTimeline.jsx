import { useState } from "react";

export default function InteractiveHorizontalTimeline({ events = [], onFilterChange, activeFilter = "ALL" }) {
  const [selectedEvent, setSelectedEvent] = useState(null);

  const filterSources = ["ALL", "JIRA", "DEV", "GIT", "BUILD", "TEST", "QA", "AI"];

  const getSourceConfig = (source) => {
    switch (source?.toUpperCase()) {
      case "JIRA":
        return { icon: "🔷", color: "#38bdf8", bg: "rgba(56, 189, 248, 0.15)", border: "rgba(56, 189, 248, 0.3)" };
      case "DEV":
        return { icon: "💻", color: "#a855f7", bg: "rgba(168, 85, 247, 0.15)", border: "rgba(168, 85, 247, 0.3)" };
      case "GIT":
        return { icon: "🔀", color: "#60a5fa", bg: "rgba(96, 165, 250, 0.15)", border: "rgba(96, 165, 250, 0.3)" };
      case "BUILD":
        return { icon: "⚙️", color: "#f59e0b", bg: "rgba(245, 158, 11, 0.15)", border: "rgba(245, 158, 11, 0.3)" };
      case "TEST":
        return { icon: "🧪", color: "#10b981", bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.3)" };
      case "QA":
        return { icon: "🐞", color: "#ef4444", bg: "rgba(239, 68, 68, 0.15)", border: "rgba(239, 68, 68, 0.3)" };
      case "AI":
        return { icon: "🤖", color: "#ec4899", bg: "rgba(236, 72, 153, 0.15)", border: "rgba(236, 72, 153, 0.3)" };
      default:
        return { icon: "⏱️", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.15)", border: "rgba(148, 163, 184, 0.3)" };
    }
  };

  const formatShortTime = (isoString) => {
    if (!isoString) return "Recent";
    const d = new Date(isoString);
    return isNaN(d.getTime())
      ? "Recent"
      : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="card" style={{ width: "100%" }}>
      {/* Header with Source Filters */}
      <div className="card__header-row">
        <div>
          <h2>⚡ Unified Activity Timeline</h2>
          <p className="card__subtitle">Cross-system chronological engineering telemetry feed</p>
        </div>

        {/* Source Pills */}
        <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap" }}>
          {filterSources.map((src) => {
            const isActive = activeFilter === src;
            const cfg = getSourceConfig(src);
            return (
              <button
                key={src}
                type="button"
                onClick={() => onFilterChange && onFilterChange(src)}
                style={{
                  background: isActive ? (src === "ALL" ? "rgba(56, 189, 248, 0.2)" : cfg.bg) : "rgba(255, 255, 255, 0.04)",
                  border: isActive ? `1px solid ${src === "ALL" ? "#38bdf8" : cfg.color}` : "1px solid var(--border-subtle)",
                  color: isActive ? (src === "ALL" ? "#38bdf8" : cfg.color) : "var(--text-secondary)",
                  borderRadius: "6px",
                  padding: "0.2rem 0.6rem",
                  fontSize: "0.74rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {src}
              </button>
            );
          })}
        </div>
      </div>

      {/* Horizontal Scrollable Stream */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          overflowX: "auto",
          padding: "0.5rem 0.25rem 1rem",
          position: "relative",
        }}
      >
        {events.length === 0 ? (
          <div style={{ padding: "1.5rem", color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", width: "100%" }}>
            No recent activity recorded for filter: <strong>{activeFilter}</strong>
          </div>
        ) : (
          events.slice(0, 16).map((evt, idx) => {
            const srcCfg = getSourceConfig(evt.source);
            const timeStr = formatShortTime(evt.timestamp);
            const isSelected = selectedEvent === evt;

            return (
              <div
                key={idx}
                style={{
                  minWidth: "220px",
                  maxWidth: "240px",
                  background: isSelected ? "rgba(22, 32, 50, 0.95)" : "rgba(17, 24, 39, 0.8)",
                  border: `1px solid ${isSelected ? srcCfg.color : "var(--border-subtle)"}`,
                  borderRadius: "10px",
                  padding: "0.85rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.45rem",
                  flexShrink: 0,
                  cursor: "pointer",
                  position: "relative",
                  transition: "all 0.18s ease",
                  boxShadow: isSelected ? `0 0 16px ${srcCfg.bg}` : "none",
                }}
                onClick={() => setSelectedEvent(isSelected ? null : evt)}
              >
                {/* Top: Time & Source Badge */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 700 }}>
                    {timeStr}
                  </span>
                  <span
                    style={{
                      fontSize: "0.68rem",
                      fontWeight: 700,
                      color: srcCfg.color,
                      background: srcCfg.bg,
                      border: `1px solid ${srcCfg.border}`,
                      borderRadius: "4px",
                      padding: "0.15rem 0.45rem",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.25rem",
                    }}
                  >
                    <span>{srcCfg.icon}</span> {evt.source}
                  </span>
                </div>

                {/* Event Title */}
                <strong
                  style={{
                    fontSize: "0.84rem",
                    color: "#fff",
                    lineHeight: 1.3,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                  title={evt.title}
                >
                  {evt.title}
                </strong>

                {/* Short Punchy Summary */}
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    lineHeight: 1.3,
                  }}
                >
                  {evt.description || "Telemetry signal verified"}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Expanded Event Detail Drawer */}
      {selectedEvent && (
        <div
          style={{
            marginTop: "0.75rem",
            padding: "0.85rem 1rem",
            borderRadius: "8px",
            background: "rgba(7, 11, 20, 0.75)",
            border: "1px solid rgba(56, 189, 248, 0.3)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.75rem", color: "#38bdf8", fontWeight: 700 }}>
              INSPECTED EVENT: {selectedEvent.event_id || selectedEvent.title}
            </div>
            <div style={{ color: "#fff", fontSize: "0.86rem", marginTop: "2px" }}>
              {selectedEvent.description}
            </div>
          </div>
          <button
            type="button"
            className="btn-secondary"
            style={{ fontSize: "0.75rem", padding: "0.25rem 0.6rem" }}
            onClick={() => setSelectedEvent(null)}
          >
            Close ✕
          </button>
        </div>
      )}
    </div>
  );
}
