import React, { useState } from 'react';

export function DealSimulator({ battlecard, onSimulate, onLogAction, onCopy }) {
  const [discount, setDiscount] = useState(10);
  const [waiveSetup, setWaiveSetup] = useState(false);
  const [guaranteeSLA, setGuaranteeSLA] = useState(false);
  const [accelerateSprint, setAccelerateSprint] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState(null);
  const [crmNotice, setCrmNotice] = useState('');

  if (!battlecard || !Number.isFinite(battlecard.overall_score)) {
    return null;
  }

  const handleSimulate = async () => {
    if (!onSimulate) return;
    setSimulating(true);
    try {
      const res = await onSimulate({
        discount_percent: Number(discount),
        waive_setup_fees: Boolean(waiveSetup),
        guarantee_sla: Boolean(guaranteeSLA),
        shorten_onboarding_days: accelerateSprint ? 21 : 0
      });
      setResult(res);
    } catch {
      // simulation failure
    } finally {
      setSimulating(false);
    }
  };

  const handlePushOfferToCRM = async () => {
    if (!onLogAction || !result) return;
    try {
      await onLogAction(`Commercial Offer Simulated: Score +${result.score_delta} pts (${result.base_score} -> ${result.simulated_score}). Script: ${result.closing_pitch_script}`);
      setCrmNotice('Concession plan logged to CRM thread!');
      setTimeout(() => setCrmNotice(''), 3000);
    } catch {
      setCrmNotice('Failed to push to CRM.');
    }
  };

  return (
    <section className="card simulator-card">
      <div className="card-header">
        <div className="header-icon-title">
          <span className="card-icon simulator-icon">🧪</span>
          <h3 className="card-title">What-If Deal Strategy Simulator</h3>
        </div>
        <span className="count-tag" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', borderColor: 'rgba(99, 102, 241, 0.3)' }}>
          Phase 3 Semantic AI
        </span>
      </div>

      <p className="simulator-subtitle text-muted" style={{ fontSize: '13px', margin: '4px 0 16px' }}>
        Model commercial concessions against buyer friction to predict score lift and generate tailored closing scripts.
      </p>

      {/* Simulator Controls Grid */}
      <div className="simulator-controls-grid">
        <div className="sim-control-item">
          <div className="sim-slider-header">
            <label htmlFor="discountSlider" className="sim-label">Licensing Discount:</label>
            <strong className="sim-val text-cyan">{discount}%</strong>
          </div>
          <input
            id="discountSlider"
            type="range"
            min="0"
            max="30"
            step="5"
            value={discount}
            onChange={(e) => setDiscount(e.target.value)}
            className="sim-range-input"
          />
        </div>

        <div className="sim-toggles-stack">
          <label className="sim-checkbox-label">
            <input
              type="checkbox"
              checked={waiveSetup}
              onChange={(e) => setWaiveSetup(e.target.checked)}
            />
            <span>Waive CTI Telephony Gateway Setup Fee</span>
          </label>

          <label className="sim-checkbox-label">
            <input
              type="checkbox"
              checked={guaranteeSLA}
              onChange={(e) => setGuaranteeSLA(e.target.checked)}
            />
            <span>Guarantee 99.9% Uptime Carrier SLA</span>
          </label>

          <label className="sim-checkbox-label">
            <input
              type="checkbox"
              checked={accelerateSprint}
              onChange={(e) => setAccelerateSprint(e.target.checked)}
            />
            <span>Commit to 21-Day Accelerated Onboarding Sprint</span>
          </label>
        </div>
      </div>

      <div style={{ marginTop: '16px', display: 'flex', gap: '10px' }}>
        <button
          className="btn-modal-primary"
          onClick={handleSimulate}
          disabled={simulating}
        >
          {simulating ? 'Simulating Deal Impact...' : '⚡ Simulate Deal Trajectory'}
        </button>
      </div>

      {/* Simulation Result Presentation */}
      {result && (
        <div className="simulation-result-box" style={{ marginTop: '18px' }}>
          <div className="sim-header-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div>
              <span className="mini-header-text">PROJECTED DEAL HEALTH TRAJECTORY</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
                <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--emerald)' }}>
                  {result.simulated_score.toFixed(1)}/10
                </span>
                <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                  (Base: {result.base_score.toFixed(1)})
                </span>
                <span className="trend-badge-green" style={{ marginLeft: '4px' }}>
                  +{result.score_delta.toFixed(1)} pts
                </span>
              </div>
            </div>
            <span className="classification-badge hot">
              🔥 {result.simulated_outlook}
            </span>
          </div>

          <p className="sim-reaction-text" style={{ fontSize: '13px', color: 'var(--text-main)', marginBottom: '12px', background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid var(--primary)' }}>
            <strong>Predicted Buyer Reaction:</strong> {result.projected_buyer_reaction}
          </p>

          <div className="sim-script-card" style={{ background: 'rgba(99, 102, 241, 0.05)', border: '1px solid rgba(99, 102, 241, 0.25)', borderRadius: '8px', padding: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span className="track-title-cyan" style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>
                🗣️ Tailored Concession Closing Script
              </span>
              <button
                className="btn-track-copy"
                onClick={() => onCopy && onCopy(result.closing_pitch_script, 'Closing pitch script copied!')}
              >
                Copy Script
              </button>
            </div>
            <p className="track-speech-quote" style={{ margin: 0, fontSize: '13px', lineHeight: 1.5 }}>
              {result.closing_pitch_script}
            </p>
          </div>

          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className="btn-rebuttal-push"
              onClick={handlePushOfferToCRM}
            >
              📥 Push Concession Plan to CRM Thread
            </button>
            {crmNotice && <span className="action-notice-text text-emerald" style={{ fontSize: '12px', fontWeight: 600 }}>{crmNotice}</span>}
          </div>
        </div>
      )}
    </section>
  );
}

