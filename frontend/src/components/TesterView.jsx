import { useCallback, useEffect, useState } from "react";
import { getTestingMetrics } from "../api/client";
import StatCard from "./StatCard";
import ActivityTimeline from "./ActivityTimeline";

export default function TesterView({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setError(null);
      const metrics = await getTestingMetrics(projectId);
      setData(metrics);
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
      return <div className="loading">Loading testing metrics…</div>;
    }
    if (error) {
      return (
        <div className="error-panel">
          <p>Failed to load testing metrics.</p>
          <pre>{error}</pre>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="error-panel">No testing data available.</div>;
  }

  return (
    <div className="view">
      <header className="view__header">
        <div>
          <p className="view__mode view__mode--tester">Tester & Automation Mode</p>
          <h1>{data.project_name}</h1>
          <p className="view__subtitle">Test suite runs, pass/fail counts, and regression metrics</p>
        </div>
        <button type="button" className="btn-secondary" onClick={load}>
          Refresh Tests
        </button>
      </header>

      <section className="card">
        <h2>Testing Metrics & Pass Rates</h2>
        <div className="stat-grid">
          <StatCard label="Total Test Runs" value={data.total_test_runs} />
          <StatCard label="Total Tests Executed" value={data.total_tests} />
          <StatCard label="Passed Tests" value={data.passed} accent="success" />
          <StatCard
            label="Failed Tests"
            value={data.failed}
            accent={data.failed > 0 ? "danger" : undefined}
          />
          <StatCard label="Skipped Tests" value={data.skipped} />
          <StatCard
            label="Pass Rate"
            value={`${data.pass_rate}%`}
            accent={data.pass_rate >= 90 ? "success" : data.pass_rate >= 70 ? "warning" : "danger"}
          />
        </div>
      </section>

      <section className="card">
        <div className="card__header-row">
          <h2>Recent Test Executions</h2>
        </div>
        <ActivityTimeline
          events={data.recent_events}
          emptyMessage="No test execution events recorded yet."
        />
      </section>
    </div>
  );
}
