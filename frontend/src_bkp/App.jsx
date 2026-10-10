import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { relayApi } from './api/client';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import LoadingState from './components/LoadingState';
import OverviewPage from './pages/OverviewPage';
import InvestigationPage from './pages/InvestigationPage';
import ActionsPage from './pages/ActionsPage';
import EvidenceList from './components/EvidenceList';
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

  if (loading) return <div className="app-loading"><LoadingState label="Connecting to Relay workspace…"/></div>;
  return <div className="app-shell">
    <Sidebar activeView={activeView} onNavigate={setActiveView} projects={projects} selectedProjectId={selectedProjectId} onSelectProject={setSelectedProjectId}/>
    <main className="main-area"><Topbar activeView={activeView} project={selectedProject} onRefresh={() => loadProjectData(selectedProjectId)} refreshing={refreshing}/>
      <div className="main-content">{error && <div className="error-banner"><span>!</span><div><strong>Something needs attention</strong><p>{error}</p></div><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
        {!projects.length ? <section className="panel"><div className="empty-state"><div className="empty-icon">⌂</div><h3>No projects yet</h3><p>Add a project through the backend seed script or project API. The UI automatically lists projects returned by the server.</p></div></section> : <>
          {activeView === 'overview' && <OverviewPage project={project} investigation={investigation} onNavigate={setActiveView} onRunAi={runAi} aiLoading={aiLoading}/>}
          {activeView === 'investigation' && <InvestigationPage project={project} investigation={investigation} aiResult={aiResult} aiLoading={aiLoading} onRunAi={runAi}/>}
          {activeView === 'actions' && <ActionsPage project={project} actions={actions} onCreate={createAction} onApprove={id => withAction(id, () => relayApi.approveAction(selectedProjectId, id), 'Action approved.')} onExecute={id => withAction(id, () => relayApi.executeAction(selectedProjectId, id), 'Simulation executed.')} onVerify={id => withAction(id, () => relayApi.verifyAction(selectedProjectId, id), 'Action verified.')} busyActionId={busyActionId}/>}
          {activeView === 'evidence' && <div className="page-stack"><section className="page-intro-row"><div><div className="eyebrow">PROJECT KNOWLEDGE</div><h2>Evidence library</h2><p>Source documents linked to {project?.name}. This will become the searchable RAG evidence layer.</p></div><span className="count-pill">{project?.evidence?.length || 0} sources</span></section><section className="panel"><EvidenceList evidence={project?.evidence || []}/></section></div>}
        </>}
        <footer className="app-footer"><span>RELAY · ORGANIZATIONAL INTELLIGENCE</span><span>Local development · Simulated execution</span></footer>
      </div>
    </main>
    {toast && <div className="toast"><span>✓</span>{toast}</div>}
  </div>;
}
