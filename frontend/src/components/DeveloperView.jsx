import { useCallback, useEffect, useState } from "react";
import { getDeveloperSummary } from "../api/client";
import StatCard from "./StatCard";
import ActivityTimeline from "./ActivityTimeline";

export default function DeveloperView({ projectId, userId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!projectId || !userId) {
      return;
    }
    try {
      setError(null);
      const summary = await getDeveloperSummary(projectId, userId);
      setData(summary);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId, userId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [load]);

  if (!projectId || !userId) {
    return <div className="loading">Loading configuration…</div>;
  }

  if (!data) {
    if (loading) {
      return <div className="loading">Loading developer summary…</div>;
    }
    if (error) {
      return (
        <div className="error-panel">
          <p>Failed to load summary.</p>
          <pre>{error}</pre>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="error-panel">No summary data available.</div>;
  }

  const { activity } = data;
  const whatYouDid = data.what_you_did?.length ? data.what_you_did : data.highlights || [];

  return (
    <div className="view">
      <header className="view__header">
        <div>
          <p className="view__mode">Developer Summary</p>
          <h1>{data.project_name}</h1>
          <p className="view__subtitle">Today</p>
        </div>
        <div className="status-pill-row">
          <span
            className={`status-pill ${
              data.monitoring_active ? "status-pill--active" : "status-pill--paused"
            }`}
          >
            Monitoring: {data.monitoring_active ? "ACTIVE" : "PAUSED"}
          </span>
          <span className="status-pill status-pill--info">{data.current_status}</span>
        </div>
      </header>

      <section className="card">
        <h2>Today&apos;s Activity</h2>
        <div className="stat-grid">
          <StatCard label="Files Modified" value={activity.file_modifications} />
          <StatCard label="Files Created" value={activity.files_created} />
          <StatCard label="Git Commits" value={activity.commits} />
          <StatCard label="Branch Changes" value={activity.branch_changes} />
        </div>
      </section>

      <section className="card">
        <h2>What You Did</h2>
        {whatYouDid.length > 0 ? (
          <ul className="highlight-list">
            {whatYouDid.map((item, index) => (
              <li key={`${item}-${index}`}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">No summary yet for today.</p>
        )}
      </section>

      <section className="card">
        <div className="card__header-row">
          <h2>Recent Activity</h2>
          <button type="button" className="btn-secondary" onClick={load}>
            Refresh
          </button>
        </div>
        <ActivityTimeline
          events={data.recent_events}
          emptyMessage="No activity recorded today. Edit files in your monitored project folder."
        />
      </section>

      <section className="card">
        <h2>Current Status</h2>
        <p className="narrative">{data.current_status}</p>
        <p className="narrative" style={{ marginTop: "0.5rem" }}>
          Monitoring: {data.monitoring_active ? "ACTIVE" : "PAUSED"}
        </p>
      </section>
    </div>
  );
}
