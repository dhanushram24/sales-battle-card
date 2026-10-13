import React from 'react';

export function Sidebar({
  activeTab,
  onSelectTab,
  leadCount = 0,
  collapsed = false,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
}) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
    { id: 'leads', label: 'Leads', icon: '👥', badge: leadCount },
    { id: 'accounts', label: 'Accounts', icon: '🏢' },
    { id: 'battlecard', label: 'Battlecard', icon: '⚔️' },
    { id: 'insights', label: 'Insights', icon: '📊' },
    { id: 'reports', label: 'Reports', icon: '📑' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div className="sidebar-mobile-backdrop" onClick={onCloseMobile}></div>
      )}

      <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Sidebar Header with Collapse Toggle */}
        <div className="sidebar-toggle-row">
          {!collapsed && <span className="sidebar-nav-heading">NAVIGATION</span>}
          <button
            className="btn-sidebar-collapse"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={`collapse-chevron-icon ${collapsed ? 'rotate-180' : ''}`}
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  onSelectTab(item.id);
                  if (onCloseMobile) onCloseMobile();
                }}
                title={collapsed ? item.label : undefined}
              >
                <span className="nav-icon">{item.icon}</span>
                {!collapsed && <span className="nav-label">{item.label}</span>}
                {item.badge !== undefined && (
                  <span className={`nav-badge ${collapsed ? 'badge-dot' : ''}`}>
                    {collapsed ? '' : item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* AI Version Card at Bottom */}
        <div className="sidebar-footer">
          {collapsed ? (
            <div
              className="ai-compact-badge"
              title="AI Powered v1.0.0 • On-demand analysis"
            >
              <span className="pulse-dot"></span>
              <span className="ai-icon-sm">🤖</span>
            </div>
          ) : (
            <div className="ai-status-card">
              <div className="ai-status-header">
                <div className="ai-status-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                </div>
                <div>
                  <span className="ai-status-title">AI Powered</span>
                  <p className="ai-status-sub">Smarter Insights, Better Deals.</p>
                </div>
              </div>
              <div className="ai-status-footer">
                <span className="ai-version-pill">v1.0.0</span>
                <span className="ai-status-pulse">
                  <span className="pulse-dot"></span> On-demand analysis
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
