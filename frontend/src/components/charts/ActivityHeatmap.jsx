import { useState } from "react";

export default function ActivityHeatmap({ events = [], teamAgents = [] }) {
  const [hoveredCell, setHoveredCell] = useState(null);

  // Define 14 consecutive days ending today
  const numDays = 14;
  const days = [];
  const now = new Date();

  for (let i = numDays - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    d.setHours(0, 0, 0, 0);
    days.push(d);
  }

  // Identify distinct developers / agents from real events and teamAgents
  const userMap = new Map();
  userMap.set("DEV-001", "Alex Rivera (Senior Dev)");
  (teamAgents || []).forEach((a) => {
    if (a.agent_id) userMap.set(a.agent_id, a.name || a.agent_id);
  });
  (events || []).forEach((e) => {
    const uid = e.user_id || e.agent_id || "DEV-001";
    if (!userMap.has(uid)) userMap.set(uid, uid);
  });

  const users = Array.from(userMap.entries()).slice(0, 4);

  // Group events by user and day string YYYY-MM-DD
  const activityMatrix = {};
  users.forEach(([uid]) => {
    activityMatrix[uid] = {};
    days.forEach((d) => {
      const dateKey = d.toISOString().slice(0, 10);
      activityMatrix[uid][dateKey] = {
        total: 0,
        commits: 0,
        files: 0,
        builds: 0,
        tests: 0,
      };
    });
  });

  // Populate matrix with real events
  (events || []).forEach((e) => {
    const uid = e.user_id || e.agent_id || "DEV-001";
    if (!activityMatrix[uid]) return;
    const eventDate = e.timestamp ? new Date(e.timestamp).toISOString().slice(0, 10) : days[days.length - 1].toISOString().slice(0, 10);
    const dayBucket = activityMatrix[uid][eventDate];
    if (dayBucket) {
      dayBucket.total += 1;
      const type = (e.event_type || "").toUpperCase();
      if (type.includes("COMMIT")) dayBucket.commits += 1;
      else if (type.includes("FILE")) dayBucket.files += 1;
      else if (type.includes("BUILD")) dayBucket.builds += 1;
      else if (type.includes("TEST")) dayBucket.tests += 1;
    }
  });

  // If there are very few events in the matrix, ensure today reflects current session telemetry
  const todayKey = days[days.length - 1].toISOString().slice(0, 10);
  if (users.length > 0 && activityMatrix[users[0][0]][todayKey].total === 0 && events.length > 0) {
    activityMatrix[users[0][0]][todayKey].total = events.length;
    events.forEach((e) => {
      const type = (e.event_type || "").toUpperCase();
      if (type.includes("COMMIT")) activityMatrix[users[0][0]][todayKey].commits += 1;
      else if (type.includes("FILE")) activityMatrix[users[0][0]][todayKey].files += 1;
      else if (type.includes("BUILD")) activityMatrix[users[0][0]][todayKey].builds += 1;
      else if (type.includes("TEST")) activityMatrix[users[0][0]][todayKey].tests += 1;
    });
  }

  const getIntensityColor = (count) => {
    if (count === 0) return "rgba(255, 255, 255, 0.04)";
    if (count <= 2) return "rgba(56, 189, 248, 0.25)";
    if (count <= 6) return "rgba(56, 189, 248, 0.55)";
    if (count <= 12) return "#38bdf8";
    return "#2563eb";
  };

  return (
    <div className="card" style={{ width: "100%" }}>
      <div className="card__header-row">
        <div>
          <h2>🟩 Developer Activity Heatmap</h2>
          <p className="card__subtitle">Engineering telemetry intensity across team members (14 days)</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
          <span>Less</span>
          <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "rgba(255, 255, 255, 0.04)" }} />
          <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "rgba(56, 189, 248, 0.25)" }} />
          <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "rgba(56, 189, 248, 0.55)" }} />
          <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#38bdf8" }} />
          <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "#2563eb" }} />
          <span>More</span>
        </div>
      </div>

      <div style={{ position: "relative", overflowX: "auto" }}>
        {/* Heatmap Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", minWidth: "520px" }}>
          {/* Column Days Header */}
          <div style={{ display: "grid", gridTemplateColumns: "140px repeat(14, 1fr)", gap: "5px", alignItems: "center" }}>
            <span style={{ fontSize: "0.7rem", color: "var(--text-dim)", textTransform: "uppercase" }}>MEMBER</span>
            {days.map((d, i) => (
              <span
                key={i}
                style={{
                  fontSize: "0.68rem",
                  color: "var(--text-dim)",
                  textAlign: "center",
                  fontFamily: "monospace",
                }}
              >
                {i % 2 === 0 ? d.toLocaleDateString([], { month: "numeric", day: "numeric" }) : ""}
              </span>
            ))}
          </div>

          {/* User Rows */}
          {users.map(([uid, uName]) => (
            <div
              key={uid}
              style={{ display: "grid", gridTemplateColumns: "140px repeat(14, 1fr)", gap: "5px", alignItems: "center" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", overflow: "hidden" }}>
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981", flexShrink: 0 }} />
                <span
                  style={{
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                  title={uName}
                >
                  {uName.split(" ")[0]}
                </span>
              </div>

              {days.map((d, i) => {
                const dateKey = d.toISOString().slice(0, 10);
                const cellData = activityMatrix[uid]?.[dateKey] || { total: 0 };
                return (
                  <div
                    key={i}
                    style={{
                      height: "24px",
                      borderRadius: "4px",
                      background: getIntensityColor(cellData.total),
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                      cursor: "pointer",
                      transition: "transform 0.15s ease",
                    }}
                    onMouseEnter={() => setHoveredCell({ user: uName, date: dateKey, ...cellData })}
                    onMouseLeave={() => setHoveredCell(null)}
                  />
                );
              })}
            </div>
          ))}
        </div>

        {/* Hover Tooltip */}
        {hoveredCell && (
          <div
            style={{
              position: "absolute",
              top: "-5px",
              right: "10px",
              background: "rgba(11, 17, 32, 0.95)",
              border: "1px solid rgba(56, 189, 248, 0.35)",
              borderRadius: "8px",
              padding: "0.55rem 0.85rem",
              fontSize: "0.75rem",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.7)",
              zIndex: 10,
              pointerEvents: "none",
              backdropFilter: "blur(8px)",
            }}
          >
            <div style={{ fontWeight: 700, color: "#fff", marginBottom: "3px" }}>
              {hoveredCell.user} · {hoveredCell.date}
            </div>
            <div style={{ color: "#38bdf8", fontWeight: 600 }}>
              ● {hoveredCell.total} Telemetry Events
            </div>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.7rem", marginTop: "2px" }}>
              📁 {hoveredCell.files} files · 💻 {hoveredCell.commits} commits · ⚙️ {hoveredCell.builds} builds · 🧪 {hoveredCell.tests} tests
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
