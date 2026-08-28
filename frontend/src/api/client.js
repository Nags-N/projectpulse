const API_BASE = import.meta.env.VITE_API_BASE || "";

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  const data = await response.json();
  if (data == null) {
    throw new Error("Empty response from server.");
  }
  return data;
}

export async function getAppConfig() {
  return fetchJson("/api/config");
}

export async function getDeveloperSummary(projectId, userId) {
  const params = new URLSearchParams({ user_id: userId });
  return fetchJson(`/api/projects/${projectId}/summary?${params}`);
}

export async function getManagerDashboard(projectId) {
  const params = new URLSearchParams({ role: "PROJECT_MANAGER" });
  return fetchJson(`/api/projects/${projectId}/dashboard?${params}`);
}
