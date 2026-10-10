import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { relayApi } from './api/client';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import LoadingState from './components/LoadingState';
import OverviewPage from './pages/OverviewPage';
import InvestigationPage from './pages/InvestigationPage';
import ActionsPage from './pages/ActionsPage';
import EvidenceList from './components/EvidenceList';
import EmailSyncPage from './pages/EmailSyncPage';
import EvidenceSearchPage from './pages/EvidenceSearchPage';
import PortfolioPage from './pages/PortfolioPage';
import RagChatPage from './pages/RagChatPage';
import DependencyMapPage from './pages/DependencyMapPage';
import DataSourcesPage from './pages/DataSourcesPage';
import './styles.css';

export default function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [project, setProject] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [aiResult, setAiResult] = useState(null);
  const [actions, setActions] = useState([]);
  const [activeView, setActiveView] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [busyActionId, setBusyActionId] = useState('');
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [gmailStatus, setGmailStatus] = useState(null);
  const [gmailStatusLoading, setGmailStatusLoading] = useState(false);
  const [gmailBusy, setGmailBusy] = useState(false);
  const [gmailSyncResult, setGmailSyncResult] = useState(null);
  const [gmailConfigResult, setGmailConfigResult] = useState(null);
  const [ragBusy, setRagBusy] = useState(false);
  const [ragResults, setRagResults] = useState([]);
  const [ragQuery, setRagQuery] = useState('');
  const [ragError, setRagError] = useState('');
  const [chatError, setChatError] = useState('');
  const [sourceBusy, setSourceBusy] = useState('');
  const [sourceFetchResults, setSourceFetchResults] = useState({ jira: null, confluence: null });
  const [sourceSyncResults, setSourceSyncResults] = useState({ jira: null, confluence: null });
  const [sourceErrors, setSourceErrors] = useState({ jira: '', confluence: '' });

  const selectedProject = useMemo(() => projects.find(p => p.id === selectedProjectId) || project, [projects, selectedProjectId, project]);
  const loadProjectData = useCallback(async (projectId, quiet = false) => {
    if (!projectId) return;
    if (!quiet) setRefreshing(true);
    setError('');
    try {
      const [projectData, investigationData, actionData] = await Promise.all([
        relayApi.getProject(projectId), relayApi.getInvestigation(projectId), relayApi.getActions(projectId),
      ]);
      setProject(projectData); setInvestigation(investigationData); setActions(actionData.actions || []); setAiResult(null);
    } catch (err) { setError(err.message || 'Could not load project data.'); }
    finally { setRefreshing(false); setLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    relayApi.getProjects().then(data => {
      if (!active) return;
      const list = data.projects || [];
      setProjects(list);
      if (list.length) setSelectedProjectId(current => current && list.some(p => p.id === current) ? current : list[0].id);
      else { setLoading(false); setError('No projects were found. Run the backend seed script or add a project.'); }
    }).catch(err => { if (active) { setLoading(false); setError(`${err.message}. Check that the FastAPI backend is running.`); } });
    return () => { active = false; };
  }, []);

  useEffect(() => { if (selectedProjectId) loadProjectData(selectedProjectId, true); }, [selectedProjectId, loadProjectData]);

  const showToast = message => { setToast(message); window.setTimeout(() => setToast(''), 3200); };
  const refreshGmailStatus = useCallback(async (projectId = selectedProjectId) => {
    if (!projectId) return;
    setGmailStatusLoading(true);
    try { const status = await relayApi.getGmailStatus(projectId); setGmailStatus(status); }
    catch (err) { setGmailStatus(null); setError(err.message || 'Could not load Gmail status.'); }
    finally { setGmailStatusLoading(false); }
  }, [selectedProjectId]);
  useEffect(() => {
    setGmailSyncResult(null); setGmailConfigResult(null);
    if (selectedProjectId) refreshGmailStatus(selectedProjectId);
  }, [selectedProjectId, refreshGmailStatus]);
  const connectGmail = async () => {
    setGmailBusy(true); setError('');
    try {
      const authWindow = window.open('about:blank', '_blank');
      const result = await relayApi.connectGmail(selectedProjectId);
      if (!result.authorization_url) { authWindow?.close(); throw new Error('Backend did not return an authorization URL.'); }
      if (authWindow) authWindow.location.href = result.authorization_url;
      else window.location.href = result.authorization_url;
      showToast('Google login opened. Complete consent, then refresh status.');
    } catch (err) { setError(err.message || 'Could not start Gmail login.'); }
    finally { setGmailBusy(false); }
  };
  const saveGmailConfig = async data => {
    setGmailBusy(true); setError(''); setGmailConfigResult(null);
    try { const result = await relayApi.configureGmail(selectedProjectId, data); setGmailConfigResult(result); await refreshGmailStatus(); showToast('Project email configuration saved.'); }
    catch (err) { setError(err.message || 'Could not save email configuration.'); }
    finally { setGmailBusy(false); }
  };
  const runGmailSync = async () => {
    setGmailBusy(true); setError(''); setGmailSyncResult(null);
    try { const result = await relayApi.runGmailSync(selectedProjectId); setGmailSyncResult(result); await refreshGmailStatus(); await loadProjectData(selectedProjectId, true); showToast('Gmail sync completed.'); }
    catch (err) { setError(err.message || 'Gmail sync failed.'); }
    finally { setGmailBusy(false); }
  };
  const disconnectGmail = async () => {
    if (!window.confirm(`Disconnect Gmail for ${selectedProject?.name || selectedProjectId}? Scheduled sync will be disabled.`)) return;
    setGmailBusy(true); setError('');
    try { await relayApi.disconnectGmail(selectedProjectId); await refreshGmailStatus(); showToast('Gmail disconnected for this project.'); }
    catch (err) { setError(err.message || 'Could not disconnect Gmail.'); }
    finally { setGmailBusy(false); }
  };
  const chatWithRag = async (message, history) => relayApi.chatWithRag(selectedProjectId, message, history);
  const fetchSourceRecords = async source => { setSourceBusy(source); setSourceErrors(c=>({...c,[source]:''})); try { const r=await relayApi.getMockIntegrationRecords(selectedProjectId,source); setSourceFetchResults(c=>({...c,[source]:r})); showToast(`${r.count} synthetic ${source} records fetched.`); } catch(e) { setSourceErrors(c=>({...c,[source]:e.message||`Could not fetch ${source} records.`})); } finally { setSourceBusy(''); } };
  const syncSourceRecords = async (source, recordIds=null) => { setSourceBusy(source); setSourceErrors(c=>({...c,[source]:''})); try { const r=await relayApi.syncMockIntegration(selectedProjectId,source,recordIds); setSourceSyncResults(c=>({...c,[source]:r})); await loadProjectData(selectedProjectId,true); showToast(`${source} records indexed into RAG.`); } catch(e) { setSourceErrors(c=>({...c,[source]:e.message||`Could not ingest ${source} records.`})); } finally { setSourceBusy(''); } };
  const searchEvidence = async query => {
    if (!selectedProjectId || !query?.trim()) return;
    setRagBusy(true); setRagError(''); setRagQuery(query); setRagResults([]);
    try {
      const response = await relayApi.searchDocuments(selectedProjectId, query.trim());
      setRagResults(Array.isArray(response) ? response : (response.results || response.matches || []));
    } catch (err) { setRagError(err.message || 'Could not search project evidence.'); }
    finally { setRagBusy(false); }
  };
  useEffect(() => { setRagResults([]); setRagQuery(''); setRagError(''); setSourceFetchResults({jira:null,confluence:null}); setSourceSyncResults({jira:null,confluence:null}); setSourceErrors({jira:'',confluence:''}); }, [selectedProjectId]);
  const runAi = async () => {
    if (!selectedProjectId) return;
    setAiLoading(true); setError('');
    try { const result = await relayApi.runAiInvestigation(selectedProjectId); setAiResult(result); setActiveView('investigation'); showToast('AI investigation completed.'); }
    catch (err) { setError(err.message || 'AI investigation failed.'); }
    finally { setAiLoading(false); }
  };
  const withAction = async (actionId, operation, successMessage) => {
    setBusyActionId(actionId); setError('');
    try { await operation(); await loadProjectData(selectedProjectId, true); showToast(successMessage); }
    catch (err) { setError(err.message || 'Action failed.'); }
    finally { setBusyActionId(''); }
  };
  const createAction = async data => { await relayApi.createAction(selectedProjectId, data); await loadProjectData(selectedProjectId, true); showToast('Action saved for approval.'); };
  const createActionFromAi = async data => {
    if (!selectedProjectId) return;
    setError('');
    try {
      await relayApi.createAction(selectedProjectId, data);
      await loadProjectData(selectedProjectId, true);
      setActiveView('actions');
      showToast('AI recommendation submitted for approval. Review it in Recovery Actions.');
    } catch (err) {
      setError(err.message || 'Could not submit the recommended recovery action.');
    }
  };

  if (loading) return <div className="app-loading"><LoadingState label="Connecting to Relay workspace…"/></div>;
  return <div className="app-shell">
    <Sidebar activeView={activeView} onNavigate={setActiveView} projects={projects} selectedProjectId={selectedProjectId} onSelectProject={setSelectedProjectId}/>
    <main className="main-area"><Topbar activeView={activeView} project={selectedProject} onRefresh={() => loadProjectData(selectedProjectId)} refreshing={refreshing}/>
      <div className="main-content">{error && <div className="error-banner"><span>!</span><div><strong>Something needs attention</strong><p>{error}</p></div><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
        {!projects.length ? <section className="panel"><div className="empty-state"><div className="empty-icon">⌂</div><h3>No projects yet</h3><p>Add a project through the backend seed script or project API. The UI automatically lists projects returned by the server.</p></div></section> : <>
          {activeView === 'portfolio' && <PortfolioPage onOpenProject={id => { setSelectedProjectId(id); setActiveView('overview'); }}/>}
          {activeView === 'dependencies' && <DependencyMapPage project={project}/>}
          {activeView === 'chat' && <RagChatPage project={selectedProject} onChat={chatWithRag}/>}
          {activeView === 'overview' && <OverviewPage project={project} investigation={investigation} onNavigate={setActiveView} onRunAi={runAi} aiLoading={aiLoading}/>}
          {activeView === 'investigation' && <InvestigationPage project={project} investigation={investigation} aiResult={aiResult} aiLoading={aiLoading} onRunAi={runAi} onCreateAction={createActionFromAi}/>}
          {activeView === 'actions' && <ActionsPage project={project} actions={actions} onCreate={createAction} onApprove={id => withAction(id, () => relayApi.approveAction(selectedProjectId, id), 'Action approved.')} onExecute={id => withAction(id, () => relayApi.executeAction(selectedProjectId, id), 'Simulation executed.')} onVerify={id => withAction(id, () => relayApi.verifyAction(selectedProjectId, id), 'Action verified.')} busyActionId={busyActionId}/>}
          {activeView === 'email' && <EmailSyncPage project={selectedProject} status={gmailStatus} loadingStatus={gmailStatusLoading} onRefreshStatus={() => refreshGmailStatus()} onConnect={connectGmail} onSaveConfig={saveGmailConfig} onRunSync={runGmailSync} onDisconnect={disconnectGmail} busy={gmailBusy} syncResult={gmailSyncResult} configResult={gmailConfigResult}/> }
          {activeView === 'evidence' && <EvidenceSearchPage project={selectedProject} onSearch={searchEvidence} busy={ragBusy} results={ragResults} searchedQuery={ragQuery} error={ragError}/>}
          {activeView === 'sources' && <DataSourcesPage project={selectedProject} onFetch={fetchSourceRecords} onSync={syncSourceRecords} busySource={sourceBusy} fetchResults={sourceFetchResults} syncResults={sourceSyncResults} errors={sourceErrors}/>} 
        </>}
        <footer className="app-footer"><span>RELAY · ORGANIZATIONAL INTELLIGENCE</span><span>Local development · Simulated execution</span></footer>
      </div>
    </main>
    {toast && <div className="toast"><span>✓</span>{toast}</div>}
  </div>;
}
