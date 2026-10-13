import React, { useState } from 'react';

const CHANNEL_ICONS = {
  whatsapp: '💬',
  email: '✉️',
  call: '📞',
  cti_event: '⚡',
  rep_note: '📝',
  customer_thread: '🌐',
};

export function OmnichannelTimeline({ interactions = [], interactionSentiments = [] }) {
  const [filter, setFilter] = useState('all');

  const counts = {
    all: interactions.length,
    whatsapp: interactions.filter((i) => i.interaction_type === 'whatsapp').length,
    email: interactions.filter((i) => i.interaction_type === 'email').length,
    call: interactions.filter((i) => i.interaction_type === 'call').length,
    cti_event: interactions.filter((i) => i.interaction_type === 'cti_event').length,
    rep_note: interactions.filter((i) => i.interaction_type === 'rep_note').length,
    customer_thread: interactions.filter((i) => i.interaction_type === 'customer_thread').length,
  };

  const filtered =
    filter === 'all'
      ? interactions
      : interactions.filter((i) => i.interaction_type === filter);

  // Helper to find sentiment tag for an interaction
  const getSentimentTag = (idx) => {
    if (!interactionSentiments || interactionSentiments.length === 0) return null;
    return interactionSentiments.find((s) => s.interaction_idx === idx + 1);
  };

  return (
    <section className="timeline-section">
      <div className="timeline-header">
        <div className="timeline-title-row">
          <div className="header-icon-title">
            <span className="card-icon timeline-icon">💬</span>
            <h3 className="card-title">Omnichannel Timeline & Sentiment Stream</h3>
          </div>
          <p className="timeline-subtitle">
            Unified historical stream with per-interaction sentiment scoring and tone classification
          </p>
        </div>

        <div className="timeline-filters">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({counts.all})
          </button>
          <button
            className={`filter-btn ${filter === 'whatsapp' ? 'active' : ''}`}
            onClick={() => setFilter('whatsapp')}
          >
            WhatsApp ({counts.whatsapp})
          </button>
          <button
            className={`filter-btn ${filter === 'email' ? 'active' : ''}`}
            onClick={() => setFilter('email')}
          >
            Email ({counts.email})
          </button>
          <button
            className={`filter-btn ${filter === 'call' ? 'active' : ''}`}
            onClick={() => setFilter('call')}
          >
            Voice Calls ({counts.call})
          </button>
          <button
            className={`filter-btn ${filter === 'cti_event' ? 'active' : ''}`}
            onClick={() => setFilter('cti_event')}
          >
            CTI Telephony ({counts.cti_event})
          </button>
          <button
            className={`filter-btn ${filter === 'rep_note' ? 'active' : ''}`}
            onClick={() => setFilter('rep_note')}
          >
            Rep Notes ({counts.rep_note})
          </button>
          <button
            className={`filter-btn ${filter === 'customer_thread' ? 'active' : ''}`}
            onClick={() => setFilter('customer_thread')}
          >
            Portal Inquiries ({counts.customer_thread})
          </button>
        </div>
      </div>

      <div className="timeline-feed">
        {filtered.length > 0 ? (
          filtered.map((item, idx) => {
            const icon = CHANNEL_ICONS[item.interaction_type] || '📌';
            const timeStr = item.created_at
              ? new Date(item.created_at).toLocaleString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })
              : 'Recent';
            const dirClass = `direction-${item.direction || 'inbound'}`;

            // Find matching sentiment
            const originalIdx = interactions.indexOf(item);
            const sentiment = getSentimentTag(originalIdx);

            let sentimentClass = 'neutral';
            let sentimentPrefix = '⚪';
            if (sentiment) {
              if (sentiment.label === 'positive') {
                sentimentClass = 'positive';
                sentimentPrefix = '🟢';
              } else if (sentiment.label === 'friction') {
                sentimentClass = 'friction';
                sentimentPrefix = '🔴';
              } else if (sentiment.label === 'hesitant') {
                sentimentClass = 'hesitant';
                sentimentPrefix = '🟡';
              }
            }

            return (
              <div key={idx} className={`timeline-item ${sentiment ? `sentiment-item-${sentimentClass}` : ''}`}>
                <div className={`timeline-channel-icon channel-${item.interaction_type}`}>
                  {icon}
                </div>
                <div className="timeline-content-box">
                  <div className="timeline-top">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="channel-badge">
                        {(item.interaction_type || 'note').replace('_', ' ')}
                      </span>
                      <span className={`direction-tag ${dirClass}`}>
                        {item.direction || 'inbound'}
                      </span>

                      {/* Real-time Sentiment Tag Chip */}
                      {sentiment && (
                        <span className={`sentiment-timeline-chip ${sentimentClass}`} title={`Sentiment Score: ${sentiment.score.toFixed(1)}/10`}>
                          <span>{sentimentPrefix}</span>
                          <strong>{sentiment.score.toFixed(1)}</strong>
                          <span className="sentiment-tone-text">{sentiment.tone}</span>
                        </span>
                      )}
                    </div>
                    <span className="timeline-time">{timeStr}</span>
                  </div>

                  <p className="timeline-text">{item.content}</p>

                  {/* Highlighted key phrase cue if present */}
                  {sentiment?.key_phrase && (
                    <div className="timeline-key-cue">
                      <span className="cue-label">Semantic Cue:</span>
                      <span className="cue-text">"{sentiment.key_phrase}"</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '30px' }}>
            No interactions found for this channel.
          </div>
        )}
      </div>
    </section>
  );
}
