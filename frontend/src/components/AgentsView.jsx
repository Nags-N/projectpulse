import { useCallback, useEffect, useState } from "react";
import { getAgents } from "../api/client";

export default function AgentsView({ projectId }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await getAgents(projectId);
      setAgents(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const getRoleBadgeClass = (role) => {
    switch (role) {
      case "DEVELOPER":
        return "badge--developer";
      case "TESTER":
        return "badge--tester";
      case "QA":
        return "badge--qa";
      default:
        return "badge--default";
    }
  };

  return (
    <div className="view">
      <header className="view__header">
        <div>
          <p className="view__mode">Distributed Multi-Device Deployment</p>
          <h1>Connected Agents</h1>
          <p className="view__subtitle">Live monitoring status across team members' machines</p>
        </div>
        <button type="button" className="btn-secondary" onClick={load}>
          Refresh Agents
        </button>
      </header>

      {error && (
        <div className="error-panel">
          <p>Failed to load agents: {error}</p>
        </div>
      )}

      {loading && agents.length === 0 ? (
        <div className="loading">Checking for registered agents…</div>
      ) : (
        <div className="card">
          <div className="table-responsive">
            <table className="agents-table">
              <thead>
                <tr>
                  <th>Agent ID</th>
                  <th>Role</th>
                  <th>Machine Name</th>
                  <th>User ID</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td>
                      <code>{agent.agent_id}</code>
                    </td>
                    <td>
                      <span className={`badge ${getRoleBadgeClass(agent.role)}`}>
                        {agent.role}
                      </span>
                    </td>
                    <td>{agent.machine_name}</td>
                    <td>{agent.user_id}</td>
                    <td>
                      <span
                        className={`status-indicator ${
                          agent.status === "ONLINE"
                            ? "status-indicator--online"
                            : "status-indicator--offline"
                        }`}
                      >
                        ● {agent.status}
                      </span>
                    </td>
                    <td className="text-muted">
                      {agent.last_seen ? new Date(agent.last_seen).toLocaleTimeString() : "Never"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Feature 16: ProjectPulse Privacy Center (Section 24) */}
      <section className="card" style={{ marginTop: "1.5rem" }}>
        <div className="card__header-row">
          <div>
            <h2>ProjectPulse Privacy Center</h2>
            <p className="card__subtitle">
              Strict privacy boundaries enforced by local client-side allowlist filters
            </p>
          </div>
          <span className="badge badge--success">✓ Privacy Preserving</span>
        </div>

        <div className="two-col-grid" style={{ marginTop: "1rem" }}>
          <div className="privacy-column privacy-column--collected">
            <h4 style={{ color: "#16a34a", marginBottom: "0.5rem" }}>
              ✓ Collected Telemetry (Project-Scoped Only)
            </h4>
            <ul className="privacy-list">
              <li><strong>Project File Modifications</strong> — Debounced file paths within approved directory.</li>
              <li><strong>Git Activity</strong> — Commit messages, active branches, checkout events without diffs.</li>
              <li><strong>Build System Activity</strong> — Exit codes and duration for approved build commands.</li>
              <li><strong>Automated Test Results</strong> — Pass/fail counts from Pytest and Jest runners.</li>
              <li><strong>QA Defect Events</strong> — Bug reports, severity levels, and build verdicts.</li>
            </ul>
          </div>

          <div className="privacy-column privacy-column--blocked">
            <h4 style={{ color: "#dc2626", marginBottom: "0.5rem" }}>
              ✗ Strictly Blocked / Never Collected
            </h4>
            <ul className="privacy-list">
              <li><strong>Keystrokes & Keylogging</strong> — Zero keyboard monitors or OS hooks.</li>
              <li><strong>Passwords & Secrets</strong> — Regex scrubs API keys, JWTs, and .env tokens.</li>
              <li><strong>Clipboard Contents</strong> — Clipboard read APIs are completely omitted.</li>
              <li><strong>Webcam & Microphone</strong> — No audio/video device capture.</li>
              <li><strong>Personal Browser & Files</strong> — Only files inside the allowlisted folder are watched.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

