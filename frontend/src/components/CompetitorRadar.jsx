import React, { useState } from 'react';

const getDynamicRebuttalText = (o, angle = 'value') => {
  const handling = o.recommended_handling || 'Address concern with structured validation.';
  const objection = o.objection || 'commercial requirement';
  switch (angle) {
    case 'technical':
      return `Technical & Integration Angle: Regarding "${objection}": ${handling} Focus on native telephony synchronization, direct API connectors, and automated call dispositions.`;
    case 'sla':
      return `Delivery & SLA Angle: Regarding "${objection}": ${handling} Align on committed implementation timelines, assigned solution engineering support, and milestone signoffs.`;
    case 'value':
    default:
      return `Value & Commercial Angle: Regarding "${objection}": ${handling} Emphasize operational ROI, elimination of third-party gateway overhead, and rep productivity gains.`;
  }
};

export function CompetitorRadar({
  competitors = [],
  objections = [],
  buyingSignals = [],
  onCopy,
  onLogAction
}) {
  const compList = competitors;
  const objList = objections;
  const signalList = buyingSignals;
  const [selectedAngles, setSelectedAngles] = useState({});
  const [actionNotices, setActionNotices] = useState({});

  const handleAngleSelect = (idx, angle) => {
    setSelectedAngles(prev => ({ ...prev, [idx]: angle }));
  };

  const getRebuttalText = (o, idx) => {
    const angle = selectedAngles[idx] || 'value';
    return getDynamicRebuttalText(o, angle);
  };

  const handlePushToCRM = async (o, idx) => {
    if (!onLogAction) return;
    const text = getRebuttalText(o, idx);
    try {
      await onLogAction(`Action Plan for objection [${o.objection}]: ${text}`);
      setActionNotices(prev => ({ ...prev, [idx]: 'Pushed to CRM thread!' }));
      setTimeout(() => {
        setActionNotices(prev => ({ ...prev, [idx]: '' }));
      }, 3000);
    } catch {
      setActionNotices(prev => ({ ...prev, [idx]: 'Failed to push to CRM.' }));
    }
  };

  return (
    <section className="card radar-card">
      {/* Header */}
      <div className="card-header">
        <div className="header-icon-title">
          <span className="card-icon competitor-icon">⚔️</span>
          <h3 className="card-title">Competitor Radar & Objections</h3>
        </div>
        <span className="detected-badge-red">{compList.length} Detected</span>
      </div>

      {/* Threat Alert Cards */}
      <div className="competitors-list">
        {!compList.length && <p className="text-muted">No competitor evidence available.</p>}
        {compList.map((c, i) => (
          <div key={i} className="threat-alert-box">
            <div className="threat-header-row">
              <span className="threat-badge-red">THREAT ALERT</span>
              <strong className="threat-competitor-name">{c.competitor_name}</strong>
            </div>

            <p className="threat-context-text">{c.context}</p>

            <div className="pitch-strategy-card">
              <div className="pitch-strategy-header">
                <span className="strategy-bulb">💡</span>
                <span className="strategy-label">Pitch Winning Strategy</span>
              </div>
              <p className="strategy-desc">{c.counter_strategy}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Active Objections & Tactical Playbook */}
      <div className="objections-section">
        <div className="sub-header-row">
          <span className="sub-icon">⚠️</span>
          <h4 className="sub-title">Active Objections & Rebuttal Playbook</h4>
        </div>

        <div className="objections-wrapper">
          {!objList.length && <p className="text-muted">No objection evidence available.</p>}
          {objList.map((o, i) => {
            const currentAngle = selectedAngles[i] || 'value';
            const rebuttalScript = getRebuttalText(o, i);
            return (
              <div key={i} className="objection-card-amber">
                <div className="objection-title-row">
                  <span className="severity-pill-amber">
                    {(o.severity || 'MEDIUM').toUpperCase()}
                  </span>
                  <span className="objection-headline">{o.objection}</span>
                </div>

                {/* Angle Selector Tabs */}
                <div className="rebuttal-angle-tabs" style={{ display: 'flex', gap: '6px', margin: '8px 0' }}>
                  {[
                    { key: 'value', label: '💰 ROI & Value' },
                    { key: 'technical', label: '⚙️ Architecture' },
                    { key: 'sla', label: '📅 SLA & Delivery' }
                  ].map(tab => (
                    <button
                      key={tab.key}
                      type="button"
                      className={`btn-filter-pill ${currentAngle === tab.key ? 'active' : ''}`}
                      style={{ fontSize: '0.72rem', padding: '3px 8px' }}
                      onClick={() => handleAngleSelect(i, tab.key)}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="rebuttal-script-box" style={{ background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: '6px', fontSize: '0.8rem', lineHeight: '1.4', color: '#e2e8f0', marginTop: '6px' }}>
                  {rebuttalScript}
                </div>

                {/* Quick Actions */}
                <div className="objection-actions-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', flexWrap: 'wrap', gap: '6px' }}>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {onCopy && (
                      <button
                        type="button"
                        className="btn-select-lead-sm"
                        style={{ fontSize: '0.75rem', padding: '3px 8px' }}
                        onClick={() => onCopy(rebuttalScript, 'Playbook rebuttal copied to clipboard.')}
                      >
                        📋 Copy Script
                      </button>
                    )}
                    {onLogAction && (
                      <button
                        type="button"
                        className="btn-select-lead-sm"
                        style={{ fontSize: '0.75rem', padding: '3px 8px', borderColor: 'var(--emerald)' }}
                        onClick={() => handlePushToCRM(o, i)}
                      >
                        📌 Push to CRM Thread
                      </button>
                    )}
                  </div>
                  {actionNotices[i] && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--emerald)', fontWeight: 600 }}>
                      ✓ {actionNotices[i]}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Buying Signals Detected */}
      <div className="buying-signals-section">
        <div className="sub-header-row">
          <span className="sub-icon">🚀</span>
          <h4 className="sub-title">Buying Signals Detected</h4>
        </div>

        <ul className="buying-signals-list">
          {signalList.map((s, i) => (
            <li key={i} className="signal-item">
              <span className="check-icon-green">✓</span>
              <span className="signal-text">{s}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
