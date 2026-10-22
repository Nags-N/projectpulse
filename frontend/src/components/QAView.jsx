import { useCallback, useEffect, useState } from "react";
import { getQAMetrics, recordQAVerdict, reportDefect, updateDefectStatus } from "../api/client";
import StatCard from "./StatCard";
import ActivityTimeline from "./ActivityTimeline";

export default function QAView({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Defect form state
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("HIGH");
  const [priority, setPriority] = useState("HIGH");
  const [relatedTask, setRelatedTask] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      setError(null);
      const metrics = await getQAMetrics(projectId);
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

  const handleReportDefect = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await reportDefect(projectId, {
        title,
        description,
        severity,
        priority,
        related_task_id: relatedTask,
        reported_by: "QA Lead",
      });
      setTitle("");
      setDescription("");
      setRelatedTask("");
      setShowForm(false);
      await load();
    } catch (err) {
      alert(`Error reporting defect: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (defectId, newStatus) => {
    try {
      await updateDefectStatus(defectId, newStatus);
      await load();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  const handleVerdict = async (approved) => {
    const reason = prompt(
      approved ? "Optional acceptance notes:" : "Reason for build rejection:"
    );
    if (reason === null) return;
    try {
      await recordQAVerdict(projectId, {
        approved,
        build_ref: "Release-Candidate v1.0",
        notes: reason,
      });
      await load();
    } catch (err) {
      alert(`Verdict failed: ${err.message}`);
    }
  };

  if (!projectId) {
    return <div className="loading">Loading configuration…</div>;
  }

  if (!data) {
    if (loading) return <div className="loading">Loading QA data…</div>;
    if (error) {
      return (
        <div className="error-panel">
          <p>Failed to load QA data: {error}</p>
          <button type="button" onClick={load}>
            Retry
          </button>
        </div>
      );
    }
    return <div className="error-panel">No QA data available.</div>;
  }

  return (
    <div className="view">
      <header className="view__header">
        <div>
          <p className="view__mode view__mode--qa">Quality Assurance & Validation Mode</p>
          <h1>{data.project_name}</h1>
          <p className="view__subtitle">Defect lifecycle, regression tracking, and release acceptance</p>
        </div>
        <div className="action-button-group">
          <button
            type="button"
            className="btn-primary"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? "Cancel Defect" : "+ Report Defect"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleVerdict(true)}
          >
            ✓ Approve Build
          </button>
          <button
            type="button"
            className="btn-danger-outline"
            onClick={() => handleVerdict(false)}
          >
            ✕ Reject Build
          </button>
        </div>
      </header>

      {/* Defect Entry Form */}
      {showForm && (
        <section className="card card--form">
          <h2>Report New Defect</h2>
          <form onSubmit={handleReportDefect}>
            <div className="form-group">
              <label>Defect Summary / Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Duplicate charge on double clicking checkout button"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Severity</label>
                <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="URGENT">URGENT</option>
                  <option value="HIGH">HIGH</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="LOW">LOW</option>
                </select>
              </div>

              <div className="form-group">
                <label>Related Task Key</label>
                <input
                  type="text"
                  value={relatedTask}
                  onChange={(e) => setRelatedTask(e.target.value)}
                  placeholder="e.g. PROJ-101"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Detailed Steps to Reproduce & Expected Behavior</label>
              <textarea
                rows="3"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="1. Click 'Pay Now' repeatedly. 2. Observe multiple charges triggered on webhook."
              />
            </div>

            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Submitting..." : "Log Defect"}
            </button>
          </form>
        </section>
      )}

      {/* QA Stat Cards */}
      <section className="card">
        <h2>Quality Metrics & Defect Status</h2>
        <div className="stat-grid">
          <StatCard
            label="Open Defects"
            value={data.open_defects}
            accent={data.open_defects > 0 ? "warning" : "success"}
          />
          <StatCard
            label="High / Critical"
            value={data.high_severity_defects}
            accent={data.high_severity_defects > 0 ? "danger" : undefined}
          />
          <StatCard label="Verified Defects" value={data.verified_defects} />
          <StatCard label="Closed Defects" value={data.closed_defects} accent="success" />
          <StatCard
            label="Build Verdict"
            value={data.latest_verdict}
            accent={
              data.latest_verdict === "APPROVED"
                ? "success"
                : data.latest_verdict === "REJECTED"
                ? "danger"
                : undefined
            }
          />
        </div>
      </section>

      {/* Defects List */}
      <section className="card">
        <h2>Active Defects ({data.defects.length})</h2>
        {data.defects.length === 0 ? (
          <p className="empty-state">No defects logged for this project.</p>
        ) : (
          <div className="table-responsive">
            <table className="agents-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Title & Description</th>
                  <th>Severity</th>
                  <th>Priority</th>
                  <th>Related Task</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.defects.map((def) => (
                  <tr key={def.defect_id}>
                    <td>
                      <code>{def.defect_id}</code>
                    </td>
                    <td>
                      <strong>{def.title}</strong>
                      {def.description && (
                        <p className="text-muted text-sm">{def.description}</p>
                      )}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          def.severity === "CRITICAL" || def.severity === "HIGH"
                            ? "badge--danger"
                            : "badge--warning"
                        }`}
                      >
                        {def.severity}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge--priority">{def.priority}</span>
                    </td>
                    <td>
                      {def.related_task_id ? <code>{def.related_task_id}</code> : "None"}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          def.status === "CLOSED"
                            ? "badge--success"
                            : def.status === "VERIFIED"
                            ? "badge--primary"
                            : "badge--warning"
                        }`}
                      >
                        {def.status}
                      </span>
                    </td>
                    <td>
                      {def.status !== "VERIFIED" && def.status !== "CLOSED" && (
                        <button
                          type="button"
                          className="btn-tiny"
                          onClick={() => handleStatusChange(def.defect_id, "VERIFIED")}
                        >
                          Verify
                        </button>
                      )}
                      {def.status !== "CLOSED" && (
                        <button
                          type="button"
                          className="btn-tiny btn-tiny--success"
                          onClick={() => handleStatusChange(def.defect_id, "CLOSED")}
                        >
                          Close
                        </button>
                      )}
                      {def.status === "CLOSED" && (
                        <button
                          type="button"
                          className="btn-tiny btn-tiny--warn"
                          onClick={() => handleStatusChange(def.defect_id, "REOPENED")}
                        >
                          Reopen
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* QA Activity Timeline */}
      <section className="card">
        <h2>QA Event Timeline</h2>
        <ActivityTimeline
          events={data.recent_events}
          emptyMessage="No QA activity recorded yet."
        />
      </section>
    </div>
  );
}
