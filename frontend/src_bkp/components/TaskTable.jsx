import React from 'react';
import StatusBadge from './StatusBadge';

function formatDate(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(`${value}T00:00:00`));
}
export default function TaskTable({ tasks = [] }) {
  return <div className="table-wrap"><table className="task-table"><thead><tr><th>Task</th><th>Owner</th><th>Status</th><th>Planned</th><th>Forecast</th><th>Dependency</th></tr></thead><tbody>
    {tasks.map(task => <tr key={task.id}><td><div className="task-name">{task.name}</div><div className="task-id">{task.id}</div></td><td>{task.owner || 'Unassigned'}</td><td><StatusBadge status={task.status}/></td><td>{formatDate(task.planned_date)}</td><td><span className={task.forecast_date > task.planned_date ? 'forecast-late' : ''}>{formatDate(task.forecast_date)}</span></td><td>{task.blocked_by?.length ? <span className="dependency-chip">↳ {task.blocked_by.join(', ')}</span> : <span className="muted">None</span>}</td></tr>)}
    {!tasks.length && <tr><td colSpan="6" className="empty-cell">No tasks have been added to this project yet.</td></tr>}
  </tbody></table></div>;
}
