import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useSearchParams } from "react-router-dom";
import { getAppConfig } from "./api/client";
import DeveloperView from "./components/DeveloperView";
import ManagerView from "./components/ManagerView";

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
      searchParams.get("project_id") || config?.project_id || "";
    const userId = searchParams.get("user_id") || config?.user_id || "";
    return { projectId, userId, config, configError };
  }, [searchParams, config, configError]);
}

function Layout({ children, projectId, userId }) {
  const devLink = `/developer?project_id=${encodeURIComponent(projectId)}&user_id=${encodeURIComponent(userId)}`;
  const mgrLink = `/manager?project_id=${encodeURIComponent(projectId)}`;

  return (
    <div className="app">
      <nav className="nav">
        <div className="nav__brand">ProjectPulse AI</div>
        <div className="nav__links">
          <Link to={devLink} className="nav__link">
            Developer
          </Link>
          <Link to={mgrLink} className="nav__link">
            Manager
          </Link>
        </div>
      </nav>
      <main className="main">{children}</main>
    </div>
  );
}

function DeveloperPage() {
  const { projectId, userId, configError } = useIds();

  if (configError && !projectId) {
    return <div className="error-panel">Config error: {configError}</div>;
  }

  return (
    <Layout projectId={projectId} userId={userId}>
      <DeveloperView projectId={projectId} userId={userId} />
    </Layout>
  );
}

function ManagerPage() {
  const { projectId, configError } = useIds();

  if (configError && !projectId) {
    return <div className="error-panel">Config error: {configError}</div>;
  }

  return (
    <Layout projectId={projectId} userId="">
      <ManagerView projectId={projectId} />
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/developer" replace />} />
      <Route path="/developer" element={<DeveloperPage />} />
      <Route path="/manager" element={<ManagerPage />} />
    </Routes>
  );
}
