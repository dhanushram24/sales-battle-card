import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom' });
after(async () => { await server.close(); });
const { DealHealthGauge } = await server.ssrLoadModule('/src/components/DealHealthGauge.jsx');
const { CompetitorRadar } = await server.ssrLoadModule('/src/components/CompetitorRadar.jsx');
const { RepActionCoPilot } = await server.ssrLoadModule('/src/components/RepActionCoPilot.jsx');
const { EditLeadModal, ProposalModal, SpotlightSearchModal } = await server.ssrLoadModule('/src/components/Modals.jsx');
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));

test('score panel stays visible during loading and failure', () => {
  assert.match(render(DealHealthGauge, { loading: true }), /Analyzing conversations/);
  assert.match(render(DealHealthGauge, { error: 'Connection failed', onRetry() {} }), /Connection failed/);
  assert.match(render(DealHealthGauge, { error: 'Connection failed', onRetry() {} }), /Generate score/);
});

test('zero score renders as zero and does not invent decomposition values', () => {
  const html = render(DealHealthGauge, { battlecard: { overall_score: 0 } });
  assert.match(html, />0\.0</);
  assert.doesNotMatch(html, />8\.8|>9\.2|Rajesh|Apex|high enthusiasm/);
});

test('insufficient evidence does not display a provisional score as readiness', () => {
  const html = render(DealHealthGauge, { battlecard: {
    overall_score: 5, purchase_outlook: 'insufficient_evidence', classification: 'Hot',
  } });
  assert.match(html, />N\/A</);
  assert.match(html, /More customer evidence is needed/);
  assert.doesNotMatch(html, />5\.0<|Hot/);
});

test('empty evidence does not generate fake competitor offers or talk tracks', () => {
  const html = render(CompetitorRadar, {}) + render(RepActionCoPilot, {});
  assert.doesNotMatch(html, /Salesforce|waive|Friday|35 sales|75\/user/);
  assert.match(html, /No competitor evidence/);
});

test('forms initialize from selected lead and proposals mark missing terms', () => {
  const first = render(EditLeadModal, { lead: { id: '1', name: 'Buyer A' } });
  const second = render(EditLeadModal, { lead: { id: '2', name: 'Buyer B' } });
  assert.match(first, /value="Buyer A"/);
  assert.match(second, /value="Buyer B"/);
  assert.doesNotMatch(second, /Buyer A/);
  assert.match(render(ProposalModal, { lead: { id: '2', name: 'Buyer B' } }), /Confirm approved pricing/);
});

test('search supports numeric IDs and missing profile fields', () => {
  const html = render(SpotlightSearchModal, { leads: [{ id: 123, name: null, company: null }] });
  assert.match(html, /123/);
  assert.match(html, /Unnamed contact/);
});
