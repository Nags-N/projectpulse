import { useState } from "react";

export default function WorkDistributionDonut({ tasks = [], onSelectStatus }) {
  const [hoveredStatus, setHoveredStatus] = useState(null);

  const todo = tasks.filter((t) => t.status === "TODO" || t.status === "To Do").length;
  const inProgress = tasks.filter((t) => t.status === "IN_PROGRESS" || t.status === "In Progress").length;
  const done = tasks.filter((t) => t.status === "COMPLETED" || t.status === "Done").length;
  const blocked = tasks.filter((t) => t.status === "BLOCKED").length;
  const total = tasks.length || 0;

  const segments = [
    { key: "TODO", label: "To Do", count: todo, color: "#94a3b8" },
    { key: "IN_PROGRESS", label: "In Progress", count: inProgress, color: "#38bdf8" },
    { key: "COMPLETED", label: "Done", count: done, color: "#10b981" },
    { key: "BLOCKED", label: "Blocked", count: blocked, color: "#ef4444" },
  ].filter((s) => s.count > 0 || total === 0);

  // SVG parameters
  const radius = 60;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * radius; // ~377

  let accumulatedPct = 0;
  const renderedSegments = segments.map((seg) => {
    const pct = total > 0 ? seg.count / total : 0.25;
    const strokeDasharray = `${pct * circumference} ${circumference}`;
    const strokeDashoffset = -accumulatedPct * circumference;
    accumulatedPct += pct;
    return { ...seg, pct, strokeDasharray, strokeDashoffset };
  });

  const activeSegment = hoveredStatus
    ? segments.find((s) => s.key === hoveredStatus)
    : null;

  return (
    <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="card__header-row">
        <div>
          <h2>🍩 Work Distribution</h2>
          <p className="card__subtitle">Jira Cloud status segmentation</p>
        </div>
        <span className="badge badge--platform">{total} Tasks</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-around", flex: 1, gap: "1rem", flexWrap: "wrap" }}>
        {/* SVG Donut */}
        <div style={{ position: "relative", width: "160px", height: "160px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 160 160" style={{ width: "100%", height: "100%", transform: "rotate(-90deg)" }}>
            {/* Background Circle */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.05)"
              strokeWidth={strokeWidth}
            />
            {/* Segments */}
            {renderedSegments.map((seg) => (
              <circle
                key={seg.key}
                cx="80"
                cy="80"
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={hoveredStatus === seg.key ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={seg.strokeDasharray}
                strokeDashoffset={seg.strokeDashoffset}
                style={{
                  cursor: "pointer",
                  transition: "all 0.25s ease",
                  filter: hoveredStatus === seg.key ? `drop-shadow(0 0 8px ${seg.color})` : "none",
                }}
                onMouseEnter={() => setHoveredStatus(seg.key)}
                onMouseLeave={() => setHoveredStatus(null)}
                onClick={() => onSelectStatus && onSelectStatus(seg.key)}
              />
            ))}
          </svg>

          {/* Donut Center Display */}
          <div style={{ position: "absolute", textAlign: "center", pointerEvents: "none" }}>
            <div style={{ fontSize: "1.85rem", fontWeight: 800, color: "#fff", lineHeight: 1 }}>
              {activeSegment ? activeSegment.count : total}
            </div>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em", marginTop: "3px" }}>
              {activeSegment ? activeSegment.label.toUpperCase() : "TOTAL TASKS"}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {segments.map((seg) => (
            <div
              key={seg.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.65rem",
                padding: "0.35rem 0.65rem",
                borderRadius: "6px",
                background: hoveredStatus === seg.key ? "rgba(255, 255, 255, 0.05)" : "transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={() => setHoveredStatus(seg.key)}
              onMouseLeave={() => setHoveredStatus(null)}
              onClick={() => onSelectStatus && onSelectStatus(seg.key)}
            >
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: seg.color }} />
              <span style={{ fontSize: "0.82rem", color: "var(--text-secondary)", minWidth: "85px" }}>{seg.label}</span>
              <strong style={{ fontSize: "0.86rem", color: "#fff", fontFamily: "monospace" }}>{seg.count}</strong>
              <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                ({total > 0 ? Math.round((seg.count / total) * 100) : 0}%)
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
