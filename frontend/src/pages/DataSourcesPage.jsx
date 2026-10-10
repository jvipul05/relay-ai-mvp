import React, { useEffect, useState } from 'react';

const SOURCES = [
  { id: 'jira', name: 'Jira', icon: 'J', description: 'Issue tracker records: status, assignee, planned and forecast dates.' },
  { id: 'confluence', name: 'Confluence', icon: 'C', description: 'Project overview, risk notes, release context and decisions.' },
];

export default function DataSourcesPage({ project, onFetch, onSync, busySource, fetchResults, syncResults, errors }) {
  const [selected, setSelected] = useState({ jira: [], confluence: [] });
  useEffect(() => setSelected({ jira: [], confluence: [] }), [project?.id]);
  const toggle = (source, id) => setSelected(current => {
    const values = current[source] || [];
    return { ...current, [source]: values.includes(id) ? values.filter(x => x !== id) : [...values, id] };
  });
  return <div className="page-stack">
    <section className="page-intro-row">
      <div><div className="eyebrow">CONNECTORS · RAG INGESTION</div><h2>Data sources</h2>
        <p>Fetch demo Jira and Confluence records at runtime, preview the records, then ingest selected records into this project's MySQL-backed RAG index.</p>
      </div>
      <span className="status-badge status-warning"><span className="status-dot"/>Synthetic demo connectors</span>
    </section>
    <div className="error-banner"><span>i</span><div><strong>Demo data, not live Atlassian</strong><p>These endpoints simulate Jira and Confluence. No Atlassian account, API token, or paid service is required. Each imported record is labelled as synthetic evidence.</p></div></div>
    <section className="data-source-grid">
      {SOURCES.map(source => {
        const data = fetchResults[source.id];
        const selectedIds = selected[source.id] || [];
        const records = data?.records || [];
        const result = syncResults[source.id];
        const busy = busySource === source.id;
        return <article className="panel data-source-card" key={source.id}>
          <div className="data-source-header">
            <div className={`data-source-logo ${source.id}`}>{source.icon}</div>
            <div className="data-source-heading"><h3>{source.name}</h3><p>{source.description}</p></div>
            <span className="status-badge status-info">Demo</span>
          </div>
          <div className="data-source-actions">
            <button className="button button-secondary" onClick={() => onFetch(source.id)} disabled={Boolean(busySource)}>{busy && !data ? 'Fetching…' : 'Fetch records'}</button>
            <button className="button button-primary" onClick={() => onSync(source.id, selectedIds.length ? selectedIds : null)} disabled={Boolean(busySource) || !records.length}>{busy ? 'Syncing…' : selectedIds.length ? `Ingest selected (${selectedIds.length})` : 'Ingest all into RAG'}</button>
          </div>
          {errors[source.id] && <div className="form-error data-source-error">{errors[source.id]}</div>}
          {data && <div className="data-source-summary"><span><strong>{records.length}</strong> records fetched at runtime</span><span>Project <strong>{project?.id}</strong></span></div>}
          {records.length > 0 && <div className="source-record-list">
            <div className="source-record-list-heading"><strong>Available records</strong><button className="text-button" onClick={() => setSelected(cur => ({ ...cur, [source.id]: selectedIds.length === records.length ? [] : records.map(r => r.record_id) }))}>{selectedIds.length === records.length ? 'Clear selection' : 'Select all'}</button></div>
            {records.map(record => <label className="source-record" key={record.record_id}>
              <input type="checkbox" checked={selectedIds.includes(record.record_id)} onChange={() => toggle(source.id, record.record_id)} />
              <span className="source-record-body"><strong>{record.title}</strong><small>{record.record_id} · {record.status || record.record_type}{record.assignee ? ` · ${record.assignee}` : ''}</small><span>{record.content_preview}</span></span>
            </label>)}
          </div>}
          {result && <div className="source-sync-result">
            <strong>Ingestion result</strong>
            <div className="sync-result-grid"><div><span>Fetched</span><strong>{result.records_fetched}</strong></div><div><span>Created</span><strong>{result.documents_created}</strong></div><div><span>Existing</span><strong>{result.already_present}</strong></div><div><span>Chunks</span><strong>{result.chunks_indexed}</strong></div></div>
            <p>{result.message}</p>
          </div>}
          {!data && <div className="email-empty-note">Fetch records to preview what will be ingested. Fetching alone does not write to MySQL.</div>}
        </article>;
      })}
    </section>
  </div>;
}
