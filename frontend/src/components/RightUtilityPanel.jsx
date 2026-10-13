import React from 'react';

export function RightUtilityPanel({ lead, interactions = [], busy, onGenerateProposal, onAddToPipeline, onViewCompanyProfile, onShareLead, onViewAllTimeline }) {
  const latest = [...interactions].reverse().slice(0, 3);
  return <div className="right-utility-panel">
    <section className="card utility-card"><div className="card-header"><h3 className="card-title">Quick actions</h3></div>
      <div className="quick-actions-list">
        <button className="btn-action-primary" disabled={!lead} onClick={onGenerateProposal}>Draft proposal</button>
        <button className="btn-action-secondary" disabled={!lead || busy} onClick={onAddToPipeline}>Move to Negotiation</button>
        <button className="btn-action-secondary" disabled={!lead} onClick={onViewCompanyProfile}>View company profile</button>
        <button className="btn-action-secondary" disabled={!lead} onClick={onShareLead}>Copy lead link</button>
      </div>
    </section>
    <section className="card utility-card"><div className="card-header"><h3 className="card-title">Lead details</h3></div>
      <dl className="lead-details-table">{Object.entries({ Company: lead?.company, Stage: lead?.stage, Owner: lead?.assigned_to }).map(([label, value]) =>
        <div className="lead-detail-row" key={label}><dt className="lead-detail-label">{label}</dt><dd className="lead-detail-value">{value || 'Not recorded'}</dd></div>)}
      </dl>
    </section>
    <section className="card utility-card"><div className="card-header"><h3 className="card-title">Recent interactions</h3><button className="btn-view-all" onClick={onViewAllTimeline}>View all</button></div>
      <div className="mini-timeline-list">{latest.map((item, index) => <div className="mini-timeline-item" key={`${item.interaction_type}:${item.id}:${index}`}>
        <span className="mini-dot dot-blue" /><div className="mini-timeline-content"><span className="mini-event-title">{item.interaction_type || 'Note'}</span>
          <span className="mini-event-time">{item.created_at ? new Date(item.created_at).toLocaleString() : 'Date not recorded'}</span></div>
      </div>)}{!latest.length && <p className="text-muted">No interactions loaded.</p>}</div>
    </section>
  </div>;
}
