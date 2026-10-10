import React from 'react';

const titles = { overview: ['Project overview', 'A live view of delivery health and execution risk.'], investigation: ['AI investigation', 'Understand what changed, why it matters, and what to do next.'], actions: ['Recovery actions', 'Turn recommendations into controlled, auditable work.'], evidence: ['Evidence library', 'Explore the project documents supporting Relay’s findings.'] };
export default function Topbar({ activeView, project, onRefresh, refreshing }) {
  const [title, subtitle] = titles[activeView] || titles.overview;
  return <header className="topbar"><div className="mobile-brand"><span className="brand-mark">r.</span><b>relay</b></div><div className="page-heading"><div className="breadcrumb">PROJECTS <span>/</span> {project?.name || 'Workspace'}</div><h1>{title}</h1><p>{subtitle}</p></div><div className="topbar-actions"><span className="environment-pill"><span className="live-dot"/> Local demo</span><button className="icon-button" title="Refresh project data" onClick={onRefresh} disabled={refreshing}>{refreshing ? '…' : '↻'}</button><div className="topbar-avatar">VJ</div></div></header>;
}
