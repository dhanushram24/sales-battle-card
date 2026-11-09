import React from 'react';

const CHANNEL_META = {
  whatsapp: { name: 'WhatsApp', icon: '💬' },
  email: { name: 'Email', icon: '✉️' },
  call: { name: 'Phone Call', icon: '📞' },
  cti_event: { name: 'CTI Telephony', icon: '⚡' },
  customer_thread: { name: 'Customer Portal', icon: '🌐' },
  rep_note: { name: 'Rep Note', icon: '📝' },
};

export function DealHealthGauge({ battlecard, loading, error, onRetry, streamProgress }) {
  if (!battlecard || !Number.isFinite(battlecard.overall_score)) return (
    <section className="card gauge-card" aria-busy={loading}>
      <div className="card-header">
        <h3 className="card-title">Deal Health Score</h3>
      </div>
      <div className="reasoning-summary-card" role={error ? 'alert' : 'status'}>
        <p className="reasoning-text">
          {loading ? (
            streamProgress ? (
              <span>⚡ {streamProgress.message} ({streamProgress.percent}%)</span>
            ) : 'Analyzing conversations. Your score will appear here when ready.'
          ) : error || 'Select a lead to load its score.'}
        </p>
        {!loading && onRetry && (
          <button className="btn-modal-primary" onClick={onRetry}>Generate score</button>
        )}
      </div>
    </section>
  );

  const score = battlecard.overall_score ?? 0;
  const insufficientEvidence = battlecard.purchase_outlook === 'insufficient_evidence';
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
  if (insufficientEvidence) {
    gaugeColor = 'var(--text-muted)';
    classificationClass = 'warm';
    classificationText = 'Insufficient evidence';
  }

  const breakdown = battlecard.score_breakdown || {};
  const emotions = battlecard.emotional_dimensions || {};
  const momentum = battlecard.momentum;
  const committee = battlecard.committee;
  const callIntel = battlecard.call_intelligence;

  const channelPulse = (battlecard.channel_sentiments || []).map(c => {
    const raw = String(c.channel || '').trim();
    const meta = CHANNEL_META[raw.toLowerCase()] || { name: raw.replace(/_/g, ' '), icon: '📡' };
    return {
      name: meta.name,
      icon: meta.icon,
      score: c.score,
    };
  });

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

      {loading && (
        <p className="status-banner" role="status">
          {streamProgress ? `⚡ ${streamProgress.message} (${streamProgress.percent}%)` : 'Refreshing analysis...'}
        </p>
      )}
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
              strokeDashoffset: insufficientEvidence ? circumference : strokeDashoffset,
            }}
          ></circle>
        </svg>
        <div className="gauge-number-box">
          <span className="score-number">{insufficientEvidence ? 'N/A' : score.toFixed(1)}</span>
          {!insufficientEvidence && <span className="score-max">/10</span>}
          <span className="score-label">Deal Health Score</span>
        </div>
      </div>

      {/* Classification Badge */}
      {insufficientEvidence && <p className="reasoning-text" role="status">More customer evidence is needed to assess purchase readiness.</p>}
      <div className="classification-box">
        <span className={`classification-badge ${classificationClass}`}>
          🔥 {classificationText}
        </span>
      </div>

      {/* Phase 3: Temporal Momentum & Velocity Pill */}
      {momentum && (
        <div className="momentum-banner-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '6px 0 12px', padding: '6px 12px', background: 'rgba(255,255,255,0.025)', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '11.5px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{momentum.momentum_direction === 'accelerating' ? '🚀' : (momentum.momentum_direction === 'stalled' ? '⚠️' : '⚡')}</span>
            <strong style={{ textTransform: 'capitalize' }}>Momentum: {momentum.momentum_direction}</strong>
            <span className={momentum.velocity_score >= 0 ? 'text-emerald' : 'text-rose'}>
              ({momentum.velocity_score >= 0 ? '+' : ''}{momentum.velocity_score.toFixed(1)}/wk)
            </span>
          </span>
          <span className="text-muted" style={{ fontSize: '11px' }}>
            Last touch: {momentum.days_since_last_customer_touch}d ago · Risk: <strong className={momentum.stall_risk_level.includes('High') || momentum.stall_risk_level.includes('Critical') ? 'text-rose' : 'text-emerald'}>{momentum.stall_risk_level}</strong>
          </span>
        </div>
      )}

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

      {/* Phase 3: Buying Committee Consensus Breakdown */}
      {committee && committee.stakeholders && committee.stakeholders.length > 0 && (
        <div className="committee-section" style={{ marginTop: '14px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="mini-header-text">BUYING COMMITTEE CONSENSUS</span>
            <span className="stance-badge-amber" style={{ fontSize: '10px' }}>
              {committee.consensus_index.toFixed(1)}/10 Index
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
            {committee.stakeholders.map((s, idx) => (
              <div key={idx} style={{ padding: '6px 8px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-subtle)', fontSize: '11px' }}>
                <div style={{ fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{s.role}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', color: 'var(--text-muted)' }}>
                  <span>{s.stance}</span>
                  <strong className={s.sentiment >= 7 ? 'text-emerald' : 'text-amber'}>{s.sentiment.toFixed(1)}/10</strong>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Phase 3: Telephony Speech & Diarization Intelligence */}
      {callIntel && (
        <div className="speech-intelligence-card" style={{ marginTop: '14px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="mini-header-text">📞 TELEPHONY SPEECH & TALK RATIO</span>
            <span className="stance-badge-amber" style={{ fontSize: '10px' }}>
              Patience: {callIntel.patience_score.toFixed(1)}/10
            </span>
          </div>

          <div style={{ marginBottom: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', marginBottom: '4px' }}>
              <span>Sales Rep: <strong>{callIntel.talk_ratio_rep}%</strong></span>
              <span>Buyer: <strong>{callIntel.talk_ratio_customer}%</strong></span>
            </div>
            <div className="progress-track" style={{ height: '6px', display: 'flex', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${callIntel.talk_ratio_rep}%`, background: '#6366f1' }} title={`Rep: ${callIntel.talk_ratio_rep}%`}></div>
              <div style={{ width: `${callIntel.talk_ratio_customer}%`, background: '#10b981' }} title={`Customer: ${callIntel.talk_ratio_customer}%`}></div>
            </div>
          </div>

          <p style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
            {callIntel.speech_summary}
          </p>
        </div>
      )}

      {/* Channel Sentiment Pulse */}
      <div className="channel-sentiment-section">
        <span className="mini-header-text" style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>CHANNEL SENTIMENT PULSE</span>
        </span>
        <div className="channel-pills-row">
          {!channelPulse.length && <span className="text-muted" style={{ fontSize: '11px' }}>No channel data</span>}
          {channelPulse.map((c, i) => (
            <div key={i} className="channel-pill">
              <span className="ch-icon">{c.icon}</span>
              <span className="ch-name">{c.name}</span>
              <span className={`ch-score ${c.score >= 7 ? 'text-emerald' : 'text-amber'}`}>
                {c.score?.toFixed(1) ?? 'N/A'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Score Breakdown Footer */}
      <div className="score-breakdown-row">
        <div className="breakdown-stat">
          <span className="b-label">Sentiment</span>
          <strong className="b-val text-emerald">{breakdown.sentiment_score?.toFixed(1) ?? 'N/A'}</strong>
        </div>
        <div className="breakdown-stat">
          <span className="b-label">Engagement</span>
          <strong className="b-val text-cyan">{breakdown.engagement_score?.toFixed(1) ?? 'N/A'}</strong>
        </div>
        <div className="breakdown-stat">
          <span className="b-label">Intent</span>
          <strong className="b-val text-emerald">{breakdown.intent_score?.toFixed(1) ?? 'N/A'}</strong>
        </div>
        <div className="breakdown-stat">
          <span className="b-label">Risk Penalty</span>
          <strong className="b-val text-rose">-{breakdown.risk_penalty?.toFixed(1) ?? 'N/A'}</strong>
        </div>
      </div>
    </section>
  );
}
