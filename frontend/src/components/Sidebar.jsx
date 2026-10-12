import React from 'react';

const navItems = [
  { id: 'overview', icon: '◫', label: 'Overview' },
  { id: 'portfolio', icon: '▥', label: 'Portfolio intelligence' },
  { id: 'dependencies', icon: '⌘', label: 'Dependency map' },
  { id: 'investigation', icon: '⌕', label: 'Investigations' },
  { id: 'actions', icon: '↗', label: 'Recovery actions' },
  { id: 'evidence', icon: '⌕', label: 'Search evidence' },
  { id: 'chat', icon: '✧', label: 'Gemini + RAG chat' },
  { id: 'sources', icon: '⇄', label: 'Data sources' },
  { id: 'email', icon: '✉', label: 'Email integration' },
];

export default function Sidebar({ activeView, onNavigate, projects, selectedProjectId, onSelectProject, onSignOut }) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark">r.</div><div><div className="brand-name">relay</div><div className="brand-caption">ORG INTELLIGENCE</div></div></div>
    <div className="workspace-label">WORKSPACE</div>
    <label className="project-select-wrap">
      <span className="project-avatar">{projects.find(p => p.id === selectedProjectId)?.name?.slice(0, 1) || 'P'}</span>
      <span className="project-select-content"><span className="muted-label">Active project</span>
        <select aria-label="Select project" value={selectedProjectId || ''} onChange={e => onSelectProject(e.target.value)}>
          {projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
        </select>
      </span><span className="select-chevron">⌄</span>
    </label>
    <div className="nav-label">INTELLIGENCE</div>
    <nav className="side-nav" aria-label="Main navigation">
      {navItems.map(item => <button key={item.id} className={`nav-item ${activeView === item.id ? 'active' : ''}`} onClick={() => onNavigate(item.id)}>
        <span className="nav-icon">{item.icon}</span><span>{item.label}</span>{item.id === 'actions' && <span className="nav-arrow">↗</span>}
      </button>)}
    </nav>
    <div className="sidebar-bottom"><div className="ai-status"><span className="live-dot"/><div><strong>Relay intelligence</strong><small>Ready to investigate</small></div></div><div className="profile"><div className="profile-avatar">VJ</div><div className="profile-meta"><strong>Demo workspace</strong><small>Local environment</small></div><button className="profile-signout" type="button" onClick={onSignOut} title="Exit guest demo">Exit</button></div></div>
  </aside>;
}
