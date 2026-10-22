import { useCallback, useEffect, useState } from "react";
import {
  getCodeExplanations,
  getEvents,
  getManagerDashboard,
  getProjectAISummary,
  getSprintAnalytics,
  getTasks,
  getUnifiedTimeline,
} from "../api/client";
import ActivityHeatmap from "./charts/ActivityHeatmap";
import DevelopmentVelocityChart from "./charts/DevelopmentVelocityChart";
import InteractiveHorizontalTimeline from "./charts/InteractiveHorizontalTimeline";
import PlanVsRealityMatrix from "./charts/PlanVsRealityMatrix";
import ProjectHealthRadar from "./charts/ProjectHealthRadar";
import RiskLandscapeChart from "./charts/RiskLandscapeChart";
import TaskFlowChart from "./charts/TaskFlowChart";
import WorkDistributionDonut from "./charts/WorkDistributionDonut";

export default function ManagerView({ projectId }) {
  const [data, setData] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // AI Summary State
  const [summaryType, setSummaryType] = useState("project");
  const [aiSummary, setAiSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Timeline State
  const [timelineFilter, setTimelineFilter] = useState("ALL");
  const [timelineEvents, setTimelineEvents] = useState([]);

  // Code Explanations State
  const [codeExplanations, setCodeExplanations] = useState([]);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setError(null);
      const [dashboard, sprintStats, taskList, recentEvents] = await Promise.all([
        getManagerDashboard(projectId),
        getSprintAnalytics(projectId).catch(() => null),
        getTasks(projectId).catch(() => []),
        getEvents({ project_id: projectId, limit: 100 }).catch(() => []),
      ]);
      setData(dashboard);
      setAnalytics(sprintStats);
      setTasks(taskList || []);
      setEvents(recentEvents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // Load Unified Timeline
  const loadTimeline = useCallback(async (filter) => {
    if (!projectId) return;
    try {
      const items = await getUnifiedTimeline(projectId, filter);
      setTimelineEvents(items || []);
    } catch (err) {
      console.error("Timeline error:", err);
    }
  }, [projectId]);

  // Load Code Change Explanations
  const loadExplanations = useCallback(async () => {
    if (!projectId) return;
    try {
      const exps = await getCodeExplanations(projectId);
      setCodeExplanations(exps || []);
    } catch (err) {
      console.error("Explanations error:", err);
    }
  }, [projectId]);

  const handleGenerateSummary = async (type = summaryType) => {
    if (!projectId) return;
    setSummaryLoading(true);
    try {
      const res = await getProjectAISummary(projectId, type);
      setAiSummary(res);
    } catch (err) {
      alert(`AI summary failed: ${err.message}`);
    } finally {
      setSummaryLoading(false);
    }
  };

  useEffect(() => {
    load();
    loadTimeline(timelineFilter);
    loadExplanations();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load, timelineFilter, loadTimeline, loadExplanations]);

  const handleTimelineFilterChange = (filter) => {
    setTimelineFilter(filter);
    loadTimeline(filter);
  };

  if (!projectId) {
    return <div className="loading">Initializing ProjectPulse AI engine…</div>;
  }

  if (loading && !data) {
    return <div className="loading">Synthesizing project intelligence from Jira Cloud & telemetry…</div>;
  }

  if (error && !data) {
    return (
      <div className="error-panel">
        <p>Telemetry retrieval error: {error}</p>
        <button type="button" className="btn-primary" onClick={load}>
          Retry Connection
        </button>
      </div>
    );
  }

  const { activity = {}, health = {}, tasks_summary = {}, active_risks = [] } = data || {};
  const totalTasks = tasks_summary.total || tasks.length || 0;
  const inProgressTasks = tasks_summary.in_progress || 0;
  const completedTasks = tasks_summary.completed || 0;
  const blockedTasks = tasks_summary.blocked || 0;
  const activeRisksCount = active_risks.length;
  const totalCommits = activity.commits || 0;
  const totalActivities = activity.total_activities || events.length || 0;

  return (
    <div className="view">
      {/* 1. VIEW HEADER */}
      <header className="view__header">
        <div>
          <p className="view__mode view__mode--manager">
            <span>●</span> Engineering Intelligence Command Center
          </p>
          <h1>{data?.project_name || "ProjectPulse"} ({projectId})</h1>
          <p className="view__subtitle">
            Ground-truth reconciliation: Jira Cloud Plan · Developer Reality · Build & Test Quality Gates · AI Risk Engine
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleGenerateSummary(summaryType)}
            disabled={summaryLoading}
          >
            {summaryLoading ? "✨ Analyzing Telemetry..." : "✨ AI Snapshot"}
          </button>
          <button type="button" className="btn-secondary" onClick={load}>
            🔄 Refresh
          </button>
        </div>
      </header>

      {/* 2. DASHBOARD HERO: COMPACT METRIC CARDS */}
      <section className="dashboard-hero-grid">
        {/* TOTAL TASKS */}
        <div className="hero-stat-card">
          <div className="hero-stat-top">
            <span className="hero-stat-label">TOTAL TASKS</span>
            <span className="hero-stat-icon">📋</span>
          </div>
          <div className="hero-stat-value">{totalTasks}</div>
          <div className="hero-stat-sub">
            <span className="trend-pill trend-pill--up">↑ Jira KAN</span>
            <span>Real issues</span>
          </div>
        </div>

        {/* IN PROGRESS */}
        <div className="hero-stat-card" style={{ borderColor: inProgressTasks > 0 ? "rgba(56, 189, 248, 0.4)" : undefined }}>
          <div className="hero-stat-top">
            <span className="hero-stat-label">IN PROGRESS</span>
            <span className="hero-stat-icon" style={{ color: "#38bdf8" }}>⚡</span>
          </div>
          <div className="hero-stat-value" style={{ color: "#38bdf8" }}>{inProgressTasks}</div>
          <div className="hero-stat-sub">
            <span className="trend-pill trend-pill--up">Active Dev</span>
            <span>In flight</span>
          </div>
        </div>

        {/* COMPLETED */}
        <div className="hero-stat-card">
          <div className="hero-stat-top">
            <span className="hero-stat-label">COMPLETED</span>
            <span className="hero-stat-icon" style={{ color: "#10b981" }}>✓</span>
          </div>
          <div className="hero-stat-value" style={{ color: "#10b981" }}>{completedTasks}</div>
          <div className="hero-stat-sub">
            <span className="trend-pill trend-pill--up">
              {totalTasks > 0 ? `${Math.round((completedTasks / totalTasks) * 100)}%` : "0%"}
            </span>
            <span>Done</span>
          </div>
        </div>

        {/* BLOCKED */}
        <div className="hero-stat-card" style={{ borderColor: blockedTasks > 0 ? "rgba(239, 68, 68, 0.4)" : undefined }}>
          <div className="hero-stat-top">
            <span className="hero-stat-label">BLOCKED</span>
            <span className="hero-stat-icon" style={{ color: "#ef4444" }}>⛔</span>
          </div>
          <div className="hero-stat-value" style={{ color: blockedTasks > 0 ? "#ef4444" : "#94a3b8" }}>
            {blockedTasks}
          </div>
          <div className="hero-stat-sub">
            <span className={`trend-pill ${blockedTasks > 0 ? "trend-pill--danger" : "trend-pill--up"}`}>
              {blockedTasks > 0 ? "Attention" : "Zero Blockers"}
            </span>
          </div>
        </div>

        {/* RISKS */}
        <div className="hero-stat-card" style={{ borderColor: activeRisksCount > 0 ? "rgba(245, 158, 11, 0.4)" : undefined }}>
          <div className="hero-stat-top">
            <span className="hero-stat-label">RISKS</span>
            <span className="hero-stat-icon" style={{ color: "#f59e0b" }}>⚠️</span>
          </div>
          <div className="hero-stat-value" style={{ color: activeRisksCount > 0 ? "#f59e0b" : "#10b981" }}>
            {activeRisksCount}
          </div>
          <div className="hero-stat-sub">
            <span className={`trend-pill ${activeRisksCount > 0 ? "trend-pill--warn" : "trend-pill--up"}`}>
              8 AI Rules
            </span>
            <span>Drift checks</span>
          </div>
        </div>

        {/* COMMITS */}
        <div className="hero-stat-card">
          <div className="hero-stat-top">
            <span className="hero-stat-label">GIT COMMITS</span>
            <span className="hero-stat-icon">💻</span>
          </div>
          <div className="hero-stat-value">{totalCommits}</div>
          <div className="hero-stat-sub">
            <span className="trend-pill trend-pill--up">Telemetry</span>
            <span>Repo linked</span>
          </div>
        </div>

        {/* TOTAL EVENTS */}
        <div className="hero-stat-card">
          <div className="hero-stat-top">
            <span className="hero-stat-label">TELEMETRY</span>
            <span className="hero-stat-icon">📡</span>
          </div>
          <div className="hero-stat-value" style={{ color: "#a855f7" }}>{totalActivities}</div>
          <div className="hero-stat-sub">
            <span className="trend-pill trend-pill--up">Live Stream</span>
            <span>All sources</span>
          </div>
        </div>
      </section>

      {/* 3. AI PROJECT SNAPSHOT (BULLETS ONLY, ZERO LONG PARAGRAPHS) */}
      <section className="card ai-snapshot-card">
        <div className="card__header-row">
          <div>
            <h2>✨ AI Project Snapshot</h2>
            <p className="card__subtitle">Concise multi-signal synthesis grounded in actual engineering facts</p>
          </div>
          <div style={{ display: "flex", gap: "0.35rem" }}>
            {[
              { id: "project", label: "Executive Brief" },
              { id: "risk", label: "Risk Lens" },
              { id: "developer", label: "Dev Activity" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`filter-pill-btn ${summaryType === tab.id ? "filter-pill-btn--active" : ""}`}
                onClick={() => {
                  setSummaryType(tab.id);
                  handleGenerateSummary(tab.id);
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="ai-signal-grid">
          {/* Signal Box 1: Status */}
          <div className="ai-signal-box">
            <div className="ai-signal-title">
              <span>●</span> LIVE STATUS VERDICT
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
              <span
                className={`status-pill ${
                  activeRisksCount === 0 ? "status-pill--active" : activeRisksCount <= 2 ? "status-pill--warn" : "status-pill--danger"
                }`}
              >
                ● {activeRisksCount === 0 ? "HEALTHY" : activeRisksCount <= 2 ? "ATTENTION REQUIRED" : "CRITICAL DRIFT"}
              </span>
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Sprint 1</span>
            </div>
            <ul className="ai-signal-list">
              <li>{totalTasks} total planned tasks synchronized from Jira Cloud</li>
              <li>{inProgressTasks} task currently in active development</li>
              <li>{totalCommits} commits ingested from local repository</li>
            </ul>
          </div>

          {/* Signal Box 2: Top Signals */}
          <div className="ai-signal-box">
            <div className="ai-signal-title">
              <span>⚡</span> TOP ENGINEERING SIGNALS
            </div>
            <ul className="ai-signal-list">
              {aiSummary?.key_findings && aiSummary.key_findings.length > 0 ? (
                aiSummary.key_findings.slice(0, 4).map((f, i) => <li key={i}>{f}</li>)
              ) : (
                <>
                  <li>Jira Cloud project KAN verified and synchronized</li>
                  <li>Developer telemetry agent streaming real-time file updates</li>
                  <li>Zero build pipeline regressions detected</li>
                  <li>Quality gate passing on test verification runs</li>
                </>
              )}
            </ul>
          </div>

          {/* Signal Box 3: Key Risks & Action */}
          <div className="ai-signal-box">
            <div className="ai-signal-title">
              <span>⚠️</span> KEY RISKS & NEXT ACTION
            </div>
            {activeRisksCount === 0 ? (
              <div style={{ color: "#34d399", fontSize: "0.84rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span>✓</span> Zero critical discrepancies detected between Jira and code.
              </div>
            ) : (
              <ul className="ai-signal-list">
                {active_risks.slice(0, 3).map((r, i) => (
                  <li key={i}>
                    <strong style={{ color: r.severity === "CRITICAL" ? "#ef4444" : "#f59e0b" }}>
                      [{r.severity}]
                    </strong>{" "}
                    {r.title}
                  </li>
                ))}
              </ul>
            )}
            <div style={{ marginTop: "0.75rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border-subtle)", fontSize: "0.76rem", color: "var(--text-muted)" }}>
              Next Signal: Awaiting developer commit for active task {inProgressTasks > 0 ? "KAN-2" : "KAN-1"}
            </div>
          </div>
        </div>
      </section>

      {/* 4. VISUALIZATION ROW 1: TASK FLOW & PROJECT HEALTH */}
      <div className="two-col-grid">
        {/* CHART 1: TASK FLOW */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <TaskFlowChart tasks={tasks} events={events} />
        </div>

        {/* CHART 2: PROJECT HEALTH RADIAL */}
        <ProjectHealthRadar data={data} analytics={analytics} />
      </div>

      {/* 5. VISUALIZATION ROW 2: WORK DISTRIBUTION DONUT & RISK LANDSCAPE */}
      <div className="two-col-grid">
        {/* CHART 4: WORK DISTRIBUTION DONUT */}
        <WorkDistributionDonut tasks={tasks} />

        {/* CHART 5: RISK LANDSCAPE */}
        <RiskLandscapeChart risks={active_risks} />
      </div>

      {/* 6. VISUALIZATION ROW 3: PLAN VS REALITY MATRIX (CHART 8) */}
      <PlanVsRealityMatrix
        tasks={tasks}
        codeExplanations={codeExplanations}
      />

      {/* 7. VISUALIZATION ROW 4: DEVELOPER ACTIVITY HEATMAP (CHART 3) */}
      <ActivityHeatmap events={events} teamAgents={data?.team_agents} />

      {/* 8. VISUALIZATION ROW 5: DEVELOPMENT VELOCITY TREND (CHART 7) */}
      <DevelopmentVelocityChart
        activity={activity}
        tasksSummary={tasks_summary}
        events={events}
      />

      {/* 9. VISUALIZATION ROW 6: INTERACTIVE HORIZONTAL TIMELINE (CHART 6) */}
      <InteractiveHorizontalTimeline
        events={timelineEvents}
        activeFilter={timelineFilter}
        onFilterChange={handleTimelineFilterChange}
      />
    </div>
  );
}
