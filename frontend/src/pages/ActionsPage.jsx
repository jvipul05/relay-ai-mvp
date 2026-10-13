import React, { useState } from 'react';
import { relayApi } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import EmptyState from '../components/EmptyState';

export default function ActionsPage({ project, actions, onCreate, onApprove, onExecute, onVerify, busyActionId }) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [formError, setFormError] = useState('');
  const [auditState, setAuditState] = useState({});

  async function submit(event) {
    event.preventDefault();
    setFormError('');
    if (!title.trim() || !description.trim()) {
      setFormError('Enter both a title and description.');
      return;
    }
    try {
      await onCreate({ title: title.trim(), description: description.trim() });
      setTitle('');
      setDescription('');
      setShowForm(false);
    } catch (error) {
      setFormError(error.message);
    }
  }

  async function toggleAudit(actionId) {
    const current = auditState[actionId];
    if (current?.events) {
      setAuditState(previous => ({
        ...previous,
        [actionId]: { ...previous[actionId], expanded: !previous[actionId]?.expanded },
      }));
      return;
    }
    setAuditState(previous => ({ ...previous, [actionId]: { loading: true, expanded: true, events: [], error: '' } }));
    try {
      const response = await relayApi.getAudit(project?.id || project?.project_id, actionId);
      setAuditState(previous => ({
        ...previous,
        [actionId]: { loading: false, expanded: true, events: response.events || [], error: '' },
      }));
    } catch (error) {
      setAuditState(previous => ({
        ...previous,
        [actionId]: { loading: false, expanded: true, events: [], error: error.message || 'Could not load audit history.' },
      }));
    }
  }

  return <div className="page-stack">
    <section className="page-intro-row">
      <div><div className="eyebrow">CONTROLLED EXECUTION</div><h2>Recovery action center</h2><p>Recommendations become tracked work only after approval. Current execution is simulated.</p></div>
      <button className="button button-primary" onClick={() => setShowForm(value => !value)}>{showForm ? 'Cancel' : '+ Create action'}</button>
    </section>
    {showForm && <section className="panel"><div className="panel-header"><div><h3>Propose a recovery action</h3><p>For {project?.name || 'the selected project'}</p></div></div>
      <form className="action-form" onSubmit={submit}>
        <label>Action title<input value={title} onChange={event => setTitle(event.target.value)} placeholder="e.g. Confirm revised vendor delivery date" maxLength={255}/></label>
        <label>Description<textarea value={description} onChange={event => setDescription(event.target.value)} placeholder="Describe the intended action and expected outcome…" rows={3}/></label>
        {formError && <p className="form-error">{formError}</p>}
        <div className="form-footer"><span>New actions start in Pending approval.</span><button className="button button-primary" type="submit">Save for approval</button></div>
      </form>
    </section>}
    <div className="action-summary-grid">
      <div className="action-summary"><span>Total actions</span><strong>{actions.length}</strong></div>
      <div className="action-summary"><span>Awaiting approval</span><strong>{actions.filter(action => action.status === 'pending_approval').length}</strong></div>
      <div className="action-summary"><span>Executed</span><strong>{actions.filter(action => ['executed', 'verified'].includes(action.status)).length}</strong></div>
      <div className="action-summary"><span>Verified</span><strong>{actions.filter(action => action.status === 'verified').length}</strong></div>
    </div>
    {!actions.length ? <section className="panel"><EmptyState title="No recovery actions yet" description="Create a proposed action, approve it, and walk through the simulated execution and verification lifecycle." action="Create first action" onAction={() => setShowForm(true)}/></section> : <section className="action-list">
      {actions.map(action => {
        const audit = auditState[action.id];
        return <article className="panel action-card" key={action.id}>
          <div className="action-card-top"><div className="action-title-wrap"><div className="action-icon">↗</div><div><div className="action-id">{action.id}</div><h3>{action.title}</h3></div></div><StatusBadge status={action.status}/></div>
          <p className="action-description">{action.description}</p>
          {action.execution_result && <div className="result-note"><strong>Execution result</strong><p>{action.execution_result}</p></div>}
          {action.verification_result && <div className="result-note verified-note"><strong>Verification result</strong><p>{action.verification_result}</p></div>}
          <div className="action-card-footer"><span className="action-created">Created {action.created_at ? new Date(action.created_at).toLocaleString() : 'recently'}</span>
            <div className="action-controls">
              {action.status === 'pending_approval' && <button className="button button-secondary" disabled={busyActionId === action.id} onClick={() => onApprove(action.id)}>Approve</button>}
              {action.status === 'approved' && <button className="button button-primary" disabled={busyActionId === action.id} onClick={() => onExecute(action.id)}>Execute simulation</button>}
              {action.status === 'executed' && <button className="button button-primary" disabled={busyActionId === action.id} onClick={() => onVerify(action.id)}>Verify result</button>}
              {action.status === 'verified' && <span className="verified-label">✓ Verified</span>}
              {busyActionId === action.id && <span className="muted">Working…</span>}
              <button className="button button-secondary button-small" type="button" disabled={(!project?.id && !project?.project_id) || audit?.loading} onClick={() => toggleAudit(action.id)}>{audit?.loading ? 'Loading audit…' : audit?.expanded ? 'Hide audit trail' : 'View audit trail'}</button>
            </div>
          </div>
          {audit?.expanded && <div className="result-note" style={{ marginTop: 12 }}>
            <strong>Audit trail</strong>
            {audit.error && <p className="form-error">{audit.error}</p>}
            {audit.loading && <p>Loading events…</p>}
            {!audit.loading && !audit.error && audit.events.length === 0 && <p>No audit events recorded yet.</p>}
            {!audit.loading && !audit.error && audit.events.length > 0 && <ol style={{ marginBottom: 0, paddingLeft: 22 }}>
              {audit.events.map(event => <li key={event.id} style={{ marginBottom: 8 }}><strong>{String(event.event_type || 'event').replaceAll('_', ' ')}</strong>{' · '}{event.actor || 'Unknown actor'}<small style={{ display: 'block', color: 'var(--muted)' }}>{event.created_at ? new Date(event.created_at).toLocaleString() : 'Time not recorded'}</small>{event.details && <p style={{ margin: '4px 0' }}>{event.details}</p>}</li>)}
            </ol>}
          </div>}
        </article>;
      })}
    </section>}
    <div className="execution-disclaimer"><span>ⓘ</span><p><strong>Safe demo mode.</strong> Execute runs a simulation only. No email, project system or external service is modified.</p></div>
  </div>;
}
