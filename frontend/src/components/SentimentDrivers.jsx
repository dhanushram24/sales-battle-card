import React from 'react';

export function SentimentDrivers({ positiveDrivers = [], frictionDrivers = [] }) {
  return (
    <section className="card drivers-card">
      <div className="card-header">
        <div className="header-icon-title">
          <span className="card-icon quote-icon">🔍</span>
          <h3 className="card-title">Sentiment Explainability & Drivers</h3>
        </div>
        <span className="count-tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--emerald)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
          Direct Quote Attribution
        </span>
      </div>

      <p className="drivers-subtitle">
        Quoted conversation evidence used to explain the readiness assessment.
      </p>

      {/* Positive Drivers */}
      <div className="drivers-block positive-block">
        <div className="drivers-block-header">
          <span className="driver-pill positive">✓ Positive Momentum Drivers</span>
        </div>
        <div className="drivers-quotes-list">
          {positiveDrivers.length > 0 ? (
            positiveDrivers.map((driver, idx) => (
              <div key={idx} className="driver-quote-item positive-quote">
                <div className="quote-meta-row">
                  <span className="quote-channel-tag">{driver.channel}</span>
                  <span className="quote-impact positive-impact">{driver.impact}</span>
                </div>
                <blockquote className="quote-text">"{driver.quote}"</blockquote>
              </div>
            ))
          ) : (
            <p className="no-driver-text">No positive driver evidence available.</p>
          )}
        </div>
      </div>

      {/* Friction Drivers */}
      <div className="drivers-block friction-block" style={{ marginTop: '16px' }}>
        <div className="drivers-block-header">
          <span className="driver-pill friction">⚠️ Deal Friction & Pushback Drivers</span>
        </div>
        <div className="drivers-quotes-list">
          {frictionDrivers.length > 0 ? (
            frictionDrivers.map((driver, idx) => (
              <div key={idx} className="driver-quote-item friction-quote">
                <div className="quote-meta-row">
                  <span className="quote-channel-tag">{driver.channel}</span>
                  <span className="quote-impact friction-impact">{driver.impact}</span>
                </div>
                <blockquote className="quote-text">"{driver.quote}"</blockquote>
              </div>
            ))
          ) : (
            <p className="no-driver-text">No friction evidence available.</p>
          )}
        </div>
      </div>
    </section>
  );
}
