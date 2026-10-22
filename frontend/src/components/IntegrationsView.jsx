import { useCallback, useEffect, useState } from "react";
import {
  connectIntegration,
  connectJira,
  disconnectIntegration,
  getIntegrations,
  getJiraInfo,
  getJiraProjects,
  getSyncHistory,
  getTasks,
  syncIntegrations,
  syncJiraProject,
  testJiraConnection,
} from "../api/client";

export default function IntegrationsView({ projectId }) {
  const [integrations, setIntegrations] = useState([]);
  const [syncHistory, setSyncHistory] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [syncResult, setSyncResult] = useState(null);

  // Real Jira Cloud Integration State
  const [jiraInfo, setJiraInfo] = useState(null);
  const [showJiraModal, setShowJiraModal] = useState(false);
  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraProjects, setJiraProjects] = useState([]);
  const [selectedJiraKey, setSelectedJiraKey] = useState(projectId || "KAN");
  const [jiraConnecting, setJiraConnecting] = useState(false);
  const [jiraSyncing, setJiraSyncing] = useState(false);
  const [jiraMsg, setJiraMsg] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [tools, history, jInfo, jProjects, taskList] = await Promise.all([
        getIntegrations(),
        getSyncHistory(projectId).catch(() => []),
        getJiraInfo().catch(() => null),
        getJiraProjects().catch(() => []),
        getTasks(projectId).catch(() => []),
      ]);
      setIntegrations(tools || []);
      setSyncHistory(history || []);
      setJiraInfo(jInfo);
      setTasks(taskList || []);
      if (jInfo?.base_url) setJiraUrl(jInfo.base_url);
      if (jInfo?.email) setJiraEmail(jInfo.email);
      if (jInfo?.project_key) {
        setSelectedJiraKey(jInfo.project_key);
      } else if (projectId) {
        setSelectedJiraKey(projectId);
      }
      setJiraProjects(jProjects || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggle = async (platform, isConnected) => {
    try {
      if (isConnected) {
        await disconnectIntegration(platform);
      } else {
        await connectIntegration(platform, {});
      }
      await load();
    } catch (err) {
      alert(`Integration toggle failed: ${err.message}`);
    }
  };

  const handleSyncAll = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await syncIntegrations(projectId);
      setSyncResult(res);
      await load();
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleConnectJira = async (e) => {
    e?.preventDefault();
    setJiraConnecting(true);
    setJiraMsg(null);
    try {
      const res = await connectJira({
        base_url: jiraUrl,
        email: jiraEmail,
        api_token: jiraToken,
      });
      setJiraMsg({ type: "success", text: res.message });
      const projects = await getJiraProjects();
      setJiraProjects(projects);
      await load();
      setTimeout(() => setShowJiraModal(false), 1500);
    } catch (err) {
      setJiraMsg({ type: "error", text: `Connection error: ${err.message}` });
    } finally {
      setJiraConnecting(false);
    }
  };

  const handleSyncJira = async () => {
    setJiraSyncing(true);
    setJiraMsg(null);
    const targetKey = selectedJiraKey || jiraInfo?.project_key || projectId || "KAN";
    try {
      const res = await syncJiraProject(targetKey, targetKey);
      if (res.status === "FAILED") {
        setJiraMsg({
          type: "error",
          text: `Sync Failed: ${res.error_message || "Could not synchronize issues from Jira Cloud."}`,
        });
      } else {
        setJiraMsg({
          type: "success",
          text: `Jira Sync (${targetKey}): Fetched ${res.records_fetched} issues · Created: ${res.records_created} · Updated: ${res.records_updated} · Unchanged: ${res.records_unchanged} · Failed: ${res.records_failed} (${res.duration_sec}s)`,
        });
      }
      await load();
    } catch (err) {
      setJiraMsg({ type: "error", text: `Sync failed: ${err.message}` });
    } finally {
      setJiraSyncing(false);
    }
  };

  const handleTestJira = async () => {
    setJiraConnecting(true);
    setJiraMsg(null);
    try {
      const res = await testJiraConnection(selectedJiraKey);
      if (res.success) {
        setJiraMsg({
          type: "success",
          text: `Connection verified! Authenticated as "${res.user_display_name || res.email}" on ${res.base_url}.${res.project_found ? ` Project [${res.project_key}] (${res.project_name}) confirmed.` : ""}`,
        });
      } else {
        setJiraMsg({
          type: "error",
          text: `Connection test failed: ${res.error_message || "Unknown error"}`,
        });
      }
      await load();
    } catch (err) {
      setJiraMsg({ type: "error", text: `Test failed: ${err.message}` });
    } finally {
      setJiraConnecting(false);
    }
  };

  const toolConfigs = [
    {
      id: "JIRA",
      name: "Jira Cloud REST API v3",
      icon: "🔷",
      color: "#38bdf8",
      description: "Official Atlassian cloud REST integration extracting issues, ADF descriptions, and sprints",
      connected: Boolean(jiraInfo?.connected),
      stats: `${tasks.length} Issues Synced`,
      projectTag: selectedJiraKey || "KAN",
      lastSync: "Recent",
      isLive: true,
    },
    {
      id: "GITHUB",
      name: "Git Repository & Telemetry",
      icon: "🔀",
      color: "#60a5fa",
      description: "Local workstation repository commit and diff stream correlation",
      connected: true,
      stats: "Active Ingestion",
      projectTag: "master",
      lastSync: "Real-Time",
      isLive: true,
    },
    {
      id: "MONDAY",
      name: "monday.com Work OS",
      icon: "📊",
      color: "#f59e0b",
      description: "Board pulses, status columns, and group item normalizer",
      connected: integrations.find((i) => i.platform === "MONDAY")?.connected || false,
      stats: "Standby",
      projectTag: "Board #1",
      lastSync: "None",
      isLive: false,
    },
    {
      id: "ASANA",
      name: "Asana Workspace",
      icon: "🔴",
      color: "#ec4899",
      description: "Workspace task lists, assignee mapping, and custom fields sync",
      connected: integrations.find((i) => i.platform === "ASANA")?.connected || false,
      stats: "Standby",
      projectTag: "Workspace",
      lastSync: "None",
      isLive: false,
    },
    {
      id: "TRELLO",
      name: "Trello Boards",
      icon: "📋",
      color: "#38bdf8",
      description: "Kanban board card movements, list states, and checklists",
      connected: integrations.find((i) => i.platform === "TRELLO")?.connected || false,
      stats: "Standby",
      projectTag: "Sprint Board",
      lastSync: "None",
      isLive: false,
    },
    {
      id: "CLICKUP",
      name: "ClickUp Spaces",
      icon: "⚡",
      color: "#a855f7",
      description: "Space folders, task statuses, and time estimate tracking",
      connected: integrations.find((i) => i.platform === "CLICKUP")?.connected || false,
      stats: "Standby",
      projectTag: "Dev Space",
      lastSync: "None",
      isLive: false,
    },
    {
      id: "LINEAR",
      name: "Linear Cycles",
      icon: "🔺",
      color: "#f43f5e",
      description: "Issue cycles, roadmap projects, and engineering triage sync",
      connected: integrations.find((i) => i.platform === "LINEAR")?.connected || false,
      stats: "Standby",
      projectTag: "Team Core",
      lastSync: "None",
      isLive: false,
    },
  ];

  return (
    <div className="view">
      {/* 1. Header */}
      <header className="view__header">
        <div>
          <p className="view__mode">
            <span>🔗</span> INTEGRATION CONTROL CENTER
          </p>
          <h1>External PM Tools & Real Jira Cloud</h1>
          <p className="view__subtitle">
            Unified adapter layer syncing project management plans from Jira Cloud, Git, and issue tracking suites
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={() => setShowJiraModal(true)}
          >
            ⚙️ Configure Jira
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={handleSyncAll}
            disabled={syncing}
          >
            {syncing ? "🔄 Synchronizing..." : "🔄 Sync All Tools"}
          </button>
        </div>
      </header>

      {/* 2. REAL JIRA CLOUD ACTIVE CONNECTION HERO CARD */}
      <section
        className="card"
        style={{
          borderLeft: `4px solid ${jiraInfo?.connected ? "#10b981" : "#ef4444"}`,
          background: "linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(11, 25, 44, 0.6))",
        }}
      >
        <div className="card__header-row">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span style={{ fontSize: "1.4rem" }}>🔷</span>
              <h2 style={{ fontSize: "1.2rem" }}>Live Jira Cloud REST API v3 Integration</h2>
              <span
                className={`status-pill ${
                  jiraInfo?.connected ? "status-pill--active" : "status-pill--danger"
                }`}
              >
                ● {jiraInfo?.connected ? "CONNECTED & ACTIVE" : "DISCONNECTED"}
              </span>
            </div>
            <p className="card__subtitle" style={{ marginTop: "0.4rem" }}>
              Instance: <code>{jiraInfo?.base_url || "https://projectpulsemajor.atlassian.net"}</code> · Authenticated User: <strong>{jiraInfo?.user_display_name || "sneha"}</strong> · API Token: <code>{jiraInfo?.masked_token || "ATAT********"}</code>
            </p>
          </div>

          {/* Sync & Test controls */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="text"
              value={selectedJiraKey}
              onChange={(e) => setSelectedJiraKey(e.target.value.toUpperCase())}
              placeholder="Project Key (e.g. KAN)"
              style={{
                width: "90px",
                padding: "0.4rem 0.6rem",
                borderRadius: "6px",
                background: "rgba(7, 11, 20, 0.8)",
                border: "1px solid var(--border-medium)",
                color: "#fff",
                fontWeight: 700,
                textAlign: "center",
                textTransform: "uppercase",
              }}
            />
            <button
              type="button"
              className="btn-primary"
              onClick={handleSyncJira}
              disabled={jiraSyncing}
            >
              {jiraSyncing ? "🔄 Syncing..." : `Sync ${selectedJiraKey || "KAN"}`}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleTestJira}
              disabled={jiraConnecting}
            >
              {jiraConnecting ? "Testing..." : "🔍 Test Connection"}
            </button>
          </div>
        </div>

        {jiraMsg && (
          <div
            style={{
              marginTop: "0.85rem",
              padding: "0.6rem 0.85rem",
              borderRadius: "6px",
              background: jiraMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
              color: jiraMsg.type === "success" ? "#34d399" : "#fca5a5",
              border: `1px solid ${jiraMsg.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
              fontSize: "0.84rem",
            }}
          >
            {jiraMsg.text}
          </div>
        )}
      </section>

      {/* 3. INTEGRATION CONTROL CARDS GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.25rem" }}>
        {toolConfigs.map((tool) => (
          <div
            key={tool.id}
            className="card"
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.85rem",
              borderColor: tool.connected ? "rgba(56, 189, 248, 0.25)" : "var(--border-subtle)",
              background: tool.connected ? "linear-gradient(135deg, rgba(17, 24, 39, 0.9), rgba(15, 23, 42, 0.7))" : "var(--bg-card)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span style={{ fontSize: "1.6rem" }}>{tool.icon}</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: "0.95rem", color: "#fff" }}>{tool.name}</h3>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Target: {tool.projectTag}</span>
                </div>
              </div>

              <span
                className={`status-pill ${
                  tool.connected ? "status-pill--active" : ""
                }`}
                style={{ fontSize: "0.72rem", padding: "0.15rem 0.5rem" }}
              >
                ● {tool.connected ? "CONNECTED" : "NOT CONNECTED"}
              </span>
            </div>

            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              {tool.description}
            </p>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.45rem 0.65rem",
                borderRadius: "6px",
                background: "rgba(7, 11, 20, 0.5)",
                fontSize: "0.74rem",
                color: "var(--text-muted)",
              }}
            >
              <span>Telemetry: <strong style={{ color: "#fff" }}>{tool.stats}</strong></span>
              <span>Last Sync: <strong>{tool.lastSync}</strong></span>
            </div>

            <div style={{ display: "flex", gap: "0.5rem", marginTop: "auto", paddingTop: "0.5rem", borderTop: "1px solid var(--border-subtle)" }}>
              {tool.id === "JIRA" ? (
                <>
                  <button
                    type="button"
                    className="btn-primary"
                    style={{ flex: 1, fontSize: "0.78rem", padding: "0.35rem 0.5rem" }}
                    onClick={handleSyncJira}
                    disabled={jiraSyncing}
                  >
                    {jiraSyncing ? "Syncing..." : `Sync ${selectedJiraKey || "KAN"}`}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ fontSize: "0.78rem", padding: "0.35rem 0.6rem" }}
                    onClick={() => setShowJiraModal(true)}
                  >
                    Configure
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className={tool.connected ? "btn-secondary" : "btn-primary"}
                  style={{ width: "100%", fontSize: "0.78rem", padding: "0.35rem 0.5rem" }}
                  onClick={() => handleToggle(tool.id, tool.connected)}
                >
                  {tool.connected ? "Disconnect Adapter" : "Connect Adapter"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 4. SYNCHRONIZATION AUDIT HISTORY TABLE */}
      <section className="card" style={{ marginTop: "1rem" }}>
        <div className="card__header-row">
          <div>
            <h2>📜 Synchronization Audit Ledger</h2>
            <p className="card__subtitle">Immutable telemetry audit logs capturing records, latency, and status</p>
          </div>
          <span className="badge badge--platform">{syncHistory.length} Runs Logged</span>
        </div>

        {syncHistory.length === 0 ? (
          <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            No synchronization history recorded yet. Click "Sync KAN" to execute an audit run.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="agents-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Source</th>
                  <th>Target Project</th>
                  <th>Timestamp</th>
                  <th>Fetched</th>
                  <th>Created</th>
                  <th>Updated</th>
                  <th>Unchanged</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {syncHistory.map((run) => (
                  <tr key={run.id || run.integration_id}>
                    <td>
                      <code>{run.integration_id || run.id}</code>
                    </td>
                    <td>
                      <span className="badge badge--platform">{run.source}</span>
                    </td>
                    <td>
                      <strong>{run.project_id || selectedJiraKey || "KAN"}</strong>
                    </td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontFamily: "monospace" }}>
                      {run.sync_started ? new Date(run.sync_started).toLocaleString() : "Recent"}
                    </td>
                    <td>
                      <strong style={{ color: "#fff" }}>{run.records_fetched || 0}</strong>
                    </td>
                    <td>
                      <span style={{ color: "#10b981", fontWeight: 600 }}>+{run.records_created || 0}</span>
                    </td>
                    <td>
                      <span style={{ color: "#38bdf8", fontWeight: 600 }}>{run.records_updated || 0}</span>
                    </td>
                    <td style={{ color: "var(--text-dim)" }}>
                      {run.records_unchanged || 0}
                    </td>
                    <td>
                      <span
                        className={`status-pill ${
                          run.status === "SUCCESS"
                            ? "status-pill--active"
                            : run.status === "IN_PROGRESS"
                            ? "status-pill--warn"
                            : "status-pill--danger"
                        }`}
                        style={{ fontSize: "0.72rem", padding: "0.15rem 0.5rem" }}
                      >
                        ● {run.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 5. JIRA CONFIGURATION MODAL */}
      {showJiraModal && (
        <div className="modal-backdrop" onClick={() => setShowJiraModal(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "560px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "1.4rem" }}>⚙️</span>
                <h3 style={{ margin: 0, fontSize: "1.2rem", color: "#fff" }}>Configure Jira Cloud Connection</h3>
              </div>
              <button
                type="button"
                className="btn-secondary"
                style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}
                onClick={() => setShowJiraModal(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleConnectJira} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
                  Jira Base Domain URL
                </label>
                <input
                  type="url"
                  placeholder="https://your-domain.atlassian.net"
                  value={jiraUrl}
                  onChange={(e) => setJiraUrl(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "0.55rem 0.8rem",
                    borderRadius: "6px",
                    background: "rgba(7, 11, 20, 0.8)",
                    border: "1px solid var(--border-medium)",
                    color: "#fff",
                    fontSize: "0.88rem",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
                  Atlassian Account Email
                </label>
                <input
                  type="email"
                  placeholder="developer@company.com"
                  value={jiraEmail}
                  onChange={(e) => setJiraEmail(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "0.55rem 0.8rem",
                    borderRadius: "6px",
                    background: "rgba(7, 11, 20, 0.8)",
                    border: "1px solid var(--border-medium)",
                    color: "#fff",
                    fontSize: "0.88rem",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "0.3rem" }}>
                  Jira API Token
                </label>
                <input
                  type="password"
                  placeholder="Enter Atlassian API Token"
                  value={jiraToken}
                  onChange={(e) => setJiraToken(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "0.55rem 0.8rem",
                    borderRadius: "6px",
                    background: "rgba(7, 11, 20, 0.8)",
                    border: "1px solid var(--border-medium)",
                    color: "#fff",
                    fontSize: "0.88rem",
                  }}
                />
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "block", marginTop: "0.25rem" }}>
                  Tokens are encrypted in memory on the backend and never exposed in React or logs.
                </span>
              </div>

              {jiraMsg && (
                <div
                  style={{
                    padding: "0.6rem 0.85rem",
                    borderRadius: "6px",
                    background: jiraMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                    color: jiraMsg.type === "success" ? "#34d399" : "#fca5a5",
                    fontSize: "0.82rem",
                  }}
                >
                  {jiraMsg.text}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowJiraModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={jiraConnecting}
                >
                  {jiraConnecting ? "Connecting..." : "Save & Verify Connection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
