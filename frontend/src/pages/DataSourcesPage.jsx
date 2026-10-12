import React, { useEffect, useState } from 'react';
import { relayApi } from '../api/client';

const SOURCES = [
  { id: 'jira', name: 'Jira', icon: 'J', description: 'Task-shaped issue previews with status, owner, planned date and forecast date.', placeholder: 'https://your-site.atlassian.net' },
  { id: 'confluence', name: 'Confluence', icon: 'C', description: 'Project overview, risks, context and decision-page previews.', placeholder: 'https://your-site.atlassian.net/wiki' },
];

const DEFAULT_CONFIG = {
  jira: { base_url: 'https://example.atlassian.net', mode: 'synthetic_demo' },
  confluence: { base_url: 'https://example.atlassian.net/wiki', mode: 'synthetic_demo' },
};

export default function DataSourcesPage({ project, onFetch, onSync, busySource, fetchResults, syncResults, errors }) {
  const [selected, setSelected] = useState({ jira: [], confluence: [] });
  const [configs, setConfigs] = useState(DEFAULT_CONFIG);
  const [draftUrls, setDraftUrls] = useState({ jira: DEFAULT_CONFIG.jira.base_url, confluence: DEFAULT_CONFIG.confluence.base_url });
  const [saving, setSaving] = useState('');
  const [configError, setConfigError] = useState('');
  const [savedMessage, setSavedMessage] = useState('');

  useEffect(() => {
    setSelected({ jira: [], confluence: [] });
    setConfigError('');
    setSavedMessage('');
    if (!project?.id) return;
    let active = true;
    relayApi.getConnectorConfig(project.id).then(response => {
      if (!active) return;
      const next = response.connectors || DEFAULT_CONFIG;
      setConfigs(next);
      setDraftUrls({
        jira: next.jira?.base_url || DEFAULT_CONFIG.jira.base_url,
        confluence: next.confluence?.base_url || DEFAULT_CONFIG.confluence.base_url,
      });
    }).catch(error => { if (active) setConfigError(error.message || 'Could not load connector test URLs.'); });
    return () => { active = false; };
  }, [project?.id]);

  const toggle = (source, id) => setSelected(current => {
    const values = current[source] || [];
    return { ...current, [source]: values.includes(id) ? values.filter(value => value !== id) : [...values, id] };
  });

  const saveUrl = async source => {
    if (!project?.id) return;
    setSaving(source);
    setConfigError('');
    setSavedMessage('');
    try {
      const response = await relayApi.saveConnectorConfig(project.id, source, draftUrls[source]);
      setConfigs(current => ({ ...current, [source]: { ...current[source], base_url: response.base_url, mode: response.mode } }));
      setDraftUrls(current => ({ ...current, [source]: response.base_url }));
      setSavedMessage(source === 'jira' ? 'Jira test link saved.' : 'Confluence test link saved.');
    } catch (error) {
      setConfigError(error.message || 'Could not save test URL.');
    } finally {
      setSaving('');
    }
  };

  return (
    <div className="page-stack">
      <section className="page-intro-row">
        <div>
          <div className="eyebrow">CONNECTORS · RAG INGESTION</div>
          <h2>Data sources</h2>
          <p>Configure the base links used by synthetic connector previews, inspect the generated records, then ingest them into this project's evidence index.</p>
        </div>
        <span className="status-badge status-warning"><span className="status-dot"/>Synthetic test mode</span>
      </section>

      <div className="error-banner connector-info-banner">
        <span>i</span>
        <div>
          <strong>Test connectors — not live Atlassian synchronization</strong>
          <p>These URLs control clickable preview links only. This mode does not authenticate to Jira or Confluence and does not read/write any remote Atlassian workspace. Re-syncing a record updates its existing evidence document rather than adding another copy.</p>
        </div>
      </div>

      {configError && <div className="form-error connector-config-error">{configError}</div>}
      {savedMessage && <div className="connector-saved-message"><span>✓</span>{savedMessage}</div>}

      <section className="data-source-grid">
        {SOURCES.map(source => {
          const data = fetchResults[source.id];
          const selectedIds = selected[source.id] || [];
          const records = data?.records || [];
          const result = syncResults[source.id];
          const busy = busySource === source.id;
          const config = configs[source.id] || DEFAULT_CONFIG[source.id];
          return (
            <article className="panel data-source-card" key={source.id}>
              <div className="data-source-header">
                <div className={'data-source-logo ' + source.id}>{source.icon}</div>
                <div className="data-source-heading"><h3>{source.name}</h3><p>{source.description}</p></div>
                <span className="status-badge status-info">Synthetic</span>
              </div>

              <div className="connector-url-form">
                <label>
                  <span>{source.name} base URL for test links</span>
                  <input
                    type="url"
                    value={draftUrls[source.id] || ''}
                    placeholder={source.placeholder}
                    onChange={event => setDraftUrls(current => ({ ...current, [source.id]: event.target.value }))}
                    maxLength={500}
                    aria-label={source.name + ' test base URL'}
                  />
                </label>
                <div className="connector-url-footer">
                  <span>Used to build the preview links below.</span>
                  <button className="button button-secondary" type="button" onClick={() => saveUrl(source.id)} disabled={Boolean(saving)}>{saving === source.id ? 'Saving…' : 'Save test URL'}</button>
                </div>
                {config?.base_url && <p className="connector-current-url">Current base: <strong>{config.base_url}</strong></p>}
              </div>

              <div className="data-source-actions">
                <button className="button button-secondary" type="button" onClick={() => onFetch(source.id)} disabled={Boolean(busySource)}>{busy && !data ? 'Fetching…' : 'Fetch preview records'}</button>
                <button className="button button-primary" type="button" onClick={() => onSync(source.id, selectedIds.length ? selectedIds : null)} disabled={Boolean(busySource) || !records.length}>{busy ? 'Syncing…' : selectedIds.length ? 'Ingest selected (' + selectedIds.length + ')' : 'Sync all into evidence'}</button>
              </div>

              {errors[source.id] && <div className="form-error data-source-error">{errors[source.id]}</div>}
              {data && <div className="data-source-summary"><span><strong>{records.length}</strong> preview records</span><span>Project <strong>{project?.id}</strong></span></div>}

              {records.length > 0 && <div className="source-record-list">
                <div className="source-record-list-heading">
                  <strong>Available records</strong>
                  <button className="text-button" type="button" onClick={() => setSelected(current => ({ ...current, [source.id]: selectedIds.length === records.length ? [] : records.map(record => record.record_id) }))}>{selectedIds.length === records.length ? 'Clear selection' : 'Select all'}</button>
                </div>
                {records.map(record => (
                  <div className="source-record" key={record.record_id}>
                    <label className="source-record-select">
                      <input type="checkbox" checked={selectedIds.includes(record.record_id)} onChange={() => toggle(source.id, record.record_id)} />
                    </label>
                    <div className="source-record-body">
                      <strong>{record.title}</strong>
                      <small>{record.record_id} · {record.status || record.record_type}{record.assignee ? ' · ' + record.assignee : ''}</small>
                      <span>{record.content_preview}</span>
                      {record.url && <a href={record.url} target="_blank" rel="noreferrer" className="source-record-link">Open test link ↗</a>}
                    </div>
                  </div>
                ))}
              </div>}

              {result && <div className="source-sync-result">
                <strong>Sync result</strong>
                <div className="sync-result-grid">
                  <div><span>Fetched</span><strong>{result.records_fetched}</strong></div>
                  <div><span>Created</span><strong>{result.documents_created}</strong></div>
                  <div><span>Updated</span><strong>{result.documents_updated ?? 0}</strong></div>
                  <div><span>No change</span><strong>{result.already_present}</strong></div>
                </div>
                <p>{result.message}</p>
              </div>}
              {!data && <div className="email-empty-note">Fetch previews to inspect the generated records. Fetching alone does not write to MySQL.</div>}
            </article>
          );
        })}
      </section>
    </div>
  );
}
