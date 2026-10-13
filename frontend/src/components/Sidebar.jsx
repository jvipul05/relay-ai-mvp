import React from 'react';

const navGroups = [
  {
    label: 'WORKSPACE',
    items: [
      { id: 'overview', icon: '⌂', label: 'Project cockpit' },
      { id: 'portfolio', icon: '▥', label: 'All projects' },
    ],
  },
  {
    label: 'UNDERSTAND',
    items: [
      { id: 'investigation', icon: '✧', label: 'AI investigation' },
      { id: 'dependencies', icon: '⤳', label: 'Dependencies' },
      { id: 'chat', icon: '◌', label: 'Ask Relay' },
    ],
  },
  {
    label: 'TAKE ACTION',
    items: [
      { id: 'relay-studio', icon: '✦', label: 'Relay Studio', highlight: true },
      { id: 'actions', icon: '✓', label: 'Recovery actions' },
    ],
  },
  {
    label: 'EVIDENCE & SOURCES',
    items: [
      { id: 'evidence', icon: '⌕', label: 'Evidence search' },
      { id: 'sources', icon: '⇄', label: 'Connected sources' },
      { id: 'email', icon: '✉', label: 'Email sync' },
    ],
  },
];

export default function Sidebar({ activeView, onNavigate, projects, selectedProjectId, onSelectProject, onSignOut }) {
  const activeProject = projects.find(project => project.id === selectedProjectId);

  return <aside className="sidebar">
    <div className="brand">
      <div className="brand-mark">r.</div>
      <div><div className="brand-name">relay</div><div className="brand-caption">WORK, CONNECTED</div></div>
    </div>

    <div className="sidebar-workspace">
      <div className="workspace-label">ACTIVE WORKSPACE</div>
      <label className="project-select-wrap">
        <span className="project-avatar">{activeProject?.name?.slice(0, 1) || 'P'}</span>
        <span className="project-select-content">
          <span className="muted-label">Project</span>
          <select aria-label="Select project" value={selectedProjectId || ''} onChange={event => onSelectProject(event.target.value)}>
            {projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </span>
        <span className="select-chevron" aria-hidden="true">⌄</span>
      </label>
    </div>

    <nav className="side-nav" aria-label="Main navigation">
      {navGroups.map(group => (
        <div className="nav-group" key={group.label}>
          <div className="nav-label">{group.label}</div>
          {group.items.map(item => (
            <button
              key={item.id}
              type="button"
              title={item.label}
              aria-current={activeView === item.id ? 'page' : undefined}
              className={`nav-item ${activeView === item.id ? 'active' : ''} ${item.highlight ? 'nav-item-highlight' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              {item.highlight && <span className="nav-arrow" aria-hidden="true">→</span>}
            </button>
          ))}
        </div>
      ))}
    </nav>

    <div className="sidebar-bottom">
      <div className="ai-status">
        <span className="live-dot"/>
        <div><strong>Relay copilot</strong><small>Ready when you are</small></div>
      </div>
      <div className="profile">
        <div className="profile-avatar">GD</div>
        <div className="profile-meta"><strong>Guest demo</strong><small>Sample workspace</small></div>
        <button className="profile-signout" type="button" onClick={onSignOut} title="Exit guest demo">Exit</button>
      </div>
    </div>
  </aside>;
}
