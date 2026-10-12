import React from 'react';

const titles = {
  overview: ['Project cockpit', 'A focused brief on delivery health and what to do next.'],
  portfolio: ['Portfolio overview', 'See which projects need attention first.'],
  investigation: ['AI investigation', 'Understand the signal, the cause, and the best next move.'],
  dependencies: ['Dependency map', 'See what is blocking progress and what gets unblocked next.'],
  actions: ['Recovery actions', 'Review, approve, and verify proposed actions in one place.'],
  evidence: ['Evidence search', 'Find the project evidence behind Relay’s recommendations.'],
  chat: ['Ask Relay', 'Ask a project question and explore evidence-backed answers.'],
  sources: ['Connected sources', 'Bring project context together from available sources.'],
  email: ['Email sync', 'Configure project-specific Gmail evidence ingestion.'],
};

export default function Topbar({ activeView, project, onRefresh, refreshing }) {
  const [title, subtitle] = titles[activeView] || titles.overview;
  return (
    <header className="topbar">
      <div className="mobile-brand"><span className="brand-mark">r.</span><b>relay</b></div>
      <div className="page-heading">
        <div className="breadcrumb">WORKSPACE <span>/</span> {project?.name || 'Select a project'}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="topbar-actions">
        <span className="environment-pill"><span className="live-dot"/> Guest demo</span>
        <button className="icon-button" type="button" title="Refresh project data" aria-label="Refresh project data" onClick={onRefresh} disabled={refreshing}>{refreshing ? '…' : '↻'}</button>
        <div className="topbar-avatar" title="Guest demo">GD</div>
      </div>
    </header>
  );
}
