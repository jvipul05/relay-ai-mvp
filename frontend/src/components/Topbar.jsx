import React from 'react';

const titles = {
  overview: ['Project cockpit', 'A focused brief on delivery health and what to do next.'],
  portfolio: ['Portfolio overview', 'See which projects need attention first.'],
  ripple: ['Ripple Intelligence', 'Detect change impacts, compare future scenarios, and learn from outcomes.'],
  investigation: ['AI investigation', 'Understand the signal, the cause, and the best next move.'],
  dependencies: ['Dependency map', 'See what is blocking progress and what gets unblocked next.'],
  actions: ['Recovery actions', 'Review, approve, and verify proposed actions in one place.'],
  evidence: ['Evidence search', 'Find the project evidence behind Relay’s recommendations.'],
  chat: ['Ask Relay', 'Ask a project question and explore evidence-backed answers.'],
  'relay-studio': ['Relay Studio', 'Turn text, images, and voice notes into a structured proposal.'],
  sources: ['Connected sources', 'Configure test links, preview connector records, and sync evidence without duplication.'],
  email: ['Email sync', 'Configure project-specific Gmail evidence ingestion.'],
};

const languages = [
  'English', 'Hindi', 'Spanish', 'French', 'German',
  'Portuguese', 'Japanese', 'Korean', 'Arabic', 'Chinese (Simplified)',
];

export default function Topbar({ activeView, project, onRefresh, refreshing, language = 'English', onLanguageChange }) {
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
        <label className="language-picker">
          <span>AI OUTPUT</span>
          <select aria-label="AI output language" value={language} onChange={event => onLanguageChange?.(event.target.value)}>
            {languages.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <span className="environment-pill"><span className="live-dot"/> Guest demo</span>
        <button className="icon-button" type="button" title="Refresh project data" aria-label="Refresh project data" onClick={onRefresh} disabled={refreshing}>{refreshing ? '…' : '↻'}</button>
        <div className="topbar-avatar" title="Guest demo">GD</div>
      </div>
    </header>
  );
}
