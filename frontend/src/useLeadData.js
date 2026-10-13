import { useCallback, useEffect, useState } from 'react';
import { apiRequest, createRequestGate } from './api';

export function useLeadData(id) {
  const [gate] = useState(createRequestGate);
  const [data, setData] = useState({ lead: null, interactions: [], battlecard: null, loading: true, scoreLoading: false, error: '', scoreError: '' });
  const path = `/leads/${encodeURIComponent(id)}`;

  const load = useCallback(async (generate = false) => {
    const request = gate.begin();
    try {
      const timeline = await apiRequest(`${path}/timeline`, { signal: request.signal });
      if (!request.isCurrent()) return;
      setData(previous => ({ ...previous, ...timeline, battlecard: null, loading: false, error: '', scoreLoading: true, scoreError: '' }));
      try {
        const battlecard = await apiRequest(`${path}/${generate ? 'sync' : 'battlecard'}`, {
          method: generate ? 'POST' : 'GET', signal: request.signal,
        });
        if (request.isCurrent()) setData(previous => ({ ...previous, battlecard, scoreLoading: false }));
      } catch (error) {
        if (request.isCurrent()) setData(previous => ({ ...previous, battlecard: null, scoreLoading: false, scoreError: error.message }));
      }
    } catch (error) {
      if (request.isCurrent()) setData(previous => ({ ...previous, lead: null, interactions: [], battlecard: null, loading: false, scoreLoading: false, error: error.message }));
    }
  }, [gate, path]);

  useEffect(() => {
    // The keyed workspace owns this request and cancels it on lead changes.
    let active = true;
    // Defer startup so React's development effect probe does not issue two requests.
    void Promise.resolve().then(() => { if (active) return load(); });
    return () => { active = false; gate.cancel(); };
  }, [load, gate]);

  async function save(changes) {
    const request = gate.begin();
    try {
      const lead = await apiRequest(path, { method: 'PATCH', body: JSON.stringify(changes), signal: request.signal });
      if (!request.isCurrent()) return null;
      setData(previous => ({ ...previous, lead, battlecard: null, scoreLoading: false, scoreError: 'Lead updated. Generate a score using the updated profile.' }));
      return lead;
    } catch (error) {
      if (request.isCurrent()) {
        setData(previous => ({ ...previous, scoreLoading: false }));
        throw error;
      }
      return null;
    }
  }

  const reload = useCallback(() => load(false), [load]);
  const sync = useCallback(() => {
    setData(previous => ({ ...previous, scoreLoading: true, scoreError: '' }));
    return load(true);
  }, [load]);
  return { ...data, reload, sync, save };
}
