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
import { DealSimulator } from './components/DealSimulator';
import { ProposalModal, CompanyProfileModal, EditLeadModal, SpotlightSearchModal } from './components/Modals';
import { apiRequest, loadAllLeads } from './api';
import { useLeadData } from './useLeadData';

function LeadWorkspace({ id, activeTab, leads, onSelectLead, onLeadSaved, onBusy, onSyncReady, health }) {
  const data = useLeadData(id);
  const { lead, interactions, battlecard, scoreLoading } = data;
  const [modal, setModal] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);
  const [leadSearch, setLeadSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('ALL');
  const [portfolioRadar, setPortfolioRadar] = useState(null);
  const [accountsList, setAccountsList] = useState([]);
  const [selectedAccountCompany, setSelectedAccountCompany] = useState('');

  useEffect(() => {
    if (activeTab === 'leads') {
      apiRequest('/portfolio/radar')
        .then(res => setPortfolioRadar(res))
        .catch(() => {});
    }
    if (activeTab === 'accounts') {
      apiRequest('/accounts')
        .then(res => {
          setAccountsList(res || []);
          if (res?.length && !selectedAccountCompany) {
            setSelectedAccountCompany(res[0].company_name);
          }
        })
        .catch(() => {});
    }
  }, [activeTab, selectedAccountCompany]);

  const filteredLeads = leads.filter(item => {
    const term = leadSearch.toLowerCase().trim();
    const matchesSearch = !term ||
      (item.name || '').toLowerCase().includes(term) ||
      (item.company || '').toLowerCase().includes(term) ||
      (item.assigned_to || '').toLowerCase().includes(term) ||
      String(item.id).includes(term);
    const matchesStage = stageFilter === 'ALL' || (item.stage || '').toLowerCase().includes(stageFilter.toLowerCase());
    return matchesSearch && matchesStage;
  });
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
    streamProgress={data.streamProgress}
    onRetry={lead && !saving ? data.sync : undefined} />;
  const competitors = <CompetitorRadar competitors={battlecard?.competitors || []}
    objections={battlecard?.objections || []} buyingSignals={battlecard?.buying_signals || []}
    onCopy={copy} onLogAction={data.addActionPlan} />;
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
        <RepActionCoPilot
          nextAction={battlecard?.next_best_action}
          talkTracks={battlecard?.recommended_talk_tracks || []}
          onCopy={copy}
          onGetReengagement={data.getReengagementPackage}
          onLogAction={data.addActionPlan}
        />
        <RightUtilityPanel lead={lead} interactions={interactions} busy={saving || scoreLoading}
          onGenerateProposal={() => setModal('proposal')} onAddToPipeline={moveToNegotiation}
          onViewCompanyProfile={() => setModal('company')}
          onShareLead={() => copy(`${window.location.origin}/?lead=${encodeURIComponent(id)}`, 'Lead link copied.')}
          onViewAllTimeline={() => document.getElementById('omnichannel-timeline-section')?.scrollIntoView({ behavior: 'smooth' })} />
      </div>
      <DealSimulator battlecard={battlecard} onSimulate={data.simulateScenario} onLogAction={data.addActionPlan} onCopy={copy} />
      {drivers}
      <div id="omnichannel-timeline-section"><OmnichannelTimeline interactions={interactions} interactionSentiments={battlecard?.interaction_sentiments || []} /></div>
    </>}
    {activeTab === 'leads' && <section className="card tab-pane-card">
      <div className="leads-header-row">
        <div>
          <h3>CRM Pipeline Intelligence ({leads.length} Leads)</h3>
          <p className="tab-pane-subtitle">Live health overview and stage tracking across all pipeline opportunities</p>
        </div>
        <div className="leads-search-box">
          <input
            type="text"
            className="input-pipeline-search"
            placeholder="🔍 Search contacts, accounts, reps, or IDs..."
            value={leadSearch}
            onChange={e => setLeadSearch(e.target.value)}
          />
        </div>
      </div>

      {portfolioRadar && (
        <div className="portfolio-radar-summary-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', margin: '14px 0 18px' }}>
          <div className="portfolio-kpi-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.025)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Portfolio Avg Health</span>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--emerald)', marginTop: '4px' }}>
              {portfolioRadar.average_health_score.toFixed(1)}/10
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Across {portfolioRadar.total_leads} active CRM deals</span>
          </div>

          <div className="portfolio-kpi-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.025)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Healthy / Ready to Close</span>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--emerald)', marginTop: '4px' }}>
              🔥 {portfolioRadar.healthy_deals_count} Deals
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Score ≥ 7.5 High intent</span>
          </div>

          <div className="portfolio-kpi-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.025)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Slippage Risk Detected</span>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: portfolioRadar.at_risk_deals_count > 0 ? 'var(--rose)' : 'var(--emerald)', marginTop: '4px' }}>
              ⚠️ {portfolioRadar.at_risk_deals_count} Deals
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>High friction or price blocker</span>
          </div>

          <div className="portfolio-kpi-card" style={{ padding: '12px', background: 'rgba(255,255,255,0.025)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Stalled Momentum</span>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: portfolioRadar.stalled_deals_count > 0 ? 'var(--amber)' : 'var(--text-muted)', marginTop: '4px' }}>
              ⏳ {portfolioRadar.stalled_deals_count} Deals
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Inactive &gt;14 calendar days</span>
          </div>
        </div>
      )}

      <div className="pipeline-filters-bar">
        {['ALL', ...Array.from(new Set(leads.map(l => l.stage).filter(Boolean)))].map(stage => (
          <button
            key={stage}
            className={`btn-filter-pill ${stageFilter === stage ? 'active' : ''}`}
            onClick={() => setStageFilter(stage)}
          >
            {stage === 'ALL' ? `All (${leads.length})` : `${stage} (${leads.filter(l => (l.stage || '').toLowerCase() === stage.toLowerCase()).length})`}
          </button>
        ))}
      </div>

      <div className="leads-table-container"><table className="crm-table"><thead><tr>
        <th>ID</th><th>Contact</th><th>Company</th><th>Stage</th><th>Assigned rep</th><th>Action</th>
      </tr></thead><tbody>{filteredLeads.map(item => <tr key={item.id} className={item.id === id ? 'active-lead-row' : ''}>
        <td><strong className="lead-id-tag">#{item.id}</strong></td>
        <td>{item.name || 'Not recorded'}</td>
        <td>{item.company || 'Not recorded'}</td>
        <td>
          <span className="stage-pill">{item.stage || 'Not recorded'}</span>
          {portfolioRadar?.leads?.find(p => p.lead_id === item.id)?.slippage_risk && (
            <span className="severity-pill-amber" style={{ fontSize: '10px', marginLeft: '6px' }}>⚠️ Slippage Risk</span>
          )}
        </td>
        <td>{item.assigned_to || 'Unassigned'}</td>
        <td><button className="btn-select-lead-sm" onClick={() => onSelectLead(item.id)}>Open lead</button></td>
      </tr>)}</tbody></table></div>
      {!filteredLeads.length && <p className="text-muted" style={{ padding: '16px', textAlign: 'center' }}>No leads match the filter criteria.</p>}
    </section>}
    {activeTab === 'accounts' && <section className="card tab-pane-card account-dossier-card">
      <div className="dossier-header">
        <div>
          <span className="mini-header-text">ACCOUNT INTELLIGENCE DOSSIER</span>
          <h2 className="dossier-company-name">{lead?.company || 'No Account Selected'}</h2>
          <p className="dossier-meta">
            Primary Contact: <strong>{lead?.name || 'Not recorded'}</strong> · 
            Stage: <span className="stage-pill">{lead?.stage || 'Not recorded'}</span> · 
            Assigned: <strong>{lead?.assigned_to || 'Unassigned'}</strong>
          </p>
        </div>
        <div className="dossier-actions">
          <button className="btn-action-primary" disabled={!lead} onClick={() => setModal('company')}>Account Profile</button>
          <button className="btn-modal-primary" disabled={!lead} onClick={() => setModal('proposal')}>Draft Proposal</button>
        </div>
      </div>

      {battlecard ? (
        <div className="dossier-grid">
          <div className="dossier-metric-box">
            <span className="dossier-metric-label">Deal Health Readiness</span>
            <div className="dossier-metric-val">{battlecard.overall_score.toFixed(1)}/10</div>
            <span className="classification-badge warm" style={{ marginTop: '6px', display: 'inline-block' }}>{battlecard.classification}</span>
          </div>
          <div className="dossier-metric-box">
            <span className="dossier-metric-label">Commercial Urgency</span>
            <div className="dossier-metric-val">{battlecard.emotional_dimensions?.commercial_urgency?.toFixed(1) ?? 'N/A'}/10</div>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '6px' }}>Stance: {battlecard.emotional_dimensions?.negotiation_stance || 'Unknown'}</p>
          </div>
          <div className="dossier-metric-box">
            <span className="dossier-metric-label">Identified Competitors</span>
            <div className="dossier-metric-val">{battlecard.competitors?.length || 0}</div>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '6px' }}>{battlecard.competitors?.map(c => c.competitor_name).join(', ') || 'None reported'}</p>
          </div>
          <div className="dossier-metric-box">
            <span className="dossier-metric-label">Active Objections</span>
            <div className="dossier-metric-val">{battlecard.objections?.length || 0}</div>
            <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '6px' }}>Top: {battlecard.objections?.[0]?.objection?.slice(0, 45) || 'No active hurdles'}</p>
          </div>
        </div>
      ) : (
        <p className="status-banner" style={{ marginTop: '16px' }}>Generate score for this account to populate intelligence dossier metrics.</p>
      )}
    </section>}
    {activeTab === 'battlecard' && competitors}
    {activeTab === 'insights' && <><p className="status-banner">{interactions.length} recorded interactions. {battlecard ? `${battlecard.analyzed_interactions_count} interactions analyzed.` : 'Generate a score to see evidence-based insights.'}</p>{score}<DealSimulator battlecard={battlecard} onSimulate={data.simulateScenario} onLogAction={data.addActionPlan} onCopy={copy} />
      {drivers}</>}
    {activeTab === 'reports' && <section className="card tab-pane-card report-briefing-card">
      <div className="report-briefing-header">
        <div>
          <span className="mini-header-text">EXECUTIVE DEAL BRIEFING</span>
          <h3>{lead?.company || 'Lead Report'} — {lead?.name || 'Contact'}</h3>
          <p className="tab-pane-subtitle">
            Analyzed {battlecard?.analyzed_interactions_count || interactions.length} interactions across {interactions.length ? new Set(interactions.map(i => i.interaction_type)).size : 0} channels.
            {battlecard?.last_synced_at ? ` Generated on ${new Date(battlecard.last_synced_at).toLocaleDateString()}.` : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-action-primary" onClick={() => window.print()}>Print / Export PDF</button>
          <button className="btn-sync" disabled={!lead} onClick={exportReport}>Download JSON</button>
        </div>
      </div>

      {battlecard ? (
        <div className="report-briefing-body">
          <div className="status-banner" style={{ marginTop: '12px', background: 'rgba(99,102,241,0.08)' }}>
            <strong>Executive Sentiment Summary:</strong> {battlecard.sentiment_summary}
          </div>

          <div className="report-sections-grid">
            <div className="report-box">
              <h4>🎯 Recommended Next Best Action</h4>
              <p style={{ marginTop: '6px', color: 'var(--text-bright)' }}>{battlecard.next_best_action}</p>
              {battlecard.recommended_talk_tracks?.length > 0 && (
                <ul style={{ marginTop: '8px', paddingLeft: '18px', fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                  {battlecard.recommended_talk_tracks.map((t, idx) => <li key={idx} style={{ marginBottom: '4px' }}>{t}</li>)}
                </ul>
              )}
            </div>

            <div className="report-box">
              <h4>✅ Validated Buying Signals</h4>
              {battlecard.buying_signals?.length ? (
                <ul style={{ marginTop: '8px', paddingLeft: '18px', fontSize: '0.88rem', color: 'var(--emerald)' }}>
                  {battlecard.buying_signals.map((s, idx) => <li key={idx} style={{ marginBottom: '4px' }}>{s}</li>)}
                </ul>
              ) : <p className="text-muted" style={{ fontSize: '0.88rem', marginTop: '6px' }}>No explicit signals recorded.</p>}
            </div>

            <div className="report-box">
              <h4>⚠️ Active Objections & Tactical Counters</h4>
              {battlecard.objections?.length ? (
                <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {battlecard.objections.map((o, idx) => (
                    <div key={idx} style={{ padding: '8px 12px', background: 'rgba(245,158,11,0.08)', borderRadius: '6px', borderLeft: '3px solid var(--amber)' }}>
                      <strong style={{ fontSize: '0.88rem', color: 'var(--amber)' }}>{o.objection}</strong>
                      <p style={{ fontSize: '0.82rem', marginTop: '4px', color: 'var(--text-muted)' }}><strong>Handling:</strong> {o.recommended_handling}</p>
                    </div>
                  ))}
                </div>
              ) : <p className="text-muted" style={{ fontSize: '0.88rem', marginTop: '6px' }}>No active objections identified.</p>}
            </div>
          </div>
        </div>
      ) : (
        <div className="status-banner" style={{ marginTop: '16px' }}>No current analysis available. Click "Generate score" or "Sync Battlecard" to populate executive briefing.</div>
      )}
    </section>}
    {activeTab === 'settings' && <section className="card tab-pane-card settings-panel-card">
      <h3>System & AI Intelligence Engine</h3>
      <p className="tab-pane-subtitle">SalesBattle Multi-Provider Architecture and CRM Bridge Status</p>

      <div className="settings-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
        <div className="report-box">
          <h4>🔌 Infrastructure Connectivity</h4>
          <ul style={{ marginTop: '10px', listStyle: 'none', padding: 0, fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><strong>Backend API:</strong> {health ? '🟢 Connected (127.0.0.1:8000)' : '🔴 Unavailable'}</li>
            <li><strong>MySQL CRM DB:</strong> {health?.database_connected ? '🟢 Connected (Paramantra DB)' : '🔴 Disconnected'}</li>
            <li><strong>Active Lead:</strong> #{id} ({lead?.name || 'Loading'})</li>
          </ul>
        </div>

        <div className="report-box">
          <h4>🧠 Multi-Provider AI Engine</h4>
          <ul style={{ marginTop: '10px', listStyle: 'none', padding: 0, fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><strong>Routing Mode:</strong> <span className="stage-pill">{health?.ai_engine?.configured_mode || 'auto'}</span></li>
            <li><strong>OpenAI:</strong> {health?.ai_engine?.openai?.configured ? '🟢 Configured (GPT-4o-mini)' : '🟡 Fallback / Unconfigured'}</li>
            <li><strong>Google Gemini:</strong> {health?.ai_engine?.gemini?.configured ? '🟢 Configured (Gemini 1.5 Flash)' : '⚪ Available as failover'}</li>
            <li><strong>Offline Heuristic:</strong> 🟢 Ready (Deterministic semantic engine)</li>
          </ul>
        </div>

        <div className="report-box">
          <h4>📊 Analysis Metrics</h4>
          <p style={{ marginTop: '8px', fontSize: '0.9rem' }}>
            {battlecard ? (
              <>
                Scored by <strong>{battlecard.analysis_metrics?.scoring_model || 'AI Model'}</strong> with deal health <strong>{battlecard.overall_score.toFixed(1)}/10</strong> ({battlecard.classification}).
              </>
            ) : data.scoreError || 'No current analysis computed for this lead.'}
          </p>
        </div>
      </div>
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
