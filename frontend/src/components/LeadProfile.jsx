import React, { useState } from 'react';

export function LeadProfile({
  lead,
  lastSyncedAt,
  onEditLead,
  onViewInCRM,
  onCopyLeadId,
  onGenerateProposal,
  onSync,
  busy,
}) {
  const [showMoreMenu, setShowMoreMenu] = useState(false);

  if (!lead) return null;

  const initials = (lead.name || '?')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const syncTime = lastSyncedAt
    ? new Date(lastSyncedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'Not analyzed';

  return (
    <section className="lead-header-banner">
      {/* Breadcrumbs Row */}
      <div className="breadcrumb-row">
        <span className="breadcrumb-link">Leads</span>
        <span className="breadcrumb-sep">&gt;</span>
        <span className="breadcrumb-current">Lead #{lead.id}</span>
        <button
          className="btn-copy-id"
          title="Copy Lead ID"
          onClick={() => onCopyLeadId(lead.id)}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="copy-icon-sm">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>
      </div>

      {/* Main Profile Info Row */}
      <div className="lead-main-bar">
        <div className="lead-left-group">
          <div className="lead-avatar-circle">{initials}</div>

          <div className="lead-info-col">
            <div className="lead-title-row">
              <h2 className="lead-name-text">{lead.name || 'Unnamed contact'}</h2>
              <span className="badge-pill pill-lead-id">Lead #{lead.id}</span>
              <span className="badge-pill pill-stage-purple">{lead.stage || 'Stage not recorded'}</span>
              <span className="badge-pill pill-status-green">{lead.status || 'Status not recorded'}</span>
            </div>

            <div className="lead-metadata-row">
              <span className="meta-item">
                <svg className="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
                  <line x1="9" y1="22" x2="9" y2="2" />
                  <path d="M8 6h.01M16 6h.01M8 10h.01M16 10h.01M8 14h.01M16 14h.01M8 18h.01M16 18h.01" />
                </svg>
                <span>{lead.company || 'Company not recorded'}</span>
              </span>

              <span className="meta-item">
                <svg className="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
                <span>License scope not recorded</span>
              </span>

              <span className="meta-item">
                <svg className="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>Assigned: <strong>{lead.assigned_to || 'Unassigned'}</strong></span>
              </span>

              <span className="meta-item">
                <svg className="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                <span>Last Synced: <strong>{syncTime}</strong></span>
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons on Right */}
        <div className="lead-actions-group">
          <button className="btn-lead-action" onClick={onEditLead} disabled={busy}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-action-icon-sm">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            <span>Edit Lead</span>
          </button>

          <div className="more-menu-wrapper">
            <button
              className="btn-lead-action"
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              aria-haspopup="true"
              aria-expanded={showMoreMenu}
            >
              <span>More</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="caret-icon-sm">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>

            {showMoreMenu && (
              <>
                <div
                  className="dropdown-backdrop-transparent"
                  onClick={() => setShowMoreMenu(false)}
                />
                <div className="more-dropdown-menu" onClick={() => setShowMoreMenu(false)}>
                  <button className="dropdown-menu-item" onClick={onEditLead} disabled={busy}>
                    <span className="dropdown-item-icon">✏️</span>
                    <span>Edit Lead Profile</span>
                  </button>
                  {onGenerateProposal && (
                    <button className="dropdown-menu-item" onClick={onGenerateProposal}>
                      <span className="dropdown-item-icon">📑</span>
                      <span>Generate Proposal</span>
                    </button>
                  )}
                  <button className="dropdown-menu-item" onClick={onViewInCRM}>
                    <span className="dropdown-item-icon">📄</span>
                    <span>View Account Details</span>
                  </button>
                  <button className="dropdown-menu-item" onClick={() => onCopyLeadId(lead.id)}>
                    <span className="dropdown-item-icon">📋</span>
                    <span>Copy Lead ID</span>
                  </button>
                  {onSync && (
                    <button className="dropdown-menu-item" onClick={onSync} disabled={busy}>
                      <span className="dropdown-item-icon">⚡</span>
                      <span>Re-analyze Battlecard</span>
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          <button className="btn-view-crm" onClick={onViewInCRM}>
            <span>View Account</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="btn-action-icon-sm">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}
