import { useEffect, useState } from "react";
import { getAgents, getJiraInfo, syncJiraProject } from "../api/client";

export default function TopCommandBar({ projectId, onSearch }) {
  const [jiraConnected, setJiraConnected] = useState(false);
  const [jiraKey, setJiraKey] = useState(projectId || "KAN");
  const [activeAgentsCount, setActiveAgentsCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    getJiraInfo()
      .then((info) => {
        if (info) {
          setJiraConnected(Boolean(info.connected));
          if (info.project_key) setJiraKey(info.project_key);
        }
      })
      .catch(() => setJiraConnected(false));

    getAgents(projectId)
      .then((agents) => {
        if (Array.isArray(agents)) {
          const active = agents.filter((a) => a.status === "ACTIVE").length;
          setActiveAgentsCount(active || agents.length);
        }
      })
      .catch(() => setActiveAgentsCount(0));
  }, [projectId]);

  const handleQuickSync = async () => {
    setSyncing(true);
    try {
      await syncJiraProject(jiraKey, jiraKey);
      window.dispatchEvent(new CustomEvent("projectpulse:synced"));
    } catch (err) {
      console.error("Sync error:", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    if (onSearch) onSearch(e.target.value);
  };

  return (
    <header className="command-bar">
      {/* Left: Breadcrumbs & Live Pulse */}
      <div className="command-bar__left">
        <div className="command-breadcrumb">
          PROJECTPULSE / <span>{jiraKey}</span>
        </div>
        <div className="live-observatory-badge">
          <div className="live-pulse-dot" />
          <span>Live Observatory</span>
        </div>
      </div>

      {/* Middle: Global Search */}
      <div className="command-bar__search">
        <div className="search-input-wrap">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="command-search-input"
            placeholder="Search tasks, commits, events, risks (Press / to focus)..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
          <span className="search-hotkey">⌘K</span>
        </div>
      </div>

      {/* Right: Live Connection Indicators & User Profile */}
      <div className="command-bar__right">
        <div className="connection-indicators">
          <div className="indicator-chip" title={jiraConnected ? "Jira Cloud Connected" : "Jira Disconnected"}>
            <span
              className={`indicator-dot ${jiraConnected ? "indicator-dot--online" : "indicator-dot--offline"}`}
            />
            Jira
          </div>
          <div className="indicator-chip" title={`${activeAgentsCount} Agents Reporting`}>
            <span
              className={`indicator-dot ${activeAgentsCount > 0 ? "indicator-dot--online" : "indicator-dot--syncing"}`}
            />
            Agent
          </div>
          <div className="indicator-chip" title="Git Telemetry Linked">
            <span className="indicator-dot indicator-dot--online" />
            Git
          </div>
          <div className="indicator-chip" title="Build Pipeline Healthy">
            <span className="indicator-dot indicator-dot--online" />
            Build
          </div>
          <div className="indicator-chip" title="Test Quality Gate Active">
            <span className="indicator-dot indicator-dot--online" />
            Test
          </div>
        </div>

        {/* Quick Sync Button */}
        <button
          type="button"
          className="btn-primary"
          style={{ fontSize: "0.8rem", padding: "0.35rem 0.85rem" }}
          onClick={handleQuickSync}
          disabled={syncing}
          title={`Synchronize latest issues from Jira Cloud ${jiraKey}`}
        >
          {syncing ? "🔄 Syncing..." : `Sync ${jiraKey}`}
        </button>

        {/* User Badge */}
        <div className="user-profile-badge">
          <div className="user-avatar-circle">
            AR
            <div className="user-avatar-presence" />
          </div>
        </div>
      </div>
    </header>
  );
}
