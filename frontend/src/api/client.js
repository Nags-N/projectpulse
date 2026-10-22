const API_BASE = import.meta.env.VITE_API_BASE || "";

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
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

export async function getAgents(projectId = "") {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return fetchJson(`/api/agents${q}`);
}

export async function getTasks(projectId = "") {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return fetchJson(`/api/tasks${q}`);
}

export async function getEvents(params = {}) {
  const q = new URLSearchParams(params).toString();
  return fetchJson(`/api/events${q ? `?${q}` : ""}`);
}

export async function getTestingMetrics(projectId = "") {
  return fetchJson(`/api/projects/${projectId}/testing`);
}

export async function getQAMetrics(projectId = "") {
  return fetchJson(`/api/projects/${projectId}/qa`);
}

export async function reportDefect(projectId, payload) {
  return fetchJson(`/api/projects/${projectId}/defects`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDefectStatus(defectId, status) {
  return fetchJson(`/api/defects/${defectId}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export async function recordQAVerdict(projectId, payload) {
  return fetchJson(`/api/projects/${projectId}/qa/verdict`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getIntegrations() {
  return fetchJson("/api/integrations");
}

export async function connectIntegration(platform, payload = {}) {
  return fetchJson(`/api/integrations/${platform}/connect`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function disconnectIntegration(platform) {
  return fetchJson(`/api/integrations/${platform}/disconnect`, {
    method: "POST",
  });
}

export async function syncIntegrations(projectId = "DLX") {
  return fetchJson(`/api/integrations/sync?project_id=${encodeURIComponent(projectId)}`, {
    method: "POST",
  });
}

// AI Assistant APIs (Phases 14 & 15)
export async function getAISuggestions(projectId = "DLX") {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/ai/suggestions`);
}

export async function chatWithAI(projectId = "DLX", query) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/ai/chat`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

// Task Evidence & Intelligence APIs (Features 9, 13, 20)
export async function getTaskEvidence(taskId) {
  return fetchJson(`/api/tasks/${encodeURIComponent(taskId)}/evidence`);
}

export async function getSprintAnalytics(projectId = "DLX", sprint = "Sprint 1") {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/analytics?sprint=${encodeURIComponent(sprint)}`);
}

export async function getSyncHistory(projectId = "DLX") {
  return fetchJson(`/api/integrations/history?project_id=${encodeURIComponent(projectId)}`);
}

// 6 Major Extension APIs
export async function getAIRisks(projectId = "DLX") {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/risks/ai`);
}

export async function getProjectAISummary(projectId = "DLX", summaryType = "project", timeframe = "24h") {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/ai/summary`, {
    method: "POST",
    body: JSON.stringify({ summary_type: summaryType, timeframe }),
  });
}

export async function getTaskAISummary(taskId) {
  return fetchJson(`/api/tasks/${encodeURIComponent(taskId)}/ai/summary`, {
    method: "POST",
  });
}

export async function getUnifiedTimeline(projectId = "DLX", filter = "ALL", limit = 150) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/timeline?filter=${encodeURIComponent(filter)}&limit=${limit}`);
}

export async function getCodeExplanations(projectId = "DLX", limit = 30) {
  return fetchJson(`/api/projects/${encodeURIComponent(projectId)}/code-explanations?limit=${limit}`);
}

export async function getJiraInfo() {
  return fetchJson("/api/integrations/jira/info");
}

export async function testJiraConnection(projectKey = null) {
  const query = projectKey ? `?project_key=${encodeURIComponent(projectKey)}` : "";
  return fetchJson(`/api/integrations/jira/test${query}`);
}

export async function connectJira(credentials) {
  return fetchJson("/api/integrations/jira/connect", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function getJiraProjects() {
  return fetchJson("/api/integrations/jira/projects");
}

export async function getJiraIssues(projectId = null, limit = 50, offset = 0, jql = null) {
  let url = `/api/integrations/jira/issues?limit=${limit}&offset=${offset}`;
  if (projectId) url += `&project_id=${encodeURIComponent(projectId)}`;
  if (jql) url += `&jql=${encodeURIComponent(jql)}`;
  return fetchJson(url);
}

export async function getJiraIssueDetail(issueKey) {
  return fetchJson(`/api/integrations/jira/issues/${encodeURIComponent(issueKey)}`);
}

export async function syncJiraProject(projectId = null, jiraProjectKey = null) {
  const body = {};
  if (projectId) body.project_id = projectId;
  if (jiraProjectKey) body.jira_project_key = jiraProjectKey;
  return fetchJson("/api/integrations/jira/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}




