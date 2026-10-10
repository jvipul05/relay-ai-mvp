import React from 'react';
export default function StatCard({ label, value, note, icon, accent = 'blue' }) {
  return <article className="stat-card"><div className="stat-top"><span className="stat-label">{label}</span><span className={`stat-icon icon-${accent}`}>{icon}</span></div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></article>;
}
