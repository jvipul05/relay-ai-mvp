const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function request(path, options = {}) {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers || {}),
  };
  const startedAt = performance.now();
  const method = (options.method || 'GET').toUpperCase();
  let response;
  try {
    response = await fetch(API_BASE + path, { ...options, headers });
  } catch (error) {
    const durationMs = Math.round(performance.now() - startedAt);
    console.warn(`[Relay API] Network failure: ${method} ${path.split('?')[0]} duration_ms=${durationMs}`);
    throw error;
  }
  const payload = await response.json().catch(() => ({}));
  const durationMs = Math.round(performance.now() - startedAt);
  if (durationMs >= 1500) {
    console.warn(`[Relay API] Slow request: ${method} ${path.split('?')[0]} status=${response.status} duration_ms=${durationMs}`);
  } else if (import.meta.env.DEV) {
    console.debug(`[Relay API] ${method} ${path.split('?')[0]} status=${response.status} duration_ms=${durationMs}`);
  }
  if (!response.ok) {
    const message = typeof payload.detail === 'string' ? payload.detail : 'Request failed (' + response.status + ')';
    throw new Error(message);
  }
  return payload;
}

const projectPath = id => '/api/projects/' + encodeURIComponent(id);

export const relayApi = {
  getProjects: () => request('/api/projects'),
  createProject: data => request('/api/projects', { method: 'POST', body: JSON.stringify(data) }),
  getPortfolio: () => request('/api/portfolio'),
  runRippleAnalysis: data => request('/api/intelligence/ripple', { method: 'POST', body: JSON.stringify(data) }),
  getRippleHistory: (projectId, limit = 10) =>
    request('/api/intelligence/history?project_id=' + encodeURIComponent(projectId) + '&limit=' + encodeURIComponent(limit)),
  recordRippleOutcome: (recordId, data) =>
    request('/api/intelligence/' + encodeURIComponent(recordId) + '/outcome', { method: 'POST', body: JSON.stringify(data) }),
  getProjectGraph: id => request(projectPath(id) + '/graph'),
  chatWithRag: (id, message, history = [], language = 'English') =>
    request(projectPath(id) + '/chat', { method: 'POST', body: JSON.stringify({ message, history, language }) }),
  getProject: id => request(projectPath(id)),
  getInvestigation: id => request(projectPath(id) + '/investigation'),
  runAiInvestigation: (id, language = 'English') =>
    request(projectPath(id) + '/ai-investigation?language=' + encodeURIComponent(language), { method: 'POST' }),
  getActions: id => request(projectPath(id) + '/actions'),
  createAction: (id, data) => request(projectPath(id) + '/actions', { method: 'POST', body: JSON.stringify(data) }),
  approveAction: (projectId, actionId, approvedBy = 'Demo User') =>
    request(projectPath(projectId) + '/actions/' + encodeURIComponent(actionId) + '/approve', {
      method: 'POST', body: JSON.stringify({ approved_by: approvedBy }),
    }),
  executeAction: (projectId, actionId) =>
    request(projectPath(projectId) + '/actions/' + encodeURIComponent(actionId) + '/execute', { method: 'POST' }),
  verifyAction: (projectId, actionId, verifiedBy = 'Demo User') =>
    request(projectPath(projectId) + '/actions/' + encodeURIComponent(actionId) + '/verify', {
      method: 'POST', body: JSON.stringify({ verified_by: verifiedBy }),
    }),
  getAudit: (projectId, actionId) =>
    request(projectPath(projectId) + '/actions/' + encodeURIComponent(actionId) + '/audit'),
  getMockIntegrationRecords: (projectId, source) =>
    request(projectPath(projectId) + '/integrations/mock/' + encodeURIComponent(source) + '/records'),
  syncMockIntegration: (projectId, source, recordIds) =>
    request(projectPath(projectId) + '/integrations/mock/' + encodeURIComponent(source) + '/sync', {
      method: 'POST', body: JSON.stringify(recordIds ? { record_ids: recordIds } : {}),
    }),
  getConnectorConfig: projectId => request(projectPath(projectId) + '/integrations/mock/config'),
  saveConnectorConfig: (projectId, source, baseUrl) =>
    request(projectPath(projectId) + '/integrations/mock/config/' + encodeURIComponent(source), {
      method: 'PUT', body: JSON.stringify({ base_url: baseUrl }),
    }),
  previewRelay: (projectId, { inputText, destination, language, schemaJson, useGoogleSearch, file }) => {
    const body = new FormData();
    body.append('input_text', inputText || '');
    body.append('destination', destination || 'auto');
    body.append('language', language || 'English');
    body.append('schema_json', schemaJson || '');
    body.append('use_google_search', String(Boolean(useGoogleSearch)));
    if (file) body.append('file', file);
    return request(projectPath(projectId) + '/relay/preview', { method: 'POST', body });
  },
  searchDocuments: (projectId, query) =>
    request(projectPath(projectId) + '/documents/search', { method: 'POST', body: JSON.stringify({ query }) }),
  getGmailStatus: projectId => request(projectPath(projectId) + '/email-sync/gmail/status'),
  connectGmail: projectId => request(projectPath(projectId) + '/email-sync/gmail/connect', { method: 'POST' }),
  configureGmail: (projectId, data) =>
    request(projectPath(projectId) + '/email-sync/gmail/config', { method: 'POST', body: JSON.stringify(data) }),
  runGmailSync: projectId =>
    request(projectPath(projectId) + '/email-sync/gmail/run', { method: 'POST' }),
  disconnectGmail: projectId =>
    request(projectPath(projectId) + '/email-sync/gmail/disconnect', { method: 'DELETE' }),
};
