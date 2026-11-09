import { useCallback, useEffect, useState } from 'react';
import { apiRequest, createRequestGate } from './api';

export function useLeadData(id) {
  const [gate] = useState(createRequestGate);
  const [data, setData] = useState({
    lead: null,
    interactions: [],
    battlecard: null,
    loading: true,
    scoreLoading: false,
    streamProgress: null,
    error: '',
    scoreError: ''
  });
  const path = `/leads/${encodeURIComponent(id)}`;

  const load = useCallback(async (generate = false) => {
    const request = gate.begin();
    try {
      const timeline = await apiRequest(`${path}/timeline`, { signal: request.signal });
      if (!request.isCurrent()) return;
      setData(previous => ({
        ...previous,
        ...timeline,
        battlecard: null,
        loading: false,
        error: '',
        scoreLoading: true,
        streamProgress: null,
        scoreError: ''
      }));

      if (generate) {
        // Real-Time Server-Sent Events (SSE) Stream
        try {
          const response = await fetch(`/api${path}/sync-stream`, { signal: request.signal });
          if (!response.ok) {
            throw new Error(`Sync stream connection failed (${response.status})`);
          }
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let finalBattlecard = null;
          let streamError = '';

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split('\n\n');
            buffer = chunks.pop() || '';

            for (const chunk of chunks) {
              const lines = chunk.split('\n');
              let eventType = 'message';
              let eventData = '';
              for (const line of lines) {
                if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                else if (line.startsWith('data: ')) eventData = line.slice(6).trim();
              }
              if (eventType === 'progress' && eventData) {
                try {
                  const p = JSON.parse(eventData);
                  if (request.isCurrent()) setData(prev => ({ ...prev, streamProgress: p }));
                } catch {}
              } else if (eventType === 'complete' && eventData) {
                try {
                  finalBattlecard = JSON.parse(eventData);
                } catch {}
              } else if (eventType === 'error' && eventData) {
                try {
                  const err = JSON.parse(eventData);
                  streamError = err.error || 'Analysis streaming failed.';
                } catch {}
              }
            }
          }

          if (streamError) throw new Error(streamError);
          if (request.isCurrent()) {
            setData(previous => ({
              ...previous,
              battlecard: finalBattlecard,
              scoreLoading: false,
              streamProgress: null
            }));
          }
        } catch (error) {
          if (request.isCurrent()) {
            setData(previous => ({
              ...previous,
              battlecard: null,
              scoreLoading: false,
              streamProgress: null,
              scoreError: error.message
            }));
          }
        }
      } else {
        // Standard cached read
        try {
          const battlecard = await apiRequest(`${path}/battlecard`, {
            method: 'GET',
            signal: request.signal,
          });
          if (request.isCurrent()) setData(previous => ({ ...previous, battlecard, scoreLoading: false }));
        } catch (error) {
          if (request.isCurrent()) setData(previous => ({ ...previous, battlecard: null, scoreLoading: false, scoreError: error.message }));
        }
      }
    } catch (error) {
      if (request.isCurrent()) {
        setData(previous => ({
          ...previous,
          lead: null,
          interactions: [],
          battlecard: null,
          loading: false,
          scoreLoading: false,
          streamProgress: null,
          error: error.message
        }));
      }
    }
  }, [gate, path]);

  useEffect(() => {
    let active = true;
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

  async function addActionPlan(note) {
    const request = gate.begin();
    try {
      const res = await apiRequest(`${path}/actions`, {
        method: 'POST',
        body: JSON.stringify({ note }),
        signal: request.signal
      });
      const timeline = await apiRequest(`${path}/timeline`, { signal: request.signal });
      if (request.isCurrent()) {
        setData(previous => ({ ...previous, ...timeline }));
      }
      return res;
    } catch (error) {
      if (request.isCurrent()) throw error;
      return null;
    }
  }

  async function simulateScenario(params) {
    const request = gate.begin();
    try {
      return await apiRequest(`${path}/simulate`, {
        method: 'POST',
        body: JSON.stringify(params),
        signal: request.signal
      });
    } catch (error) {
      if (request.isCurrent()) throw error;
      return null;
    }
  }

  async function getReengagementPackage() {
    const request = gate.begin();
    try {
      return await apiRequest(`${path}/reengage`, {
        method: 'POST',
        signal: request.signal
      });
    } catch (error) {
      if (request.isCurrent()) throw error;
      return null;
    }
  }

  const reload = useCallback(() => load(false), [load]);
  const sync = useCallback(() => {
    setData(previous => ({ ...previous, scoreLoading: true, streamProgress: { step: 'starting', message: 'Connecting to CRM & AI engine...', percent: 10 }, scoreError: '' }));
    return load(true);
  }, [load]);

  return { ...data, reload, sync, save, addActionPlan, simulateScenario, getReengagementPackage };
}
