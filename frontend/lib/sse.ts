"use client";
/**
 * lib/sse.ts
 *
 * SSE client for GET /research/{job_id}/stream
 *
 * Features:
 *   - Exponential backoff reconnect (max 5 retries)
 *   - Abort on navigation via AbortController
 *   - Max event buffer to prevent memory blowup on huge traces
 *   - Event reducer producing AgentTraceState for React
 *   - Typed SSE envelope parsing with graceful fallback
 *
 * Usage (inside a React component or SWR hook):
 *
 *   const abortRef = useRef<AbortController>();
 *
 *   useEffect(() => {
 *     abortRef.current = new AbortController();
 *     const unsub = subscribeToJobStream(jobId, abortRef.current.signal, (state) => {
 *       setTraceState(state);
 *     });
 *     return () => {
 *       abortRef.current?.abort();
 *       unsub();
 *     };
 *   }, [jobId]);
 *
 * Versioned: v1 — April 2026
 */

import type { SSEEnvelope, SSEEventType, AgentTraceState } from './types';
import { useEffect, useRef, useState } from 'react';


// ─── Config ───────────────────────────────────────────────────────────────────

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';

const SSE_CONFIG = {
  /** Maximum events held in memory. Older events are dropped from the head. */
  MAX_BUFFER:       500,
  /** Base reconnect delay in ms */
  BACKOFF_BASE_MS:  1_000,
  /** Max reconnect delay in ms */
  BACKOFF_MAX_MS:   30_000,
  /** Max reconnect attempts before giving up */
  MAX_RETRIES:      5,
} as const;


// ─── Reducer ─────────────────────────────────────────────────────────────────

type TraceAction =
  | { type: 'CONNECTING' }
  | { type: 'CONNECTED' }
  | { type: 'EVENT';  payload: SSEEnvelope }
  | { type: 'DONE' }
  | { type: 'ERROR';  message: string }
  | { type: 'RESET' };

export function traceReducer(state: AgentTraceState, action: TraceAction): AgentTraceState {
  switch (action.type) {
    case 'RESET':
      return { events: [], status: 'idle' };

    case 'CONNECTING':
      return { ...state, status: 'connecting', errorMessage: undefined };

    case 'CONNECTED':
      return { ...state, status: 'streaming' };

    case 'EVENT': {
      const ev = action.payload;
      // Buffer management: drop oldest if over limit
      const events = state.events.length >= SSE_CONFIG.MAX_BUFFER
        ? [...state.events.slice(1), ev]
        : [...state.events, ev];
      return {
        ...state,
        events,
        // Surface trace_id from first envelope that contains one
        traceId: state.traceId ?? ev.trace_id,
      };
    }

    case 'DONE':
      return { ...state, status: 'done' };

    case 'ERROR':
      return { ...state, status: 'error', errorMessage: action.message };

    default:
      return state;
  }
}

export const initialTraceState: AgentTraceState = {
  events: [],
  status: 'idle',
};


// ─── SSE envelope parser ──────────────────────────────────────────────────────

const KNOWN_TYPES = new Set<SSEEventType>([
  'planner', 'researcher', 'tool', 'synthesizer',
  'guardrails', 'critic', 'revision', 'memory', 'done', 'error',
]);

function isAbortLikeError(err: unknown): boolean {
  if (err instanceof DOMException && err.name === 'AbortError') return true;
  if (typeof err !== 'object' || err === null) return false;
  const name = 'name' in err ? String(err.name) : '';
  const message = 'message' in err ? String(err.message) : '';
  return name === 'AbortError' || /abort/i.test(message);
}

function parseEnvelope(raw: string): SSEEnvelope | null {
  try {
    const parsed = JSON.parse(raw);
    // Graceful fallback: accept any object with a `type` field
    if (typeof parsed === 'object' && parsed !== null && 'type' in parsed) {
      const type: SSEEventType = KNOWN_TYPES.has(parsed.type) ? parsed.type : 'error';
      return {
        type,
        msg:      typeof parsed.msg === 'string'     ? parsed.msg     : JSON.stringify(parsed),
        ts:       typeof parsed.ts === 'number'      ? parsed.ts      : undefined,
        detail:   typeof parsed.detail === 'string'  ? parsed.detail  : undefined,
        latency:  typeof parsed.latency === 'string' ? parsed.latency : undefined,
        trace_id: typeof parsed.trace_id === 'string'? parsed.trace_id: undefined,
        langfuse_trace_url: typeof parsed.langfuse_trace_url === 'string'
          ? parsed.langfuse_trace_url : undefined,
      };
    }
    return null;
  } catch {
    console.warn('[sse] Failed to parse envelope:', raw.slice(0, 200));
    return null;
  }
}


// ─── ReadableStream-based SSE parser ─────────────────────────────────────────
// Using fetch + ReadableStream instead of EventSource for better abort control.

async function* readSSELines(
  response: Response,
  signal: AbortSignal,
): AsyncGenerator<string> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (!signal.aborted) {
      let done = false;
      let value: Uint8Array | undefined;
      try {
        ({ done, value } = await reader.read());
      } catch (err: unknown) {
        if (signal.aborted || isAbortLikeError(err)) break;
        throw err;
      }
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        // SSE: lines starting with "data:" carry event payloads
        if (line.startsWith('data:')) {
          yield line.slice(5).trim();
        }
      }
    }
  } finally {
    try {
      await reader.cancel();
    } catch (err: unknown) {
      if (!signal.aborted && !isAbortLikeError(err)) {
        console.warn('[sse] Failed to cancel stream reader:', err);
      }
    }
  }
}


// ─── Backoff ──────────────────────────────────────────────────────────────────

function backoffDelay(attempt: number): number {
  const jitter = Math.random() * 500;
  return Math.min(
    SSE_CONFIG.BACKOFF_BASE_MS * Math.pow(2, attempt) + jitter,
    SSE_CONFIG.BACKOFF_MAX_MS,
  );
}


// ─── Main subscription function ───────────────────────────────────────────────

/**
 * Subscribe to the SSE stream for a research job.
 *
 * @param jobId   - Research job ID
 * @param signal  - AbortSignal (abort on navigation / unmount)
 * @param onState - Called with updated AgentTraceState on every event
 * @returns       - Unsubscribe function (also call abort() on the controller)
 */
export function subscribeToJobStream(
  jobId: string,
  signal: AbortSignal,
  onState: (state: AgentTraceState) => void,
): () => void {
  let state: AgentTraceState = { ...initialTraceState };
  let cancelled = false;

  const dispatch = (action: TraceAction) => {
    state = traceReducer(state, action);
    onState(state);
  };

  const connect = async (attempt: number = 0) => {
    if (cancelled || signal.aborted) return;

    dispatch({ type: 'CONNECTING' });

    try {
      const res = await fetch(`${BASE_URL}/research/${jobId}/stream`, {
        signal,
        headers: { Accept: 'text/event-stream' },
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      dispatch({ type: 'CONNECTED' });

      for await (const line of readSSELines(res, signal)) {
        if (cancelled || signal.aborted) break;

        if (line === '[DONE]' || line === 'done') {
          dispatch({ type: 'DONE' });
          return;
        }

        const envelope = parseEnvelope(line);
        if (envelope) {
          dispatch({ type: 'EVENT', payload: envelope });
          if (envelope.type === 'done') {
            dispatch({ type: 'DONE' });
            return;
          }
          if (envelope.type === 'error') {
            dispatch({ type: 'ERROR', message: envelope.msg });
            return;
          }
        }
      }

      // Stream ended without explicit done — mark complete
      if (!signal.aborted) dispatch({ type: 'DONE' });

    } catch (err: unknown) {
      if (signal.aborted || cancelled) return;

      if (isAbortLikeError(err)) return;

      console.warn(`[sse] Connection error (attempt ${attempt}):`, err);

      if (attempt >= SSE_CONFIG.MAX_RETRIES) {
        dispatch({ type: 'ERROR', message: `Stream disconnected after ${attempt} retries` });
        return;
      }

      // Exponential backoff reconnect
      const delay = backoffDelay(attempt);
      console.info(`[sse] Reconnecting in ${Math.round(delay)}ms…`);
      await new Promise(r => setTimeout(r, delay));
      connect(attempt + 1);
    }
  };

  connect();

  return () => { cancelled = true; };
}


// ─── React hook ───────────────────────────────────────────────────────────────
// Paste this into your component tree. Requires React 18+.

/**
 * useJobStream — React hook wrapping subscribeToJobStream.
 *
 * import { useJobStream } from '@/lib/sse';
 * const { state } = useJobStream(jobId);
 *
 * Note: import React hooks directly in your component file;
 * this stub uses the global React namespace for portability.
 */
export function useJobStream(jobId: string | null): { state: AgentTraceState } {
  const [state, setState] = useState<AgentTraceState>(initialTraceState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!jobId) return;

    setState(initialTraceState);
    const controller = new AbortController();
    abortRef.current = controller;

    const unsub = subscribeToJobStream(jobId, controller.signal, setState);

    return () => {
      unsub();
      controller.abort();
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
    };
  }, [jobId]);

  return { state };
}
