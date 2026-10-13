import React, { useEffect, useState } from 'react';
import { relayApi } from '../api/client';

const EXAMPLE_CHANGE = 'Vendor API delivery moved from October 10 to October 15 (5 days). Integration is blocked until the API arrives. The same integration engineer may also be needed by another project. Compare doing nothing, parallelizing eligible work, and reducing scope; identify downstream impacts and flag any conflicting evidence.';

const outcomeLabels = [
  { value: 'worked', label: 'It worked' },
  { value: 'partially_worked', label: 'Partly worked' },
  { value: 'did_not_work', label: 'Did not work' },
];

function PanelHeading({ title, description, right }) {
  return <div className="panel-header"><div><h3>{title}</h3>{description && <p>{description}</p>}</div>{right}</div>;
}

export default function RippleIntelligencePage({ project, language = 'English' }) {
  const [changeText, setChangeText] = useState(EXAMPLE_CHANGE);
  const [source, setSource] = useState('vendor_email');
  const [assumedDelayDays, setAssumedDelayDays] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [savingOutcome, setSavingOutcome] = useState('');

  const refreshHistory = async (projectId = project?.id) => {
    if (!projectId) return;
    setHistoryLoading(true);
    setHistoryError('');
    try {
      const response = await relayApi.getRippleHistory(projectId, 10);
      setHistory(response.records || []);
    } catch (err) {
      setHistoryError(err.message || 'Could not load outcome history.');
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    setResult(null);
    refreshHistory(project?.id);
  }, [project?.id]);

  const runAnalysis = async event => {
    event?.preventDefault();
    if (!project?.id || changeText.trim().length < 10) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await relayApi.runRippleAnalysis({
        project_id: project.id,
        change_text: changeText.trim(),
        source,
        language,
        assumed_delay_days: Number(assumedDelayDays) || 0,
      });
      setResult(response);
      // The analysis is ready; refresh history independently so it does not keep
      // the main Analyze button in its loading state.
      void refreshHistory(project.id);
    } catch (err) {
      setError(err.message || 'Ripple analysis failed. No actions were executed.');
    } finally {
      setLoading(false);
    }
  };

  const saveOutcome = async (recordId, status) => {
    setSavingOutcome(recordId + ':' + status);
    setError('');
    try {
      const response = await relayApi.recordRippleOutcome(recordId, {
        status,
        notes: '',
      });
      setResult(current => current?.record_id === recordId
        ? { ...current, outcome_status: response.outcome_status }
        : current);
      await refreshHistory(project?.id);
    } catch (err) {
      setError(err.message || 'Could not save outcome feedback.');
    } finally {
      setSavingOutcome('');
    }
  };

  const analysis = result?.analysis;
  const simulation = result?.simulation;
  const cardStyle = { border: '1px solid var(--line)', borderRadius: 12, padding: 14, background: 'var(--panel)', minWidth: 0 };
  const statStyle = { fontSize: 12, color: 'var(--muted)', display: 'block', marginBottom: 5 };

  return <div className="page-stack">
    <section className="page-intro-row">
      <div>
        <div className="eyebrow">PROACTIVE ORGANIZATIONAL FORESIGHT</div>
        <h2>Ripple Intelligence</h2>
        <p>Turn a small change into a traceable impact map, compare possible futures, and record what worked.</p>
      </div>
      <span className="model-pill">Evidence · Impact · What-if</span>
    </section>

    <section className="panel">
      <PanelHeading title="Change Radar" description="Paste a vendor update, meeting decision, requirement change, or operational signal. Relay checks it against project records and available evidence." right={project ? <span className="count-pill">{project.id}</span> : null}/>
      {!project ? <div className="empty-state"><p>Select a project to investigate a change.</p></div> : <form onSubmit={runAnalysis} style={{ display: 'grid', gap: 14 }}>
        <label style={{ display: 'grid', gap: 7 }}>
          <span style={{ fontSize: 13, fontWeight: 700 }}>Change or new signal</span>
          <textarea value={changeText} onChange={e => setChangeText(e.target.value)} rows={5} maxLength={6000} required minLength={10} placeholder="Paste the new email, meeting decision, or change notification…"
            style={{ width: '100%', resize: 'vertical', padding: 12, border: '1px solid var(--line)', borderRadius: 10, background: 'var(--panel)', color: 'inherit', lineHeight: 1.5 }}/>
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>Signal source</span>
            <select value={source} onChange={e => setSource(e.target.value)} style={{ padding: 10, border: '1px solid var(--line)', borderRadius: 8, background: 'var(--panel)', color: 'inherit' }}>
              <option value="vendor_email">Vendor email</option>
              <option value="meeting_notes">Meeting notes</option>
              <option value="requirement_change">Requirement change</option>
              <option value="project_update">Project update</option>
              <option value="manual">Manual signal</option>
            </select>
          </label>
          <label style={{ display: 'grid', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>What-if delay assumption (days)</span>
            <input type="number" min="0" max="365" value={assumedDelayDays} onChange={e => setAssumedDelayDays(e.target.value)} style={{ padding: 10, border: '1px solid var(--line)', borderRadius: 8, background: 'var(--panel)', color: 'inherit' }}/>
          </label>
        </div>
        <div style={{ display: 'flex', gap: 9, flexWrap: 'wrap', alignItems: 'center' }}>
          <button className="button button-primary" type="submit" disabled={loading || changeText.trim().length < 10}>{loading ? 'Investigating impact…' : '✦ Analyze ripple effect'}</button>
          <button className="button button-secondary" type="button" onClick={() => setChangeText(EXAMPLE_CHANGE)} disabled={loading}>Load demo signal</button>
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>No external actions run automatically.</span>
        </div>
      </form>}
    </section>

    {error && <div className="error-banner"><span>!</span><div><strong>Analysis needs attention</strong><p>{error}</p></div><button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
    {loading && <section className="panel"><div style={{ display: 'flex', gap: 12, alignItems: 'center' }}><span className="live-dot"/><div><strong>Tracing the ripple effect…</strong><p style={{ margin: '5px 0 0', color: 'var(--muted)' }}>Checking evidence, project dependencies, resource overlap, contradictions, and scenario assumptions.</p></div></div></section>}

    {result && analysis && <>
      <section className="panel">
        <PanelHeading title="Signal interpretation" description={analysis.executive_summary} right={<span className={analysis.urgency === 'critical' || analysis.urgency === 'high' ? 'status-badge status-warning' : 'status-badge status-info'}>{analysis.urgency || 'medium'} urgency</span>}/>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
          <div style={cardStyle}><span style={statStyle}>Change type</span><strong>{analysis.event_type || 'Not classified'}</strong></div>
          <div style={cardStyle}><span style={statStyle}>Changed entity</span><strong>{analysis.changed_entity || 'Not identified'}</strong></div>
          <div style={cardStyle}><span style={statStyle}>Previous state</span><strong>{analysis.previous_state || 'Not specified'}</strong></div>
          <div style={cardStyle}><span style={statStyle}>New state</span><strong>{analysis.new_state || 'Not specified'}</strong></div>
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 0 }}>Model: {result.model || 'Gemini'}{result.fallback_used ? ' · fallback model used' : ''} · Retrieval: {result.retrieval_mode || 'not reported'} · {result.evidence?.length || 0} evidence items</p>
      </section>

      <section className="panel">
        <PanelHeading title="Cross-project ripple" description="Projects Gemini identified from the portfolio and dependency/resource heuristics." right={<span className="count-pill">{result.impacted_projects?.length || 0} projects</span>}/>
        {(result.impacted_projects || []).length ? <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
          {result.impacted_projects.map(item => <article key={item.id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'start' }}><strong>{item.name}</strong><span className="count-pill">{item.id}</span></div>
            <p style={{ color: 'var(--muted)', fontSize: 13, margin: '8px 0' }}>{item.status} · Release {item.planned_release || 'not set'}</p>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12 }}><span>Risk index <b>{item.risk_score}/100</b></span><span>At-risk tasks <b>{item.at_risk_task_count}</b></span></div>
            {item.shared_resources?.length > 0 && <p style={{ fontSize: 12, marginBottom: 0 }}>Shared resources: {item.shared_resources.join(', ')}</p>}
          </article>)}
        </div> : <p>No downstream project could be verified from the current portfolio.</p>}
      </section>

      <section className="panel">
        <PanelHeading title="Contradiction & trust check" description="A change is not automatically a contradiction. Unsupported source conflicts are marked unverified."/>
        {(analysis.contradictions || []).length ? <div style={{ display: 'grid', gap: 10 }}>
          {analysis.contradictions.map((item, index) => <article key={index} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'start' }}><strong>{item.title}</strong><span className={item.severity === 'high' ? 'status-badge status-warning' : 'status-badge status-neutral'}>{item.severity}</span></div>
            <p>{item.description}</p>
            <small style={{ color: 'var(--muted)' }}>Source refs: {item.source_refs?.length ? item.source_refs.join(', ') : 'No verified document reference'}</small>
          </article>)}
        </div> : <div className="empty-state"><p>No explicit contradiction was confirmed from retrieved evidence. Relay will not invent one.</p></div>}
        {result.evidence?.length > 0 && <div style={{ marginTop: 14 }}><h4>Retrieved evidence</h4><div style={{ display: 'grid', gap: 8 }}>{result.evidence.map((item, i) => <div key={item.chunk_id || item.document_id || i} style={{ padding: 10, border: '1px solid var(--line)', borderRadius: 8 }}><strong>{item.title || item.document_id}</strong><p style={{ fontSize: 13, margin: '4px 0' }}>{item.content}</p><small style={{ color: 'var(--muted)' }}>{item.source || 'Source unknown'} · {item.document_id || ''}</small></div>)}</div></div>}
      </section>

      <section className="panel">
        <PanelHeading title="Recommended interventions" description="Suggestions remain proposals; use Recovery Actions to request approval before execution."/>
        {(analysis.recommended_actions || []).length ? <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
          {analysis.recommended_actions.map((item, index) => <article key={index} style={cardStyle}><div className="eyebrow">OPTION 0{index + 1}</div><h4>{item.title}</h4><p>{item.rationale}</p>{item.tradeoffs?.length > 0 && <><strong style={{ fontSize: 12 }}>Trade-offs</strong><ul>{item.tradeoffs.map((tradeoff, j) => <li key={j}>{tradeoff}</li>)}</ul></>}</article>)}
        </div> : <p>No intervention could be recommended from available evidence.</p>}
      </section>

      {simulation && <section className="panel">
        <PanelHeading title="What-if decision simulator" description="Rule-based estimates compare scenarios. They are not calibrated predictions or probabilities." right={<span className="count-pill">{simulation.assumed_event_delay_days} day(s) modeled</span>}/>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 12 }}>
          {(simulation.scenarios || []).map((item, index) => <article key={item.name} style={{ ...cardStyle, borderColor: index === 0 ? 'var(--line)' : 'var(--blue)' }}>
            <div className="eyebrow">SCENARIO 0{index + 1}</div><h4>{item.name}</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, margin: '12px 0' }}>
              <div><span style={statStyle}>Estimated release</span><strong>{item.estimated_release_date}</strong></div>
              <div><span style={statStyle}>Projected slip</span><strong>{item.projected_slip_days} days</strong></div>
              <div><span style={statStyle}>Risk index</span><strong>{item.risk_index}/100</strong></div>
              <div><span style={statStyle}>Residual event delay</span><strong>{item.remaining_event_delay_days} days</strong></div>
            </div>
            <p>{item.tradeoff}</p>
            <ul>{(item.assumptions || []).map((a, i) => <li key={i}>{a}</li>)}</ul>
          </article>)}
        </div>
        <div style={{ marginTop: 12, padding: 12, background: 'var(--panel)', borderRadius: 10, border: '1px dashed var(--line)' }}><strong>Simulation assumptions</strong><ul>{(simulation.assumptions || []).map((a, i) => <li key={i}>{a}</li>)}</ul></div>
      </section>}

      <section className="panel">
        <PanelHeading title="Outcome feedback" description="Record whether a prior intervention worked. Relay keeps the feedback with this investigation for later review."/>
        {result.outcome_status ? <p>Outcome recorded: <strong>{result.outcome_status.replaceAll('_', ' ')}</strong></p> : <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>{outcomeLabels.map(item => <button key={item.value} className={item.value === 'worked' ? 'button button-primary' : 'button button-secondary'} type="button" disabled={Boolean(savingOutcome)} onClick={() => saveOutcome(result.record_id, item.value)}>{savingOutcome === result.record_id + ':' + item.value ? 'Saving…' : item.label}</button>)}</div>}
      </section>

      {(analysis.assumptions?.length > 0 || analysis.missing_information?.length > 0) && <section className="panel" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}><div><h3>Assumptions</h3><ul>{analysis.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul></div><div><h3>Missing information</h3><ul>{analysis.missing_information.map((item, index) => <li key={index}>{item}</li>)}</ul></div></section>}
    </>}

    <section className="panel">
      <PanelHeading title="Investigation & outcome history" description="Prior change signals and human feedback for this project." right={<button className="button button-secondary button-small" type="button" onClick={() => refreshHistory()} disabled={historyLoading}>{historyLoading ? 'Refreshing…' : '↻ Refresh'}</button>}/>
      {historyError && <div className="error-banner">{historyError}</div>}
      {historyLoading && !history.length ? <p>Loading history…</p> : history.length ? <div style={{ display: 'grid', gap: 10 }}>{history.map(item => <article key={item.record_id} style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'start', flexWrap: 'wrap' }}><strong>{item.title || 'Change investigation'}</strong><span className="count-pill">{item.created_at ? new Date(item.created_at).toLocaleString() : item.record_id}</span></div>
        <p>{item.summary}</p><div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}><small style={{ color: 'var(--muted)' }}>{item.record_id}</small>{item.outcome_status ? <span className="status-badge status-success">Outcome: {item.outcome_status.replaceAll('_', ' ')}</span> : <span className="status-badge status-neutral">Awaiting outcome</span>}</div>
        {!item.outcome_status && <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 10 }}>{outcomeLabels.map(outcome => <button key={outcome.value} className="button button-secondary button-small" type="button" disabled={Boolean(savingOutcome)} onClick={() => saveOutcome(item.record_id, outcome.value)}>{outcome.label}</button>)}</div>}
      </article>)}</div> : <div className="empty-state"><p>No Ripple investigations have been saved yet. Run a change analysis to start the history.</p></div>}
    </section>
  </div>;
}
