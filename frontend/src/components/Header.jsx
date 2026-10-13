import React, { useState } from 'react';
import { NotificationsPopover } from './Modals';

export function Header({
  leads = [],
  currentLeadId,
  onSelectLead,
  onSync,
  syncing,
  dbStatus,
  onOpenSearch,
  onToggleSidebar,
}) {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="app-header">
      {/* Left: Hamburger Toggle & Brand Block */}
      <div className="header-left-cluster">
        <button
          className="btn-toggle-sidebar"
          onClick={onToggleSidebar}
          title="Toggle Navigation Menu"
          aria-label="Toggle Navigation Menu"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="hamburger-icon">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <div className="header-brand-block">
          <div className="header-logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <div className="header-brand-info">
            <h1 className="header-brand-title">PARAMANTRA</h1>
            <p className="header-brand-sub">Omnichannel Semantic Intelligence & Deal Health Predictor</p>
          </div>
        </div>
      </div>

      {/* Center: Responsive Global Search Bar */}
      <div className="header-search-bar" onClick={onOpenSearch} onKeyDown={event => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); onOpenSearch(); } }} role="button" tabIndex={0}>
        <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <span className="search-placeholder-desktop">Search leads, account, or company...</span>
        <span className="search-placeholder-mobile">Search CRM...</span>
        <kbd className="shortcut-badge">⌘ K</kbd>
      </div>

      {/* Right: Header Actions */}
      <div className="header-right-actions">
        {/* Notification Bell */}
        <div className="notif-wrapper">
          <button
            className="btn-icon-notif"
            onClick={() => setShowNotifications(!showNotifications)}
            title="Deal Alerts & Signals"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="bell-icon">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            
          </button>

          <NotificationsPopover
            isOpen={showNotifications}
            onClose={() => setShowNotifications(false)}
          />
        </div>

        {/* Lead Selector Dropdown */}
        <div className="lead-selector-wrapper">
          <label htmlFor="leadSelect" className="selector-label">Select CRM Lead:</label>
          <div className="select-container">
            <select
              id="leadSelect"
              className="lead-dropdown"
              value={currentLeadId}
              onChange={(e) => onSelectLead(e.target.value)}
            >
              {leads && leads.length > 0 ? (
                leads.map((l) => (
                  <option key={l.id} value={l.id}>
                    Lead #{l.id} – {l.name} ({l.company || 'Paramantra Account'})
                  </option>
                ))
              ) : (
                <option value="">No leads available</option>
              )}
            </select>
            <svg className="dropdown-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Sync Battlecard Button */}
        <button className="btn-sync" onClick={onSync} disabled={syncing || !currentLeadId}>
          {syncing ? (
            <>
              <div className="spinner"></div>
              <span className="sync-btn-text">Analyzing Deal...</span>
            </>
          ) : (
            <>
              <span className="sync-icon">⚡</span>
              <span className="sync-btn-text">Sync Battlecard</span>
            </>
          )}
        </button>

        {/* Database Status Pill */}
        <div className={`db-status-pill ${dbStatus ? 'online' : 'offline'}`} title="Database connection status">
          <span className="status-dot"></span>
          <span className="db-status-text">{dbStatus === null ? 'Not checked' : dbStatus ? 'MySQL Live' : 'Database offline'}</span>
        </div>
      </div>
    </header>
  );
}
