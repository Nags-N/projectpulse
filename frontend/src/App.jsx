import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { getAppConfig } from "./api/client";
import AgentsView from "./components/AgentsView";
import AIAssistantView from "./components/AIAssistantView";
import DeveloperView from "./components/DeveloperView";
import IntegrationsView from "./components/IntegrationsView";
import ManagerView from "./components/ManagerView";
import QAView from "./components/QAView";
import Sidebar from "./components/Sidebar";
import SystemStatusStrip from "./components/SystemStatusStrip";
import TasksView from "./components/TasksView";
import TesterView from "./components/TesterView";
import TopCommandBar from "./components/TopCommandBar";

function useIds() {
  const [searchParams] = useSearchParams();
  const [config, setConfig] = useState(null);
  const [configError, setConfigError] = useState(null);

  useEffect(() => {
    getAppConfig()
      .then(setConfig)
      .catch((err) => setConfigError(err.message));
  }, []);

  return useMemo(() => {
    const projectId =
      searchParams.get("project_id") || config?.project_id || "DLX";
    const userId = searchParams.get("user_id") || config?.user_id || "DEV-001";
    return { projectId, userId, config, configError };
  }, [searchParams, config, configError]);
}

function Layout({ children, projectId, userId }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar
        projectId={projectId}
        userId={userId}
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
      />
      <div className={`app-main ${collapsed ? "app-main--collapsed" : ""}`}>
        <TopCommandBar projectId={projectId} />
        <SystemStatusStrip projectId={projectId} />
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}

function DeveloperPage() {
  const { projectId, userId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId={userId}>
      <DeveloperView projectId={projectId} userId={userId} />
    </Layout>
  );
}

function ManagerPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <ManagerView projectId={projectId} />
    </Layout>
  );
}

function TesterPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <TesterView projectId={projectId} />
    </Layout>
  );
}

function QAPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <QAView projectId={projectId} />
    </Layout>
  );
}

function IntegrationsPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <IntegrationsView projectId={projectId} />
    </Layout>
  );
}

function AgentsPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <AgentsView projectId={projectId} />
    </Layout>
  );
}

function TasksPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <TasksView projectId={projectId} />
    </Layout>
  );
}

function AIAssistantPage() {
  const { projectId, configError } = useIds();
  if (configError && !projectId) return <div className="error-panel">Config error: {configError}</div>;
  return (
    <Layout projectId={projectId} userId="">
      <AIAssistantView projectId={projectId} />
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/manager" replace />} />
      <Route path="/manager" element={<ManagerPage />} />
      <Route path="/developer" element={<DeveloperPage />} />
      <Route path="/tester" element={<TesterPage />} />
      <Route path="/qa" element={<QAPage />} />
      <Route path="/tasks" element={<TasksPage />} />
      <Route path="/integrations" element={<IntegrationsPage />} />
      <Route path="/agents" element={<AgentsPage />} />
      <Route path="/assistant" element={<AIAssistantPage />} />
    </Routes>
  );
}

