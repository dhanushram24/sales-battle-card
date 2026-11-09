import React, { useState } from 'react';

export function RepActionCoPilot({ nextAction, talkTracks = [], onCopy, onGetReengagement, onLogAction }) {
  const defaultAction = nextAction || 'Generate a score to see the recommended next action.';
  const defaultTracks = talkTracks;
  const [reengagement, setReengagement] = useState(null);
  const [loadingReengage, setLoadingReengage] = useState(false);
  const [crmNotice, setCrmNotice] = useState('');

  const handleGenerateRecovery = async () => {
    if (!onGetReengagement) return;
    setLoadingReengage(true);
    try {
      const res = await onGetReengagement();
      setReengagement(res);
    } catch {
      // recovery package generation error handled gracefully
    } finally {
      setLoadingReengage(false);
    }
  };

  const handlePushRecoveryToCRM = async () => {
    if (!onLogAction || !reengagement) return;
    try {
      await onLogAction(`Autonomous Intervention Plan Logged: ${reengagement.email_subject} | Recommended Concession: ${reengagement.recommended_concession}`);
      setCrmNotice('Intervention plan logged to CRM!');
      setTimeout(() => setCrmNotice(''), 3000);
    } catch {
      setCrmNotice('Failed to push to CRM.');
    }
  };

  return (
    <section className="card copilot-card">
      {/* Header */}
      <div className="card-header">
        <div className="header-icon-title">
          <span className="card-icon lightning-icon">⚡</span>
          <h3 className="card-title">Sales Rep Action Co-Pilot</h3>
        </div>
      </div>

      {/* Recommended Next Best Action Box */}
      <div className="next-action-glow-box">
        <div className="next-action-header-row">
          <div className="action-tag-group">
            <span className="target-icon">🎯</span>
            <span className="action-tag-text">RECOMMENDED NEXT BEST ACTION</span>
          </div>
          <button
            className="btn-copy-action" disabled={!nextAction}
            onClick={() => onCopy(defaultAction, 'Next Best Action copied to clipboard!')}
          >
            Copy Action
          </button>
        </div>

        <p className="next-action-paragraph">{defaultAction}</p>

        {onGetReengagement && (
          <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
            <button
              className="btn-track-copy"
              style={{ fontSize: '11px', padding: '4px 10px', background: 'rgba(239, 68, 68, 0.15)', borderColor: 'rgba(239, 68, 68, 0.35)', color: 'var(--rose)' }}
              onClick={handleGenerateRecovery}
              disabled={loadingReengage}
            >
              {loadingReengage ? 'Generating Recovery Package...' : '🚨 Generate Executive Recovery Package'}
            </button>
          </div>
        )}
      </div>

      {/* Autonomous Re-Engagement Intervention Card */}
      {reengagement && (
        <div className="reengagement-intervention-box" style={{ marginTop: '14px', padding: '12px', background: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="severity-pill-amber" style={{ background: 'rgba(239, 68, 68, 0.2)', color: 'var(--rose)' }}>
                {reengagement.urgency_level.toUpperCase()} INTERVENTION
              </span>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-main)' }}>
                {reengagement.intervention_headline}
              </span>
            </div>
            <button
              className="btn-track-copy"
              onClick={() => onCopy(reengagement.email_body, 'Recovery email copied to clipboard!')}
            >
              Copy Email
            </button>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px' }}>
            <strong>Subject:</strong> {reengagement.email_subject}
          </div>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '11.5px', color: 'var(--text-main)', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '6px', margin: '4px 0 8px' }}>
            {reengagement.email_body}
          </pre>

          <div style={{ fontSize: '11px', marginBottom: '4px', fontWeight: 600, color: 'var(--text-muted)' }}>
            Executive Call Agenda:
          </div>
          <ul style={{ margin: '0 0 8px', paddingLeft: '18px', fontSize: '11px', color: 'var(--text-muted)' }}>
            {reengagement.executive_call_agenda.map((pt, i) => (
              <li key={i}>{pt}</li>
            ))}
          </ul>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className="btn-rebuttal-push"
              style={{ fontSize: '11px', padding: '5px 12px' }}
              onClick={handlePushRecoveryToCRM}
            >
              📥 Push Intervention Plan to CRM
            </button>
            {crmNotice && <span className="action-notice-text text-emerald" style={{ fontSize: '11px', fontWeight: 600 }}>{crmNotice}</span>}
          </div>
        </div>
      )}

      {/* Scripted Talk Tracks */}
      <div className="talk-tracks-wrapper">
        <span className="talk-tracks-mini-header">SCRIPTED TALK TRACKS FOR NEXT CALL</span>

        <div className="talk-tracks-stack">
          {defaultTracks.map((track, i) => (
            <div key={i} className="talk-track-glass-card">
              <div className="track-top-bar">
                <span className="track-title-cyan">Pitch Option #{i + 1}</span>
                <button
                  className="btn-track-copy"
                  onClick={() => onCopy(track, `Pitch Option #${i + 1} copied to clipboard!`)}
                >
                  Copy
                </button>
              </div>
              <p className="track-speech-quote">"{track}"</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
