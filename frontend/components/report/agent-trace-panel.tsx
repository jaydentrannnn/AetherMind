"use client";

import { useJobStream } from "@/lib/sse";
import type { AgentTraceState } from "@/lib/types";

/**
 * AgentTracePanel renders the live SSE stream for a research job.
 *
 * When `traceState` is provided the component reuses that state (avoids opening
 * a second SSE connection when the parent already subscribes). Otherwise it
 * subscribes on its own via `useJobStream`.
 */
export function AgentTracePanel({
  jobId,
  traceState,
}: {
  jobId: string;
  traceState?: AgentTraceState;
}): JSX.Element {
  const fallback = useJobStream(traceState ? null : jobId);
  const state = traceState ?? fallback.state;

  return (
    <aside className="card-surface h-[70vh] overflow-auto" data-testid="trace-panel">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Agent Trace</h3>
        <span className="text-xs text-[var(--text-muted)]">{state.status}</span>
      </div>
      <ul className="space-y-2">
        {state.events.map((event, index) => (
          <li
            className="rounded border border-[var(--border-subtle)] p-2 text-xs"
            data-testid="trace-event"
            key={`${event.type}-${index}`}
          >
            <div className="font-medium">{event.type}</div>
            <div className="text-[var(--text-muted)]">{event.msg}</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
