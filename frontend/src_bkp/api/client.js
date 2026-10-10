const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.detail === 'string' ? payload.detail : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

export const relayApi = {
  getProjects: () => request('/api/projects'),
  getProject: (id) => request(`/api/projects/${encodeURIComponent(id)}`),
  getInvestigation: (id) => request(`/api/projects/${encodeURIComponent(id)}/investigation`),
  runAiInvestigation: (id) => request(`/api/projects/${encodeURIComponent(id)}/ai-investigation`, { method: 'POST' }),
  getActions: (id) => request(`/api/projects/${encodeURIComponent(id)}/actions`),
  createAction: (id, data) => request(`/api/projects/${encodeURIComponent(id)}/actions`, { method: 'POST', body: JSON.stringify(data) }),
  approveAction: (projectId, actionId, approvedBy = 'Demo User') => request(`/api/projects/${encodeURIComponent(projectId)}/actions/${encodeURIComponent(actionId)}/approve`, { method: 'POST', body: JSON.stringify({ approved_by: approvedBy }) }),
  executeAction: (projectId, actionId) => request(`/api/projects/${encodeURIComponent(projectId)}/actions/${encodeURIComponent(actionId)}/execute`, { method: 'POST' }),
  verifyAction: (projectId, actionId, verifiedBy = 'Demo User') => request(`/api/projects/${encodeURIComponent(projectId)}/actions/${encodeURIComponent(actionId)}/verify`, { method: 'POST', body: JSON.stringify({ verified_by: verifiedBy }) }),
  getAudit: (projectId, actionId) => request(`/api/projects/${encodeURIComponent(projectId)}/actions/${encodeURIComponent(actionId)}/audit`),
};
