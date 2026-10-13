import React, { useEffect, useState } from 'react';
import StatCard from '../components/StatCard';

const defaultForm = {
  name: '',
  project_id: '',
  planned_release: '',
  status: 'Planning',
  risk_score: 25,
  description: '',
  tasks_text: '',
};

export default function PortfolioPage({ onOpenProject, onCreateProject }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState('');
  const [form, setForm] = useState(defaultForm);

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')}/api/portfolio`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Portfolio request failed');
      setData(result);
    } catch (err) {
      setError(err.message || 'Could not load portfolio.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const setField = (key, value) => setForm(current => ({ ...current, [key]: value }));

  const create = async event => {
    event.preventDefault();
    setCreateError('');
    if (!form.name.trim() || !form.planned_release) {
      setCreateError('Project name and target release date are required.');
      return;
    }
    if (!onCreateProject) {
      setCreateError('Project creation is not connected to the workspace.');
      return;
    }
    setCreateBusy(true);
    try {
      const tasks = form.tasks_text.split('\n').map(name => name.trim()).filter(Boolean).slice(0, 30)
        .map(name => ({ name, status: 'Planned', owner: 'Unassigned' }));
      const payload = {
        name: form.name.trim(),
        ...(form.project_id.trim() ? { project_id: form.project_id.trim().toUpperCase() } : {}),
        planned_release: form.planned_release,
        status: form.status,
        risk_score: Number(form.risk_score),
        description: form.description.trim(),
        tasks,
      };
      await onCreateProject(payload);
      setForm(defaultForm);
      setShowCreate(false);
      await refresh();
    } catch (err) {
      setCreateError(err.message || 'Project could not be created.');
    } finally {
      setCreateBusy(false);
    }
  };

  const fieldStyle = {
    width: '100%', padding: '10px 11px', border: '1px solid var(--line)',
    borderRadius: 8, color: 'inherit', background: 'var(--panel)', minWidth: 0,
  };
  const labelStyle = { display: 'grid', gap: 6, fontSize: 12, color: 'var(--muted)' };

  return <div className="page-stack">
    <section className="page-intro-row">
      <div>
        <div className="eyebrow">CROSS-PROJECT INTELLIGENCE</div>
        <h2>Portfolio intelligence</h2>
        <p>Compare delivery risks, find shared resource conflicts, and create projects for Relay to investigate.</p>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="button button-secondary" onClick={refresh} disabled={loading}>{loading ? 'Refreshing…' : '↻ Refresh portfolio'}</button>
        <button className="button button-primary" onClick={() => { setShowCreate(open => !open); setCreateError(''); }}>{showCreate ? 'Cancel' : '+ Add project'}</button>
      </div>
    </section>

    {showCreate && <section className="panel">
      <div className="panel-header"><div><h3>Add a project</h3><p>Create a persistent project record, optional starter tasks, and a brief Relay can retrieve as evidence.</p></div></div>
      <form onSubmit={create} style={{ display: 'grid', gap: 14 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          <label style={labelStyle}>Project name *
            <input style={fieldStyle} value={form.name} onChange={e => setField('name', e.target.value)} required maxLength={255} placeholder="e.g. Customer Portal Modernization"/>
          </label>
          <label style={labelStyle}>Project ID (optional)
            <input style={fieldStyle} value={form.project_id} onChange={e => setField('project_id', e.target.value)} maxLength={64} placeholder="Auto-generated if empty"/>
          </label>
          <label style={labelStyle}>Target release date *
            <input style={fieldStyle} type="date" value={form.planned_release} onChange={e => setField('planned_release', e.target.value)} required/>
          </label>
          <label style={labelStyle}>Initial status
            <select style={fieldStyle} value={form.status} onChange={e => setField('status', e.target.value)}>
              <option>Planning</option><option>On Track</option><option>In Progress</option><option>At Risk</option><option>Delayed</option>
            </select>
          </label>
          <label style={labelStyle}>Initial risk index (0–100)
            <input style={fieldStyle} type="number" min="0" max="100" value={form.risk_score} onChange={e => setField('risk_score', e.target.value)} required/>
          </label>
        </div>
        <label style={labelStyle}>Project brief / context
          <textarea style={{ ...fieldStyle, resize: 'vertical', lineHeight: 1.5 }} rows={4} value={form.description} onChange={e => setField('description', e.target.value)} maxLength={10000} placeholder="Goals, key dates, vendor commitments, dependencies, owners, known risks…"/>
          <small>Stored as a project-brief evidence document. Do not paste confidential secrets.</small>
        </label>
        <label style={labelStyle}>Starter tasks (one task per line, optional)
          <textarea style={{ ...fieldStyle, resize: 'vertical' }} rows={4} value={form.tasks_text} onChange={e => setField('tasks_text', e.target.value)} placeholder={'Requirements confirmation\nAPI integration\nTesting and UAT'}/>
          <small>Each task starts as Planned and Unassigned. You can add real owners and dates later through your data workflows.</small>
        </label>
        {createError && <div className="error-banner"><span>!</span><div>{createError}</div></div>}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button className="button button-primary" type="submit" disabled={createBusy}>{createBusy ? 'Creating project…' : 'Create project'}</button>
          <button className="button button-secondary" type="button" onClick={() => { setShowCreate(false); setCreateError(''); }}>Cancel</button>
        </div>
      </form>
    </section>}

    {error && <div className="error-banner">{error}</div>}
    {data && <>
      <section className="stats-grid">
        <StatCard label="Projects" value={data.count} note="Projects in the workspace database" icon="▥" accent="blue"/>
        <StatCard label="High-risk projects" value={data.summary.high_risk_projects} note="Risk index ≥ 70" icon="⚑" accent="rose"/>
        <StatCard label="At-risk tasks" value={data.summary.risk_tasks} note="Delayed, blocked or at risk" icon="↗" accent="amber"/>
        <StatCard label="Forecast slips" value={data.summary.forecast_slips} note="Forecast later than plan" icon="◷" accent="violet"/>
      </section>
      <section className="panel">
        <div className="panel-header"><div><h3>Project comparison</h3><p>Each row is calculated from stored project and task records.</p></div></div>
        {loading && !data.projects?.length ? <p>Loading portfolio…</p> : <div className="portfolio-list">
          {data.projects.map(p => <button className="portfolio-row" key={p.id} onClick={() => onOpenProject(p.id)}>
            <div className="portfolio-project"><span className="project-avatar-light">{p.name.slice(0, 1)}</span><span><strong>{p.name}</strong><small>{p.id} · Release {p.planned_release}</small></span></div>
            <div className="portfolio-risk"><span>Risk index</span><div className="portfolio-meter"><i style={{ width: `${Math.max(0, Math.min(100, p.risk_score))}%` }}/></div><strong>{p.risk_score}/100</strong></div>
            <div className="portfolio-metric"><span>At-risk tasks</span><strong>{p.risk_task_count}</strong></div>
            <div className="portfolio-metric"><span>Forecast slips</span><strong>{p.forecast_slips}</strong></div>
            <span className="portfolio-status">{p.status}</span>
          </button>)}
        </div>}
      </section>
    </>}
  </div>;
}
