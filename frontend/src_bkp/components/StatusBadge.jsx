import React from 'react';

export default function StatusBadge({ status = 'Unknown' }) {
  const normalized = String(status).toLowerCase().replaceAll('_', ' ');
  let tone = 'neutral';
  if (['verified', 'completed', 'healthy', 'on track'].includes(normalized)) tone = 'success';
  else if (['at risk', 'pending approval', 'delayed', 'blocked'].includes(normalized)) tone = 'warning';
  else if (['executed', 'approved', 'in progress'].includes(normalized)) tone = 'info';
  else if (['failed', 'cancelled', 'overdue'].includes(normalized)) tone = 'danger';
  return <span className={`status-badge status-${tone}`}><span className="status-dot" />{normalized}</span>;
}
