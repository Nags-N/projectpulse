import { useEffect, useState } from "react";
import { getAppConfig, getJiraInfo, getTasks } from "../api/client";

export default function SystemStatusStrip({ projectId }) {
  const [jiraInfo, setJiraInfo] = useState(null);
  const [taskCount, setTaskCount] = useState(0);
  const [config, setConfig] = useState(null);

  useEffect(() => {
    getJiraInfo()
      .then(setJiraInfo)
      .catch(() => setJiraInfo(null));

    getAppConfig()
      .then(setConfig)
      .catch(() => {});

    getTasks(projectId)
      .then((tasks) => {
        if (Array.isArray(tasks)) setTaskCount(tasks.length);
      })
      .catch(() => {});
  }, [projectId]);

  const isConnected = Boolean(jiraInfo?.connected);
  const key = jiraInfo?.project_key || projectId || "KAN";

  return (
    <div className="system-status-strip">
      <div className="status-strip-item">
        <span
          style={{
            width: "7px",
            height: "7px",
            borderRadius: "50%",
            background: isConnected ? "#10b981" : "#ef4444",
            boxShadow: isConnected ? "0 0 6px #10b981" : "none",
          }}
        />
        <span>Jira Cloud: <strong>{key}</strong> ({isConnected ? "Live Connected" : "Disconnected"})</span>
      </div>

      <span className="status-strip-sep">/</span>

      <div className="status-strip-item">
        <span>Planned Issues: <strong>{taskCount} Synced</strong></span>
      </div>

      <span className="status-strip-sep">/</span>

      <div className="status-strip-item">
        <span>Active User: <strong>{jiraInfo?.user_display_name || "sneha"}</strong></span>
      </div>

      <span className="status-strip-sep">/</span>

      <div className="status-strip-item">
        <span>Telemetry Stream: <strong>Active Ingestion</strong></span>
      </div>

      <span className="status-strip-sep">/</span>

      <div className="status-strip-item">
        <span>Engine: <strong>ProjectPulse Early Warning v1.0</strong></span>
      </div>
    </div>
  );
}
