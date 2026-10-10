import React, { useState } from 'react';

export default function EvidenceSearchPage({ project, onSearch, busy, results, searchedQuery, error }) {
  const [query, setQuery] = useState('');
  const submit = (event) => {
    event.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };
  return <div className="page-stack">
    <section className="page-intro-row">
      <div><div className="eyebrow">PROJECT KNOWLEDGE</div><h2>Search evidence</h2>
        <p>Search indexed project documents and Gmail content using semantic retrieval.</p>
      </div>
    </section>
    <section className="panel rag-search-panel">
      <div className="panel-header"><div><h3>Ask the evidence library</h3><p>Search is scoped to {project?.name || project?.id || 'the selected project'}.</p></div><span className="status-badge status-success"><span className="status-dot"/>RAG search</span></div>
      <form className="rag-search-form" onSubmit={submit}>
        <label htmlFor="rag-query">What do you want to find?</label>
        <div className="rag-search-input-row"><input id="rag-query" value={query} onChange={e => setQuery(e.target.value)} placeholder="e.g. vendor API delivery delayed October 15" />
          <button className="button button-primary" type="submit" disabled={busy || !query.trim()}>{busy ? 'Searching…' : 'Search evidence'}</button>
        </div>
        <div className="rag-query-suggestions"><span>Try:</span>{['vendor API delivery delayed October 15', 'What is blocking integration?', 'production release risk'].map(q => <button type="button" key={q} onClick={() => { setQuery(q); onSearch(q); }} disabled={busy}>{q}</button>)}</div>
      </form>
    </section>
    {error && <div className="error-banner"><span>!</span><div><strong>Search failed</strong><p>{error}</p></div></div>}
    {searchedQuery && <section className="panel">
      <div className="panel-header"><div><h3>Search results</h3><p>Results for “{searchedQuery}”</p></div><span className="count-pill">{results.length} results</span></div>
      {!results.length ? <div className="empty-state"><div className="empty-icon">⌕</div><h3>No matching evidence found</h3><p>Try different wording or verify that documents have been ingested and indexed for this project.</p></div> :
      <div className="rag-results-list">{results.map((result, index) => <article className="rag-result" key={result.chunk_id || result.document_id || index}>
        <div className="rag-result-top"><div><span className="source-type">{String(result.source || '').startsWith('gmail:') ? 'GMAIL EMAIL' : 'PROJECT DOCUMENT'}</span><h4>{result.title || 'Untitled source'}</h4></div><span className="rag-score">Score {typeof result.score === 'number' ? result.score.toFixed(4) : '—'}</span></div>
        <p className="rag-result-content">{result.content || 'No content available.'}</p>
        <div className="rag-result-meta"><span>Document: {result.document_id || '—'}</span><span>Task: {result.related_task_id || 'Not linked'}</span><span>Source: {result.source || 'Unknown'}</span></div>
      </article>)}</div>}
    </section>}
    {!searchedQuery && <section className="panel rag-info-panel"><div className="empty-state"><div className="empty-icon">⌕</div><h3>Search real project evidence</h3><p>Search runs against the selected project's indexed document chunks. Gmail results appear here after a successful email sync and indexing.</p></div></section>}
  </div>;
}
