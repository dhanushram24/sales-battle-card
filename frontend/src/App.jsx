import { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { LeadProfile } from './components/LeadProfile';
import { DealHealthGauge } from './components/DealHealthGauge';
import { CompetitorRadar } from './components/CompetitorRadar';
import { RepActionCoPilot } from './components/RepActionCoPilot';
import { RightUtilityPanel } from './components/RightUtilityPanel';
import { SentimentDrivers } from './components/SentimentDrivers';
import { OmnichannelTimeline } from './components/OmnichannelTimeline';
import { ProposalModal, CompanyProfileModal, EditLeadModal, SpotlightSearchModal } from './components/Modals';
import { apiRequest, loadAllLeads } from './api';
import { useLeadData } from './useLeadData';

function LeadWorkspace({ id, activeTab, leads, onSelectLead, onLeadSaved, onBusy, onSyncReady, health }) {
  const data = useLeadData(id);
  const { lead, interactions, battlecard, scoreLoading } = data;
  const [modal, setModal] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  useEffect(() => { onBusy(scoreLoading || saving); }, [scoreLoading, saving, onBusy]);
  useEffect(() => {
    onSyncReady(() => data.sync);
    return () => onSyncReady(null);
  }, [data.sync, onSyncReady]);
  const copy = async (text, message = 'Copied to clipboard.') => {
    try { await navigator.clipboard.writeText(String(text)); setNotice(message); return true; }
    catch { setNotice('Clipboard access failed. Select and copy the text manually.'); return false; }
  };
  const save = async changes => {
    setSaving(true);
    try {
      const saved = await data.save(changes);
      if (saved) { onLeadSaved(saved); setNotice('Lead changes saved to the database.'); }
      return saved;
    } finally { setSaving(false); }
  };
  const moveToNegotiation = async () => {
    try { await save({ stage: 'Negotiation' }); }
    catch (error) { setNotice(error.message); }
  };
  const exportReport = () => {
    const blob = new Blob([JSON.stringify({ lead, battlecard, interactions }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `salesbattle-${id.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    setNotice('Report download started.');
  };
  const score = <DealHealthGauge battlecard={battlecard} loading={scoreLoading} error={data.scoreError}
    onRetry={lead && !saving ? data.sync : undefined} />;
  const competitors = <CompetitorRadar competitors={battlecard?.competitors || []}
    objections={battlecard?.objections || []} buyingSignals={battlecard?.buying_signals || []} />;
  const drivers = <SentimentDrivers positiveDrivers={battlecard?.positive_drivers || []}
    frictionDrivers={battlecard?.friction_drivers || []} />;
  return <>
    {notice && <div className="status-banner" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss message">Dismiss</button></div>}
    {data.loading && <p role="status" className="status-banner">Loading lead conversations...</p>}
    {data.error && <div className="status-banner error-banner" role="alert">{data.error}<button onClick={data.reload}>Retry loading lead</button></div>}
    {battlecard?.cache_saved === false && <p className="status-banner" role="alert">The score was generated, but could not be saved. Check database permissions before reloading.</p>}
    {activeTab === 'dashboard' && <>
      <LeadProfile lead={lead} lastSyncedAt={battlecard?.last_synced_at} busy={scoreLoading || saving}
        onEditLead={() => setModal('edit')} onViewInCRM={() => setModal('company')}
        onCopyLeadId={copy} onGenerateProposal={() => setModal('proposal')} onSync={() => data.sync()} />
      <div className="intelligence-quad-grid">
        {score}{competitors}
        <RepActionCoPilot nextAction={battlecard?.next_best_action} talkTracks={battlecard?.recommended_talk_tracks || []} onCopy={copy} />
        <RightUtilityPanel lead={lead} interactions={interactions} busy={saving || scoreLoading}
          onGenerateProposal={() => setModal('proposal')} onAddToPipeline={moveToNegotiation}
          onViewCompanyProfile={() => setModal('company')}
          onShareLead={() => copy(`${window.location.origin}/?lead=${encodeURIComponent(id)}`, 'Lead link copied.')}
          onViewAllTimeline={() => document.getElementById('omnichannel-timeline-section')?.scrollIntoView({ behavior: 'smooth' })} />
      </div>
      {drivers}
      <div id="omnichannel-timeline-section"><OmnichannelTimeline interactions={interactions} interactionSentiments={battlecard?.interaction_sentiments || []} /></div>
    </>}
    {activeTab === 'leads' && <section className="card tab-pane-card">
      <h3>CRM Leads ({leads.length})</h3>
      <div className="leads-table-container"><table className="crm-table"><thead><tr>
        <th>ID</th><th>Contact</th><th>Company</th><th>Stage</th><th>Assigned rep</th><th>Action</th>
      </tr></thead><tbody>{leads.map(item => <tr key={item.id}>
        <td>{item.id}</td><td>{item.name || 'Not recorded'}</td><td>{item.company || 'Not recorded'}</td>
        <td>{item.stage || 'Not recorded'}</td><td>{item.assigned_to || 'Unassigned'}</td>
        <td><button className="btn-select-lead-sm" onClick={() => onSelectLead(item.id)}>Open lead</button></td>
      </tr>)}</tbody></table></div>
    </section>}
    {activeTab === 'accounts' && <section className="card tab-pane-card"><h3>Account profile</h3>
      <p>{lead?.company || 'No account details available.'}</p>
      <p>Contact: {lead?.name || 'Not recorded'} · Stage: {lead?.stage || 'Not recorded'}</p>
      <button className="btn-action-primary" disabled={!lead} onClick={() => setModal('company')}>View account details</button>
    </section>}
    {activeTab === 'battlecard' && competitors}
    {activeTab === 'insights' && <><p className="status-banner">{interactions.length} recorded interactions. {battlecard ? `${battlecard.analyzed_interactions_count} interactions analyzed.` : 'Generate a score to see evidence-based insights.'}</p>{score}{drivers}</>}
    {activeTab === 'reports' && <section className="card tab-pane-card"><h3>Lead report</h3>
      <p>{battlecard ? `Deal health: ${battlecard.overall_score.toFixed(1)}/10. ${battlecard.sentiment_summary}` : 'No current analysis available.'}</p>
      <p>Deal health measures purchase readiness, not a calibrated win probability.</p>
      <button className="btn-sync" disabled={!lead} onClick={exportReport}>Download JSON report</button>
    </section>}
    {activeTab === 'settings' && <section className="card tab-pane-card"><h3>Connection status</h3>
      <p>Backend: {health ? 'Connected' : 'Unavailable'}</p>
      <p>Database: {health?.database_connected ? 'Connected' : 'Unavailable'}</p>
      <p>Analysis: {battlecard ? 'Score available for this lead' : data.scoreError || 'No score loaded'}</p>
    </section>}
    {modal === 'proposal' && lead && <ProposalModal lead={lead} onClose={() => setModal('')} onCopyProposal={copy} />}
    {modal === 'company' && lead && <CompanyProfileModal lead={lead} onClose={() => setModal('')} />}
    {modal === 'edit' && lead && <EditLeadModal lead={lead} onClose={() => setModal('')} onSaveLead={save} />}
  </>;
}

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [leads, setLeads] = useState([]);
  const [currentLeadId, setCurrentLeadId] = useState('');
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [syncAction, setSyncAction] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    const checkHealth = () => apiRequest('/health', { signal }).then(result => {
      if (!signal.aborted) setHealth(result);
    }).catch(() => { if (!signal.aborted) setHealth(null); });
    void checkHealth();
    const healthTimer = setInterval(checkHealth, 30000);
    loadAllLeads(signal).then(items => {
      if (signal.aborted) return;
      setLeads(items); setLoading(false); setError('');
      const requested = new URLSearchParams(window.location.search).get('lead');
      setCurrentLeadId(previous => items.some(item => item.id === previous) ? previous : items.find(item => item.id === requested)?.id || items[0]?.id || '');
    }).catch(failure => { if (!signal.aborted) { setError(failure.message); setLoading(false); } });
    return () => { controller.abort(); clearInterval(healthTimer); };
  }, [refresh]);
  useEffect(() => {
    const shortcut = event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); setSearchOpen(value => !value);
      }
    };
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, []);
  const selectLead = id => {
    setCurrentLeadId(String(id)); setActiveTab('dashboard'); setSearchOpen(false); setBusy(false);
    const url = new URL(window.location.href); url.searchParams.set('lead', id); window.history.replaceState(null, '', url);
  };
  const retry = () => { setLoading(true); setError(''); setRefresh(value => value + 1); };
  return <div className={`crm-layout-root ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
    <div className="ambient-glow glow-top-left" /><div className="ambient-glow glow-bottom-right" />
    <Header leads={leads} currentLeadId={currentLeadId} onSelectLead={selectLead}
      onSync={() => syncAction?.()} syncing={busy} dbStatus={health?.database_connected ?? null}
      onOpenSearch={() => setSearchOpen(true)}
      onToggleSidebar={() => window.innerWidth <= 768 ? setMobileMenuOpen(value => !value) : setSidebarCollapsed(value => !value)} />
    <div className="crm-body-container">
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} leadCount={leads.length} collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(value => !value)} mobileOpen={mobileMenuOpen} onCloseMobile={() => setMobileMenuOpen(false)} />
      <div className="crm-main-viewport"><main className="crm-content-container">
        {loading && <p className="status-banner" role="status">Loading CRM leads...</p>}
        {error && <div className="status-banner error-banner" role="alert">{error}<button onClick={retry}>Retry connection</button></div>}
        {!loading && !error && !leads.length && <div className="status-banner">No leads found in the configured database.<button onClick={retry}>Refresh leads</button></div>}
        {currentLeadId && <LeadWorkspace key={currentLeadId} id={currentLeadId} activeTab={activeTab} leads={leads}
          onSelectLead={selectLead} onLeadSaved={saved => setLeads(items => items.map(item => item.id === saved.id ? saved : item))}
          onBusy={setBusy} onSyncReady={setSyncAction} health={health} />}
      </main></div>
    </div>
    {searchOpen && <SpotlightSearchModal leads={leads} onSelectLead={selectLead} onClose={() => setSearchOpen(false)} />}
  </div>;
}
export default App;
