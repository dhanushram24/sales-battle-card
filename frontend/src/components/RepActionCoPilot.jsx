import React from 'react';

export function RepActionCoPilot({ nextAction, talkTracks = [], onCopy }) {
  const defaultAction = nextAction || 'Generate a score to see the recommended next action.';
  const defaultTracks = talkTracks;

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
      </div>

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
