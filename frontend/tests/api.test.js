import { afterEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { apiRequest, createRequestGate, loadAllLeads } from '../src/api.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test('lead switch aborts old requests and rejects late results', () => {
  const gate = createRequestGate();
  const first = gate.begin();
  const next = gate.begin();
  assert.equal(first.signal.aborted, true);
  assert.equal(first.isCurrent(), false);
  assert.equal(next.isCurrent(), true);
  gate.cancel();
  assert.equal(next.signal.aborted, true);
  assert.equal(next.isCurrent(), false);
});

test('preserves zero scores and sends JSON updates', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/leads/1');
    assert.equal(options.method, 'PATCH');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.equal(JSON.parse(options.body).name, 'Changed');
    return Response.json({ overall_score: 0 });
  };
  assert.equal((await apiRequest('/leads/1', { method: 'PATCH', body: JSON.stringify({ name: 'Changed' }) })).overall_score, 0);
});

test('keeps backend failure actionable and rejects malformed responses', async () => {
  globalThis.fetch = async () => Response.json({ detail: 'Unable to save lead' }, { status: 503 });
  await assert.rejects(apiRequest('/leads/1'), /Unable to save lead/);
  globalThis.fetch = async () => new Response('<html>Proxy error</html>', { status: 502 });
  await assert.rejects(apiRequest('/leads/1'), /502/);
  globalThis.fetch = async () => new Response('<html>Invalid success</html>');
  await assert.rejects(apiRequest('/leads/1'), /invalid response/);
});

test('formats validation errors and preserves cancellation', async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ msg: 'Name required' }] }, { status: 422 });
  await assert.rejects(apiRequest('/leads/1'), /Name required/);
  globalThis.fetch = async () => { throw new DOMException('Cancelled', 'AbortError'); };
  await assert.rejects(apiRequest('/leads'), { name: 'AbortError' });
});

test('loads all lead pages and normalizes numeric IDs', async () => {
  const requested = [];
  globalThis.fetch = async url => {
    requested.push(url);
    return Response.json(url.includes('offset=0&') ? Array.from({ length: 200 }, (_, id) => ({ id })) : [{ id: 200 }]);
  };
  const leads = await loadAllLeads();
  assert.equal(leads.length, 201);
  assert.equal(leads[200].id, '200');
  assert.deepEqual(requested, ['/api/leads?offset=0&limit=200', '/api/leads?offset=200&limit=200']);
});
