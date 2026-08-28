import { useCallback, useEffect, useState } from "react";
import { getManagerDashboard } from "../api/client";
import StatCard from "./StatCard";
import ActivityTimeline from "./ActivityTimeline";

export default function ManagerView({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!projectId) {
      return;
    }
    try {
      setError(null);
      const dashboard = await getManagerDashboard(projectId);
      setData(dashboard);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [load]);

  if (!projectId) {
    return <div className="loading">Loading configuration…</div>;
  }

  if (!data) {
    if (loading) {
      return <div className="loading">Loading project dashboard…</div>;
    }
    if (error) {
      return (
        <div className="error-panel">
          <p>Failed to load dashboard.</p>
          <pre>{error}</pre>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="error-panel">No dashboard data available.</div>;
  }

  const { activity } = data;

  return (
    <div className="view">
      <header className="view__header">
        <div>
          <p className="view__mode view__mode--manager">Project Manager Mode</p>
          <h1>{data.project_name}</h1>
          <p className="view__subtitle">Project intelligence dashboard</p>
        </div>
      </header>

      <section className="card">
        <h2>Project Activity</h2>
        <div className="stat-grid">
          <StatCard label="Total Activities" value={activity.total_activities} />
          <StatCard label="File Modifications" value={activity.file_modifications} />
          <StatCard label="Git Commits" value={activity.commits} />
          <StatCard label="Branch Changes" value={activity.branch_changes} />
          <StatCard
            label="Build Failures"
            value={activity.build_failures}
            accent={activity.build_failures > 0 ? "danger" : undefined}
          />
          <StatCard label="Build Successes" value={activity.build_successes} accent="success" />
        </div>
      </section>

      {data.signals.length > 0 && (
        <section className="card">
          <h2>Project Signals</h2>
          <ul className="signal-list">
            {data.signals.map((signal) => (
              <li
                key={signal}
                className={
                  signal.startsWith("⚠") ? "signal-list__warn" : "signal-list__ok"
                }
              >
                {signal}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="card">
        <h2>Project Narrative</h2>
        <p className="narrative">{data.narrative_summary}</p>
      </section>

      <section className="card">
        <div className="card__header-row">
          <h2>Recent Project Events</h2>
          <button type="button" className="btn-secondary" onClick={load}>
            Refresh
          </button>
        </div>
        <ActivityTimeline
          events={data.recent_events}
          emptyMessage="No project events recorded yet."
        />
      </section>
    </div>
  );
}
