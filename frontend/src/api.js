export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the backend. Start the server on port 8000, then retry.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => item.msg).join('; ') : `Request failed (${response.status}). Please retry.`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (data === null) throw new Error('The backend returned an invalid response. Please retry.');
  return data;
}

export function createRequestGate() {
  let version = 0;
  let controller;
  return {
    begin() {
      controller?.abort();
      controller = new AbortController();
      const current = ++version;
      return { signal: controller.signal, isCurrent: () => current === version };
    },
    cancel() { version++; controller?.abort(); },
  };
}

export async function loadAllLeads(signal) {
  const leads = [];
  for (let offset = 0; ; offset += 200) {
    const page = await apiRequest(`/leads?offset=${offset}&limit=200`, { signal });
    leads.push(...page.map(lead => ({ ...lead, id: String(lead.id) })));
    if (page.length < 200) return leads;
  }
}
