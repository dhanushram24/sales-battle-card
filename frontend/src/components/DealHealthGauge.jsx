import React from 'react';

export function DealHealthGauge({ battlecard, loading, error, onRetry }) {
  if (!battlecard || !Number.isFinite(battlecard.overall_score)) return (
    <section className="card gauge-card" aria-busy={loading}>
      <div className="card-header">
        <h3 className="card-title">Deal Health Score</h3>
      </div>
      <div className="reasoning-summary-card" role={error ? 'alert' : 'status'}>
        <p className="reasoning-text">
          {loading ? 'Analyzing conversations. Your score will appear here when ready.' :
            error || 'Select a lead to load its score.'}
        </p>
        {!loading && onRetry && (
          <button className="btn-modal-primary" onClick={onRetry}>Generate score</button>
        )}
      </div>
    </section>
  );

  const score = battlecard.overall_score ?? 0;
  const circumference = 314;
  const strokeDashoffset = circumference - (score / 10) * circumference;

  let gaugeColor = 'var(--emerald)';
  let classificationClass = 'hot';
  let classificationText = battlecard.classification || 'Unclassified';

  if (score < 6.5) {
    gaugeColor = 'var(--rose)';
    classificationClass = 'cold';
  } else if (score < 8.5) {
    gaugeColor = 'var(--amber)';
    classificationClass = 'warm';
  }

  const breakdown = battlecard.score_breakdown || {};
  const emotions = battlecard.emotional_dimensions || {};

  const channelPulse = (battlecard.channel_sentiments || []).map(c => ({
    name: c.channel, icon: '', score: c.score,
  }));

  return (
    <section className="card gauge-card">
      {/* Card Header */}
      <div className="card-header">
        <div className="header-icon-title">
          <span className="card-icon heart-icon">💖</span>
          <h3 className="card-title">Deal Health Score</h3>
          <span className="info-tooltip-icon" title="AI estimate of purchase readiness; not a calibrated win probability">ℹ️</span>
        </div>
        <span className="trend-badge-green">
          📈 {battlecard.sentiment_trend || 'Unknown'}
        </span>
      </div>

      {loading && <p className="status-banner" role="status">Refreshing analysis...</p>}
      {error && <p className="status-banner error-banner" role="alert">{error}</p>}
      {/* Radial Gauge */}
      <div className="radial-gauge-container">
        <svg className="radial-gauge-svg" viewBox="0 0 120 120">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>
          <circle className="gauge-bg" cx="60" cy="60" r="50"></circle>
          <circle
            className="gauge-bar"
            cx="60"
            cy="60"
            r="50"
            style={{
              stroke: gaugeColor,
              strokeDashoffset: strokeDashoffset,
            }}
          ></circle>
        </svg>
        <div className="gauge-number-box">
          <span className="score-number">{score.toFixed(1)}</span>
          <span className="score-max">/10</span>
          <span className="score-label">Deal Health Score</span>
        </div>
      </div>

      {/* Classification Badge */}
      <div className="classification-box">
        <span className={`classification-badge ${classificationClass}`}>
          🔥 {classificationText}
        </span>
      </div>

      {/* Emotional & Commercial Stance */}
      <div className="emotional-dimensions-card">
        <div className="emotional-header">
          <span className="mini-header-text">EMOTIONAL & COMMERCIAL STANCE</span>
          <span className="stance-badge-amber">{emotions.negotiation_stance || 'Unknown'}</span>
        </div>

        <div className="emotional-meters-grid">
          <div className="emotional-meter-item">
            <div className="meter-label-row">
              <span className="meter-name">Trust & Rapport</span>
              <strong className="meter-val">{emotions.trust_and_rapport?.toFixed(1) ?? 'N/A'}/10</strong>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill fill-cyan"
                style={{ width: `${(emotions.trust_and_rapport ?? 0) * 10}%` }}
              ></div>
            </div>
          </div>

          <div className="emotional-meter-item">
            <div className="meter-label-row">
              <span className="meter-name">Commercial Urgency</span>
              <strong className="meter-val">{emotions.commercial_urgency?.toFixed(1) ?? 'N/A'}/10</strong>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill fill-purple-pink"
                style={{ width: `${(emotions.commercial_urgency ?? 0) * 10}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Channel Sentiment Pulse */}
      <div className="channel-sentiment-section">
        <span className="mini-header-text" style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>💬</span> CHANNEL SENTIMENT PULSE
        </span>
        <div className="channel-sentiment-grid">
          {channelPulse.map((c, i) => (
            <div key={i} className="channel-pulse-card">
              <div className="channel-pulse-header">
                <span className="pulse-icon">{c.icon}</span>
                <span className="pulse-score">{c.score.toFixed(1)}</span>
              </div>
              <span className="pulse-name">{c.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Score Decomposition */}
      <div className="decomposition-section">
        <div className="mini-header-title">
          <span className="icon-sm">⚖️</span>
          <span className="mini-header-text">SCORE DECOMPOSITION</span>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-labels">
            <span>Sentiment Polarity</span>
            <strong className="val-text">{breakdown.sentiment_score?.toFixed(1) ?? 'N/A'} / 10</strong>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill fill-blue"
              style={{ width: `${(breakdown.sentiment_score ?? 0) * 10}%` }}
            ></div>
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-labels">
            <span>Engagement & Velocity</span>
            <strong className="val-text">{breakdown.engagement_score?.toFixed(1) ?? 'N/A'} / 10</strong>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill fill-magenta"
              style={{ width: `${(breakdown.engagement_score ?? 0) * 10}%` }}
            ></div>
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-labels">
            <span>Buyer Urgency & Intent</span>
            <strong className="val-text">{breakdown.intent_score?.toFixed(1) ?? 'N/A'} / 10</strong>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill fill-emerald"
              style={{ width: `${(breakdown.intent_score ?? 0) * 10}%` }}
            ></div>
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-labels">
            <span>Deal Friction / Penalty</span>
            <strong className="val-risk">-{breakdown.risk_penalty?.toFixed(1) ?? 'N/A'}</strong>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill fill-risk"
              style={{ width: `${((breakdown.risk_penalty ?? 0) / 5) * 100}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Semantic Reasoning Summary */}
      <div className="reasoning-summary-card">
        <div className="reasoning-header">
          <span className="bulb-icon">💡</span>
          <span className="reasoning-title">Semantic Reasoning Summary</span>
        </div>
        <p className="reasoning-text">
          Purchase outlook: {battlecard.purchase_outlook?.replaceAll('_', ' ') || 'Unknown'}
          {' | '}Confidence: {battlecard.confidence || 'Unknown'}
        </p>
        <p className="reasoning-text">
          {battlecard.sentiment_summary ||
            "No reasoning summary available."}
        </p>
        {battlecard.evidence_summary && (
          <details>
            <summary>Buying evidence summary</summary>
            <p className="reasoning-text" style={{ whiteSpace: 'pre-wrap' }}>
              {(() => {
                try { return Object.entries(JSON.parse(battlecard.evidence_summary))
                  .map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value}`).join('\n\n'); }
                catch { return battlecard.evidence_summary; }
              })()}
            </p>
          </details>
        )}
      </div>
    </section>
  );
}
