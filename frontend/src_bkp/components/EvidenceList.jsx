import React from 'react';
export default function EvidenceList({ evidence = [] }) {
  if (!evidence.length) return <div className="empty-state"><div className="empty-icon">▤</div><h3>No evidence available</h3><p>Project emails and documents will appear here as they are ingested.</p></div>;
  return <div className="evidence-list">{evidence.map(item => <article className="evidence-item" key={item.id}><div className="evidence-file-icon">▤</div><div className="evidence-body"><div className="evidence-title-row"><h3>{item.title}</h3><span className="evidence-id">{item.id}</span></div><p>{item.finding || item.content}</p><div className="evidence-meta"><span>◉ {item.source || 'Project document'}</span>{item.related_task && <span>↗ Related task: {item.related_task}</span>}</div></div></article>)}</div>;
}
