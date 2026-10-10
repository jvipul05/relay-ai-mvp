import React from 'react';
export default function EmptyState({ title, description, action, onAction }) { return <div className="empty-state"><div className="empty-icon">◇</div><h3>{title}</h3><p>{description}</p>{action && <button className="button button-primary" onClick={onAction}>{action}</button>}</div>; }
