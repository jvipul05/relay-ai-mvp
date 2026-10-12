import React from 'react';
import StatCard from '../components/StatCard';
import StatusBadge from '../components/StatusBadge';

function shortDate(value) {
  if (!value) return 'Date not set';
  const parsed = new Date(`${value}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(parsed);
}

export default function OverviewPage({ project, investigation, onNavigate, onRunAi, aiLoading }) {
  const tasks = project?.tasks || [];
  const riskScore = project?.current_risk_score ?? project?.risk_score;
  const riskRingDegrees = Math.min(100, Math.max(0, Number(riskScore) || 0)) * 3.6;
  const atRiskTasks = tasks.filter(task => ['at risk', 'delayed', 'blocked'].includes(String(task.status).toLowerCase()));
  const delayedTasks = tasks.filter(task => task.forecast_date && task.planned_date && task.forecast_date > task.planned_date);
  const release = shortDate(project?.planned_release);
  const focusTasks = (atRiskTasks.length ? atRiskTasks : tasks).slice(0, 4);
  const nextMove = investigation?.recommended_next_step ||
    (tasks.some(task => String(task.status).toLowerCase() === 'blocked')
      ? 'Start with the blocked task and confirm what needs to change to unblock it.'
      : 'Run an AI investigation to identify the most useful next step.');
  const summary = investigation?.summary ||
    'Relay brings together delivery status, dependencies, and supporting evidence to help the team decide what to do next.';

  return (
    <div className="page-stack mission-page">
      <section className="mission-hero">
        <div className="mission-hero-copy">
          <div className="mission-kicker"><span className="mission-kicker-mark">✦</span> YOUR PROJECT BRIEF <span className="mission-kicker-divider">/</span> {project?.is_synthetic ? "SYNTHETIC DEMO DATA" : "CONNECTED PROJECT DATA"}</div>
          <div className="mission-project-line">
            <span className="mission-project-avatar">{project?.name?.slice(0, 1) || 'P'}</span>
            <div><span className="mission-project-id">{project?.id || 'PROJECT'}</span><h2>{project?.name || 'Your project'}</h2></div>
            <StatusBadge status={project?.status || 'Unknown'}/>
          </div>
          <h1>Make the next move <span>with confidence.</span></h1>
          <p className="mission-hero-description">Spot delivery risk, understand what is causing it, and turn the findings into a clear recovery plan.</p>
          <div className="mission-hero-actions">
            <button className="button button-primary" type="button" onClick={onRunAi} disabled={aiLoading}>
              {aiLoading ? <><span className="button-spinner"/> Analysing project…</> : <><span>✧</span> Investigate project risk <span className="mission-button-arrow">→</span></>}
            </button>
            <button className="button mission-button-quiet" type="button" onClick={() => onNavigate('dependencies')}>Explore dependencies</button>
          </div>
          <div className="mission-hero-meta">
            <span><small>PLANNED RELEASE</small><strong>{release}</strong></span>
            <span><small>DELIVERY STATUS</small><strong>{project?.status || 'Not available'}</strong></span>
          </div>
        </div>

        <aside className="mission-signal-card">
          <div className="mission-signal-top"><span className="mission-signal-dot"/> RELAY SIGNAL</div>
          <div className="mission-risk-visual">
            <div className="mission-risk-ring" style={{ background: `conic-gradient(#ef8b7b 0deg ${riskRingDegrees}deg, #445576 ${riskRingDegrees}deg 360deg)` }}><span><strong>{riskScore ?? '—'}</strong><small>/100 risk</small></span></div>
            <div><span className="mission-risk-label">Delivery risk</span><strong className="mission-risk-state">{Number(riskScore) >= 70 ? 'Needs attention' : Number(riskScore) >= 40 ? 'Keep watching' : 'In good shape'}</strong><small className="mission-risk-help">Illustrative demo score</small></div>
          </div>
          <div className="mission-risk-track"><span style={{ width: `${Math.max(0, Math.min(100, Number(riskScore) || 0))}%` }}/></div>
          <div className="mission-signal-foot"><span>{atRiskTasks.length} priority tasks</span><span>{delayedTasks.length} forecast slips</span></div>
          <div className="mission-signal-divider"/>
          <div className="mission-signal-insight">
            <span className="mission-insight-icon">✧</span>
            <div><small>NEXT BEST MOVE</small><p>{nextMove}</p></div>
          </div>
        </aside>
      </section>

      <section className="mission-stats-grid" aria-label="Project snapshot">
        <StatCard label="Tasks needing attention" value={atRiskTasks.length} note={`Out of ${tasks.length} tracked tasks`} icon="⚑" accent="amber"/>
        <StatCard label="Forecast slips" value={delayedTasks.length} note="Forecast later than plan" icon="↗" accent="rose"/>
        <StatCard label="Root causes found" value={investigation?.root_causes?.length || 0} note={investigation ? 'From the latest assessment' : 'Run an investigation to explore'} icon="✧" accent="violet"/>
        <StatCard label="Release target" value={release} note="Current planned release" icon="◷" accent="blue"/>
      </section>

      <section className="mission-workflow-section">
        <div className="mission-section-heading"><div><span className="eyebrow">FROM SIGNAL TO OUTCOME</span><h3>A clear path forward</h3><p>Follow the same simple loop from discovery to verified action.</p></div></div>
        <div className="mission-workflow">
          <button type="button" className="mission-step" onClick={() => onNavigate('portfolio')}><span className="mission-step-number">01</span><span className="mission-step-icon">⌂</span><span className="mission-step-copy"><strong>Understand</strong><small>See the bigger picture</small></span><span className="mission-step-arrow">↗</span></button>
          <button type="button" className="mission-step" onClick={() => onNavigate('investigation')}><span className="mission-step-number">02</span><span className="mission-step-icon">✧</span><span className="mission-step-copy"><strong>Investigate</strong><small>Find causes and evidence</small></span><span className="mission-step-arrow">↗</span></button>
          <button type="button" className="mission-step" onClick={() => onNavigate('actions')}><span className="mission-step-number">03</span><span className="mission-step-icon">✓</span><span className="mission-step-copy"><strong>Take action</strong><small>Review a recovery plan</small></span><span className="mission-step-arrow">↗</span></button>
          <button type="button" className="mission-step" onClick={() => onNavigate('actions')}><span className="mission-step-number">04</span><span className="mission-step-icon">◎</span><span className="mission-step-copy"><strong>Verify</strong><small>Check what changed</small></span><span className="mission-step-arrow">↗</span></button>
        </div>
      </section>

      <section className="mission-lower-grid">
        <div className="panel mission-focus-panel">
          <div className="panel-header"><div><h3>Where attention is needed</h3><p>{atRiskTasks.length ? 'The highest-priority delivery items in this project.' : 'A short list of the project’s delivery checkpoints.'}</p></div><button className="text-button" type="button" onClick={() => onNavigate('dependencies')}>See dependencies <span>→</span></button></div>
          {focusTasks.length ? <div className="mission-focus-list">
            {focusTasks.map((task, index) => <article className="mission-focus-task" key={task.id || `${task.name}-${index}`}>
              <div className={`mission-task-index ${['blocked', 'delayed', 'at risk'].includes(String(task.status).toLowerCase()) ? 'needs-attention' : ''}`}>{String(index + 1).padStart(2, '0')}</div>
              <div className="mission-task-main"><div className="mission-task-heading"><strong>{task.name}</strong><StatusBadge status={task.status || 'Unknown'}/></div><span>{task.id || 'Project task'} · {task.owner || 'Owner not assigned'}</span><small>{task.blocked_by?.length ? `Waiting on ${task.blocked_by.join(', ')}` : task.forecast_date && task.planned_date && task.forecast_date > task.planned_date ? `Forecast ${shortDate(task.forecast_date)} · planned ${shortDate(task.planned_date)}` : `Planned ${shortDate(task.planned_date)}`}</small></div>
              <span className="mission-task-chevron" aria-hidden="true">→</span>
            </article>)}
          </div> : <div className="mission-no-tasks"><span>✓</span><strong>No delivery tasks found</strong><p>Add project tasks to see delivery risk and dependencies here.</p></div>}
          <div className="mission-focus-footer"><span><span className="mission-footer-dot"/> Priority-first view</span><button className="text-button" type="button" onClick={() => onNavigate('investigation')}>Open full investigation <span>→</span></button></div>
        </div>

        <aside className="panel mission-next-panel">
          <div className="mission-next-header"><span className="mission-next-sparkle">✧</span><span><small>RELAY RECOMMENDS</small><strong>Your next best move</strong></span></div>
          <p className="mission-next-summary">{summary}</p>
          <div className="mission-next-action"><span>01</span><div><small>START HERE</small><p>{nextMove}</p></div></div>
          <button className="button button-primary mission-next-button" type="button" onClick={onRunAi} disabled={aiLoading}>{aiLoading ? 'Analysing…' : 'Generate an AI investigation →'}</button>
          <p className="mission-next-note"><span>ⓘ</span> Recommendations use available project context. Verify important findings with the source owner.</p>
        </aside>
      </section>
    </div>
  );
}
