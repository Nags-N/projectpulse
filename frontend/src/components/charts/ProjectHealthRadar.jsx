export default function ProjectHealthRadar({ data = {}, analytics = null }) {
  const { activity = {}, health = {}, tasks_summary = {}, active_risks = [] } = data;

  const totalTasks = tasks_summary.total || 0;
  const completedTasks = tasks_summary.completed || 0;
  const inProgressTasks = tasks_summary.in_progress || 0;
  const totalEvents = activity.total_activities || 0;
  const buildFailures = activity.build_failures || 0;
  const bugsReported = activity.bugs_reported || 0;

  // Verify sufficiency of telemetry
  const hasData = totalTasks > 0 || totalEvents > 0;

  if (!hasData) {
    return (
      <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: "260px" }}>
        <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📡</div>
        <div className="badge badge--warning" style={{ fontSize: "0.85rem", padding: "0.4rem 0.8rem" }}>
          DATA INSUFFICIENT
        </div>
        <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "0.5rem", textAlign: "center" }}>
          Awaiting engineering telemetry and Jira synchronization.
        </p>
      </div>
    );
  }

  // Calculate Real Grounded Scores
  // 1. Execution Score: Completed + half-credit for in-progress tasks
  const executionScore = totalTasks > 0
    ? Math.round(((completedTasks + 0.5 * inProgressTasks) / totalTasks) * 100)
    : 50;

  // 2. Delivery Velocity: Sprint velocity completion if available, else proportional
  const deliveryScore = analytics?.completion_rate_pct != null
    ? Math.min(100, Math.round(analytics.completion_rate_pct))
    : Math.min(100, Math.round((completedTasks / Math.max(totalTasks, 1)) * 100) + (inProgressTasks > 0 ? 30 : 0));

  // 3. Quality Gate: Penalized by build failures and open bugs
  const qualityPenalty = (buildFailures * 15) + (bugsReported * 20);
  const qualityScore = Math.max(10, Math.min(100, 100 - qualityPenalty));

  // 4. Risk Resilience: 100 minus active critical and high risks
  const criticalCount = active_risks.filter((r) => r.severity === "CRITICAL").length;
  const highCount = active_risks.filter((r) => r.severity === "HIGH").length;
  const riskScore = Math.max(15, Math.min(100, 100 - (criticalCount * 30 + highCount * 15)));

  // 5. Activity Cadence: Telemetry volume normalized against expected project pace
  const activityScore = Math.min(100, Math.max(20, Math.round((totalEvents / 25) * 100)));

  const metrics = [
    { label: "Execution", score: executionScore, color: "#38bdf8", icon: "⚡" },
    { label: "Delivery", score: deliveryScore, color: "#a855f7", icon: "🚀" },
    { label: "Quality", score: qualityScore, color: "#10b981", icon: "🛡️" },
    { label: "Resilience", score: riskScore, color: "#f59e0b", icon: "⚖️" },
    { label: "Activity", score: activityScore, color: "#ec4899", icon: "📡" },
  ];

  // Overall Composite Score
  const compositeScore = Math.round(
    metrics.reduce((acc, m) => acc + m.score, 0) / metrics.length
  );

  return (
    <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="card__header-row">
        <div>
          <h2>🎯 Project Health Observatory</h2>
          <p className="card__subtitle">Multi-axis real-time operational scorecard</p>
        </div>
        <span
          className={`status-pill ${
            compositeScore >= 75 ? "status-pill--active" : compositeScore >= 50 ? "status-pill--warn" : "status-pill--danger"
          }`}
        >
          {compositeScore >= 75 ? "● OPTIMAL" : compositeScore >= 50 ? "● ATTENTION" : "● CRITICAL"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", alignItems: "center", flex: 1 }}>
        {/* Radial Composite Meter */}
        <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 160 160" style={{ width: "140px", height: "140px" }}>
            {/* Background Track */}
            <circle
              cx="80"
              cy="80"
              r="62"
              fill="none"
              stroke="rgba(255, 255, 255, 0.06)"
              strokeWidth="12"
            />
            {/* Animated Glow Meter */}
            <circle
              cx="80"
              cy="80"
              r="62"
              fill="none"
              stroke={compositeScore >= 75 ? "#10b981" : compositeScore >= 50 ? "#38bdf8" : "#ef4444"}
              strokeWidth="12"
              strokeDasharray={`${(compositeScore / 100) * 389.5} 389.5`}
              strokeLinecap="round"
              transform="rotate(-90 80 80)"
              style={{ transition: "stroke-dasharray 1s ease" }}
            />
          </svg>
          <div style={{ position: "absolute", textAlign: "center" }}>
            <div style={{ fontSize: "2.2rem", fontWeight: 800, color: "#fff", lineHeight: 1 }}>
              {compositeScore}
            </div>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", color: "var(--text-muted)", marginTop: "2px" }}>
              HEALTH INDEX
            </div>
          </div>
        </div>

        {/* 5 Axis Grounded Metrics */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
          {metrics.map((m, idx) => (
            <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem" }}>
                <span style={{ color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "0.35rem" }}>
                  <span>{m.icon}</span> {m.label}
                </span>
                <strong style={{ color: "#fff", fontFamily: "monospace" }}>{m.score}%</strong>
              </div>
              <div style={{ width: "100%", height: "5px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "999px", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${m.score}%`,
                    height: "100%",
                    background: m.color,
                    borderRadius: "999px",
                    transition: "width 0.8s ease",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
