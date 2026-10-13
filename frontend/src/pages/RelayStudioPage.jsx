import React, { useState } from 'react';
import { relayApi } from '../api/client';

const DESTINATIONS = [
  { value: 'auto', label: 'Auto-route with Relay', description: 'Classify the content and recommend the best destination.' },
  { value: 'jira', label: 'Jira issue', description: 'Create a review-ready issue payload.' },
  { value: 'confluence', label: 'Confluence page', description: 'Format knowledge as a structured page.' },
  { value: 'slack', label: 'Slack summary', description: 'Create a concise message and action list.' },
];

const DEFAULT_SCHEMA = {
  type: 'object',
  properties: {
    detected_type: { type: 'string', enum: ['code', 'log', 'meeting_notes', 'project_update', 'incident', 'support_request', 'other'] },
    recommended_destination: { type: 'string', enum: ['jira', 'confluence', 'slack', 'manual_review'] },
    title: { type: 'string' },
    summary: { type: 'string' },
    structured_payload: { type: 'object', properties: {}, additionalProperties: true },
    action_items: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, owner: { type: 'string' }, due_date: { type: 'string' },
      priority: { type: 'string', enum: ['Highest', 'High', 'Medium', 'Low', 'Not specified'] },
    }, required: ['title', 'owner', 'due_date', 'priority'], additionalProperties: false } },
    assumptions: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['detected_type', 'recommended_destination', 'title', 'summary', 'structured_payload', 'action_items', 'assumptions', 'open_questions'],
  additionalProperties: false,
};

const TEMPLATE_SCHEMAS = {
  auto: DEFAULT_SCHEMA,
  jira: {
    type: 'object',
    properties: {
      issue_type: { type: 'string', enum: ['Bug', 'Task', 'Story', 'Incident'] },
      summary: { type: 'string' },
      description: { type: 'string' },
      priority: { type: 'string', enum: ['Highest', 'High', 'Medium', 'Low', 'Lowest'] },
      labels: { type: 'array', items: { type: 'string' } },
      acceptance_criteria: { type: 'array', items: { type: 'string' } },
      action_items: DEFAULT_SCHEMA.properties.action_items,
      assumptions: { type: 'array', items: { type: 'string' } },
    },
    required: ['issue_type', 'summary', 'description', 'priority', 'labels', 'acceptance_criteria', 'action_items', 'assumptions'],
    additionalProperties: false,
  },
  confluence: {
    type: 'object',
    properties: {
      title: { type: 'string' }, summary: { type: 'string' },
      sections: { type: 'array', items: { type: 'object', properties: { heading: { type: 'string' }, body: { type: 'string' } }, required: ['heading', 'body'], additionalProperties: false } },
      decisions: { type: 'array', items: { type: 'string' } },
      action_items: DEFAULT_SCHEMA.properties.action_items,
      assumptions: { type: 'array', items: { type: 'string' } },
    },
    required: ['title', 'summary', 'sections', 'decisions', 'action_items', 'assumptions'],
    additionalProperties: false,
  },
  slack: {
    type: 'object',
    properties: {
      channel_message: { type: 'string' },
      key_points: { type: 'array', items: { type: 'string' } },
      action_items: DEFAULT_SCHEMA.properties.action_items,
      open_questions: { type: 'array', items: { type: 'string' } },
    },
    required: ['channel_message', 'key_points', 'action_items', 'open_questions'],
    additionalProperties: false,
  },
};

function downloadJson(value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'relay-structured-output.json';
  link.click();
  URL.revokeObjectURL(url);
}

export default function RelayStudioPage({ project, language = 'English', onCreateAction }) {
  const [inputText, setInputText] = useState('');
  const [destination, setDestination] = useState('auto');
  const [file, setFile] = useState(null);
  const [useCustomSchema, setUseCustomSchema] = useState(false);
  const [schemaText, setSchemaText] = useState(JSON.stringify(DEFAULT_SCHEMA, null, 2));
  const [useGoogleSearch, setUseGoogleSearch] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [saved, setSaved] = useState(false);

  const generate = async event => {
    event.preventDefault();
    if (!project?.id || (!inputText.trim() && !file)) {
      setError('Add text or attach an image/audio file before generating a preview.');
      return;
    }
    setBusy(true);
    setError('');
    setResult(null);
    setSaved(false);
    try {
      const response = await relayApi.previewRelay(project.id, {
        inputText, destination, language,
        schemaJson: useCustomSchema ? schemaText : '',
        useGoogleSearch, file,
      });
      setResult(response);
    } catch (caught) {
      setError(caught.message || 'Relay preview failed.');
    } finally {
      setBusy(false);
    }
  };

  const saveProposal = async () => {
    if (!result || !onCreateAction || saved) return;
    const output = result.output || {};
    const title = output.title || output.summary || output.channel_message || output.description ||
      (destination === 'jira' ? output.summary : null) || 'Structured Relay proposal';
    const safeTitle = ('Relay proposal: ' + String(title)).slice(0, 250);
    const description = [
      'Prepared by Relay Studio for ' + (project?.name || project?.id || 'the selected project') + '.',
      'Destination: ' + result.resolved_destination + ' (preview only).',
      'Language: ' + result.language + '.',
      'Human approval is required. No external system was changed.',
      '',
      'Structured proposal:',
      JSON.stringify(output, null, 2),
    ].join('\n');
    setSaved(true);
    try {
      await onCreateAction({ title: safeTitle, description });
    } catch {
      setSaved(false);
    }
  };

  return (
    <div className="page-stack relay-studio-page">
      <section className="relay-studio-hero">
        <div>
          <div className="relay-studio-kicker"><span>✦</span> MULTIMODAL · STRUCTURED · HUMAN-APPROVED</div>
          <h2>One input. The right next step.</h2>
          <p>Paste a noisy update, upload a whiteboard image, or add a voice memo. Relay classifies the content, returns schema-validated JSON, and lets you review it before creating an internal approval item.</p>
          <div className="relay-studio-tags"><span>Gemini reasoning</span><span>Schema Studio</span><span>Diff preview</span></div>
        </div>
        <div className="relay-studio-hero-art" aria-hidden="true"><span>IN</span><i>→</i><span>AI</span><i>→</i><span>JSON</span></div>
      </section>

      <form className="panel relay-studio-form" onSubmit={generate}>
        <div className="relay-studio-form-header"><div><span className="eyebrow">STEP 01 · INPUT</span><h3>Bring your raw context</h3><p>Content is processed for this request only; the uploaded binary is not saved by Relay.</p></div><span className="relay-language-chip">{language}</span></div>
        <label className="relay-input-label">Paste notes, logs, a request, or meeting transcript
          <textarea value={inputText} onChange={event => setInputText(event.target.value)} maxLength={12000} rows={6} placeholder={'Example: Vendor API delivery moved to Oct 15. Integration is blocked. QA needs two full days for regression. Who needs to do what?'} />
        </label>
        <div className="relay-input-foot"><span>{inputText.length.toLocaleString()} / 12,000 characters</span><button type="button" className="text-button" onClick={() => setInputText('ERROR: GET /vendor/catalog returned 503 for 18 minutes. Retry policy exhausted. Release train R42 is blocked; vendor response expected tomorrow. Create a clear bug ticket with impact and acceptance criteria.')}>Use example log</button></div>
        <div className="relay-upload-panel">
          <div className="relay-upload-icon">⇧</div>
          <div className="relay-upload-copy"><strong>Or add an image / voice note</strong><small>PNG, JPG, WebP, GIF, WAV, MP3, M4A, OGG, FLAC or AAC · max 10 MB</small></div>
          <label className="button button-secondary relay-file-button">Choose file<input type="file" accept="image/png,image/jpeg,image/webp,image/gif,audio/wav,audio/x-wav,audio/mpeg,audio/mp3,audio/mp4,audio/m4a,audio/x-m4a,audio/aac,audio/ogg,audio/flac" onChange={event => setFile(event.target.files?.[0] || null)} /></label>
          {file && <button type="button" className="relay-remove-file" onClick={() => setFile(null)} aria-label="Remove attachment">×</button>}
        </div>
        {file && <div className="relay-file-chip"><span>▤</span><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div>}

        <div className="relay-options-grid">
          <label>Output destination
            <select value={destination} onChange={event => { setDestination(event.target.value); if (!useCustomSchema) setSchemaText(JSON.stringify(TEMPLATE_SCHEMAS[event.target.value] || DEFAULT_SCHEMA, null, 2)); }}>
              {DESTINATIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <small>{DESTINATIONS.find(item => item.value === destination)?.description}</small>
          </label>
          <div className="relay-grounding-option">
            <label className="relay-checkbox"><input type="checkbox" checked={useGoogleSearch} onChange={event => setUseGoogleSearch(event.target.checked)} /><span><strong>Ground with Google Search</strong><small>Optional extra Gemini request; may use additional quota. Disabled by default.</small></span></label>
          </div>
        </div>

        <details className="relay-schema-studio">
          <summary><span><strong>Schema Studio</strong><small>Customize the JSON contract without changing backend code.</small></span><span className="relay-schema-toggle-label">{useCustomSchema ? 'Custom schema ON' : 'Using destination template'}</span></summary>
          <label className="relay-checkbox relay-schema-enable"><input type="checkbox" checked={useCustomSchema} onChange={event => setUseCustomSchema(event.target.checked)} /><span><strong>Use my own JSON Schema</strong><small>Object schemas only, maximum 8 KB and four nesting levels. Unsupported schema keywords are rejected before Gemini runs.</small></span></label>
          <textarea className="relay-schema-editor" value={useCustomSchema ? schemaText : JSON.stringify(TEMPLATE_SCHEMAS[destination] || DEFAULT_SCHEMA, null, 2)} onChange={event => setSchemaText(event.target.value)} readOnly={!useCustomSchema} rows={12} spellCheck={false} aria-label="Custom JSON Schema" />
          <div className="relay-schema-actions"><button type="button" className="text-button" onClick={() => setSchemaText(JSON.stringify(TEMPLATE_SCHEMAS[destination] || DEFAULT_SCHEMA, null, 2))}>Load destination template</button><button type="button" className="text-button" onClick={() => setSchemaText(JSON.stringify(DEFAULT_SCHEMA, null, 2))}>Load auto-router schema</button></div>
        </details>

        {error && <div className="form-error relay-studio-error">{error}</div>}
        <div className="relay-studio-submit-row"><span><span className="live-dot"/> Output language: {language}</span><button className="button button-primary" type="submit" disabled={busy}>{busy ? <><span className="button-spinner"/> Relay is processing…</> : 'Generate structured preview →'}</button></div>
      </form>

      {busy && <section className="panel relay-progress-panel"><div className="relay-progress-orbit"><span>✦</span></div><strong>Relay is connecting the dots</strong><p>Reading input, classifying intent, and preparing a structured proposal in {language}.</p><div className="relay-progress-bar"><i/></div><span className="relay-progress-caption">The output will remain a preview until a person reviews it.</span></section>}

      {result && <section className="relay-results page-stack">
        <div className="relay-pipeline-panel panel">
          <div className="relay-result-heading"><div><span className="eyebrow">STEP 02 · PIPELINE</span><h3>From raw context to review-ready output</h3></div><span className="status-badge status-success"><span className="status-dot"/>Schema validated</span></div>
          <div className="relay-pipeline">
            {result.pipeline?.map((step, index) => <div className={'relay-pipeline-step ' + (step.status === 'current' ? 'current' : 'complete')} key={step.id}><span>{step.status === 'complete' ? '✓' : index + 1}</span><strong>{step.label}</strong>{index < result.pipeline.length - 1 && <i/>}</div>)}
          </div>
          <div className="relay-destination-result"><span className="relay-destination-icon">↗</span><div><small>RECOMMENDED DESTINATION</small><strong>{String(result.resolved_destination || 'manual_review').replaceAll('_', ' ')}</strong><span>Selected mode: {destination === 'auto' ? 'Auto-route' : destination}</span></div><button className="button button-secondary" type="button" onClick={() => downloadJson(result.output)}>Download JSON</button></div>
        </div>

        <div className="relay-diff-grid">
          <section className="panel relay-diff-card">
            <div className="relay-diff-header"><span className="relay-diff-index">A</span><div><strong>Original input</strong><small>What you supplied</small></div></div>
            <div className="relay-original-input">{result.original_text || 'No text pasted; analyze the attached file shown below.'}</div>
            {result.attachment && <div className="relay-attachment-summary"><span>▤</span><div><strong>{result.attachment.filename}</strong><small>{result.attachment.mime_type} · {(result.attachment.size_bytes / 1024 / 1024).toFixed(2)} MB</small></div></div>}
          </section>
          <section className="panel relay-diff-card relay-diff-output">
            <div className="relay-diff-header"><span className="relay-diff-index">B</span><div><strong>Gemini structured output</strong><small>Validated against the selected schema</small></div><span className="status-badge status-info">{result.language}</span></div>
            <pre className="relay-json-preview">{JSON.stringify(result.output, null, 2)}</pre>
          </section>
        </div>

        {result.grounding?.warning && <div className="error-banner relay-grounding-warning"><span>i</span><div><strong>Search grounding note</strong><p>{result.grounding.warning}</p></div></div>}
        {result.grounding?.sources?.length > 0 && <section className="panel relay-web-sources"><div className="panel-header"><div><h3>Web sources used</h3><p>Search grounding was enabled for this preview.</p></div></div><div>{result.grounding.sources.map(source => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title || source.url} ↗</a>)}</div></section>}

        <section className="relay-review-panel panel">
          <div className="relay-review-icon">✓</div><div className="relay-review-copy"><span className="eyebrow">STEP 03 · HUMAN REVIEW</span><h3>Review before relaying</h3><p>Approve to create an internal recovery-action proposal. This does not create a real Jira issue, Confluence page, or Slack message.</p><small>{result.notice}</small></div>
          <div className="relay-review-actions"><button className="button button-secondary" type="button" onClick={() => navigator.clipboard?.writeText(JSON.stringify(result.output, null, 2))}>Copy JSON</button><button className="button button-primary" type="button" onClick={saveProposal} disabled={saved}>{saved ? 'Saved to Recovery Actions ✓' : 'Approve & save proposal →'}</button></div>
        </section>
      </section>}
    </div>
  );
}
