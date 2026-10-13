import React from 'react';

export function CompetitorRadar({ competitors = [], objections = [], buyingSignals = [] }) {
  const compList = competitors;
  const objList = objections;
  const signalList = buyingSignals;

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

      {/* Active Objections */}
      <div className="objections-section">
        <div className="sub-header-row">
          <span className="sub-icon">⚠️</span>
          <h4 className="sub-title">Active Objections</h4>
        </div>

        <div className="objections-wrapper">
          {!objList.length && <p className="text-muted">No objection evidence available.</p>}
          {objList.map((o, i) => (
            <div key={i} className="objection-card-amber">
              <div className="objection-title-row">
                <span className="severity-pill-amber">
                  {(o.severity || 'MEDIUM').toUpperCase()}
                </span>
                <span className="objection-headline">{o.objection}</span>
              </div>
              <p className="objection-handling-text">
                <strong>Handling:</strong> {o.recommended_handling}
              </p>
            </div>
          ))}
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
