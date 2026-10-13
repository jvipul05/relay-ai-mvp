import React, { useEffect, useState } from 'react';

const DEFAULT_KEYWORDS = ['Project Alpha', 'delayed', 'blocked', 'delivery date', 'release', 'project risk'];

export default function EmailSyncPage({ project, status, loadingStatus, onRefreshStatus, onConnect, onSaveConfig, onRunSync, onDisconnect, busy, syncResult, configResult }) {
  const [keywordsText, setKeywordsText] = useState(DEFAULT_KEYWORDS.join('\n'));
  const [intervalMinutes, setIntervalMinutes] = useState(15);
  const [enabled, setEnabled] = useState(false);
  const [localMessage, setLocalMessage] = useState('');

  useEffect(() => {
    if (!status) return;
    setKeywordsText((status.keywords?.length ? status.keywords : DEFAULT_KEYWORDS).join('\n'));
    setIntervalMinutes(status.interval_minutes || 15);
    setEnabled(Boolean(status.enabled));
  }, [status?.project_id, status?.keywords, status?.interval_minutes, status?.enabled]);

  const save = async (event) => {
    event.preventDefault();
    setLocalMessage('');
    const keywords = [...new Set(keywordsText.split(/\n|,/).map(x => x.trim()).filter(Boolean))];
    if (!keywords.length) {
      setLocalMessage('Add at least one keyword before saving.');
      return;
    }
    if (keywords.length > 20) {
      setLocalMessage('Use no more than 20 keywords.');
      return;
    }
    await onSaveConfig({ keywords, interval_minutes: Number(intervalMinutes), enabled });
  };

  return <div className="page-stack">
    <section className="page-intro-row">
      <div><div className="eyebrow">PROJECT INTEGRATIONS</div><h2>Email ingestion</h2>
        <p>Connect Gmail, configure which emails matter to this project, and run a manual sync. Settings are scoped to the selected project.</p>
      </div>
      <button className="button button-secondary" onClick={onRefreshStatus} disabled={loadingStatus || busy}>{loadingStatus ? 'Refreshing…' : '↻ Refresh status'}</button>
    </section>

    {status?.disabled && <div className="execution-disclaimer" role="status"><span>ⓘ</span><p>{status.message || "Gmail is disabled in this public demo."} The rest of the workspace uses synthetic demonstration data.</p></div>}

    <section className="panel">
      <div className="panel-header"><div><h3>Gmail connection</h3><p>Read-only access to the selected mailbox</p></div>
        <span className={`status-badge ${status?.connected ? 'status-success' : 'status-warning'}`}><span className="status-dot"/>{status?.connected ? 'Connected' : 'Not connected'}</span>
      </div>
      <div className="email-settings-content">
        <div className="email-account-row">
          <div className="email-account-icon">G</div>
          <div className="email-account-meta"><strong>{status?.email_address || 'No Gmail account connected'}</strong><small>Active project: {project?.name || project?.id || 'Select a project'}</small></div>
          <div className="email-account-actions">
            <button className="button button-primary" onClick={onConnect} disabled={Boolean(status?.disabled) || busy || !project?.id}>{busy ? 'Please wait…' : status?.connected ? 'Reconnect Gmail' : 'Login with Google'}</button>
            {status?.connected && <button className="button button-secondary" onClick={onDisconnect} disabled={busy}>Disconnect</button>}
          </div>
        </div>
        {status?.last_sync_at && <div className="email-sync-meta"><span>Last sync</span><strong>{new Date(status.last_sync_at).toLocaleString()}</strong></div>}
        {status?.last_error && <div className="form-error">Last sync error: {status.last_error}</div>}
        <p className="email-help">Login opens Google's authorization page in a new tab. After granting read-only access, return here and refresh status.</p>
      </div>
    </section>

    <section className="panel">
      <div className="panel-header"><div><h3>Project email configuration</h3><p>Keywords determine which emails are selected for this project.</p></div></div>
      <form className="email-config-form" onSubmit={save}>
        <label>Keywords <span className="field-hint">One per line or comma-separated · up to 20</span>
          <textarea rows={6} value={keywordsText} onChange={e => setKeywordsText(e.target.value)} placeholder={'Project Alpha\ndelayed\nblocked\nrelease'} disabled={Boolean(status?.disabled) || !status?.connected || busy}/>
        </label>
        <div className="email-config-row">
          <label>Scheduled sync interval
            <select value={intervalMinutes} onChange={e => setIntervalMinutes(Number(e.target.value))} disabled={Boolean(status?.disabled) || !status?.connected || busy}>
              <option value={15}>Every 15 minutes</option><option value={30}>Every 30 minutes</option><option value={60}>Every hour</option><option value={360}>Every 6 hours</option><option value={720}>Every 12 hours</option><option value={1440}>Daily</option>
            </select>
          </label>
          <label className="email-enabled-toggle"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} disabled={Boolean(status?.disabled) || !status?.connected || busy}/> Enable scheduled sync</label>
        </div>
        <div className="form-footer"><span>Saved configuration applies only to {project?.name || 'the selected project'}.</span><button className="button button-primary" type="submit" disabled={Boolean(status?.disabled) || !status?.connected || busy}>{busy ? 'Saving…' : 'Save configuration'}</button></div>
        {localMessage && <p className="form-error">{localMessage}</p>}
        {configResult && <p className="email-success">{configResult.message || 'Configuration saved.'}</p>}
      </form>
    </section>

    <section className="panel">
      <div className="panel-header"><div><h3>Manual sync</h3><p>Fetch matching messages now, without waiting for the schedule.</p></div><button className="button button-primary" onClick={onRunSync} disabled={Boolean(status?.disabled) || !status?.connected || busy}>{busy ? 'Syncing…' : '↻ Run sync now'}</button></div>
      {syncResult ? <div className="sync-result-grid">
        <div><span>Matched</span><strong>{syncResult.messages_matched ?? '—'}</strong></div>
        <div><span>Ingested</span><strong>{syncResult.messages_ingested ?? '—'}</strong></div>
        <div><span>Skipped</span><strong>{syncResult.messages_skipped ?? '—'}</strong></div>
        <div><span>Failures</span><strong>{syncResult.failures?.length ?? 0}</strong></div>
      </div> : <div className="email-empty-note">After a sync, the result summary will appear here. Existing emails may be rechecked; the backend should deduplicate using Gmail message IDs.</div>}
      {syncResult?.failures?.length > 0 && <div className="email-failures"><strong>Sync failures</strong><ul>{syncResult.failures.map((failure, i) => <li key={i}>{typeof failure === 'string' ? failure : JSON.stringify(failure)}</li>)}</ul></div>}
    </section>
  </div>;
}
