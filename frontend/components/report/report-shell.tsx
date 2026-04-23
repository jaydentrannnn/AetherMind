"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useJobStream } from "@/lib/sse";
import type { Report, ReportVersionMeta } from "@/lib/types";
import { AgentTracePanel } from "./agent-trace-panel";
import { DiagnosticsFooter } from "./diagnostics-footer";
import { FeedbackForm } from "./feedback-form";
import { ReportContent } from "./report-content";
import { GuardrailsTab } from "./tabs/guardrails-tab";
import { RubricTab } from "./tabs/rubric-tab";
import { SourcesTab } from "./tabs/sources-tab";
import { VersionsTab } from "./tabs/versions-tab";

type ReportTab = "report" | "sources" | "guardrails" | "rubric" | "versions" | "feedback";

/** Event types that indicate the report has likely changed on the backend. */
const REFETCH_TRIGGER_TYPES = new Set(["synthesizer", "critic", "memory", "done"]);

export function ReportShell({ reportId }: { reportId: string }): JSX.Element {
  const [tab, setTab] = useState<ReportTab>("report");
  const [report, setReport] = useState<Report | null>(null);
  const [versions, setVersions] = useState<ReportVersionMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Single SSE subscription for the whole shell; AgentTracePanel receives state via prop.
  const { state: traceState } = useJobStream(reportId);
  const eventCount = traceState.events.length;
  const lastEventType = eventCount > 0 ? traceState.events[eventCount - 1].type : undefined;
  const streamStatus = traceState.status;

  // Refetch logic: runs on mount, on every new relevant SSE event, and once when the
  // stream ends. Polling falls back every 3s while the stream is still active so the
  // UI keeps refreshing even if the backend emits no intermediate events.
  type FetchResult = "ok" | "pending" | "error";
  const refetchRef = useRef<() => Promise<FetchResult>>(async () => "pending");

  const fetchOnce = useCallback(async (): Promise<FetchResult> => {
    try {
      const [reportResponse, versionsResponse] = await Promise.all([
        api.getReport(reportId),
        api.getReportVersions(reportId).catch(() => [] as ReportVersionMeta[]),
      ]);
      setReport(reportResponse);
      setVersions(versionsResponse);
      setLoading(false);
      setError(null);
      return "ok";
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return "pending";
      setError(err instanceof Error ? err.message : "Failed to load report");
      return "error";
    }
  }, [reportId]);

  refetchRef.current = fetchOnce;

  // Effect 1: initial load + polling until either the report exists or the stream finishes.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setReport(null);
    setError(null);

    const POLL_MS = 3_000;
    const poll = async (): Promise<void> => {
      while (!cancelled) {
        const result = await refetchRef.current();
        if (cancelled) return;
        if (result !== "pending") return; // ok or error — stop polling
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    };
    void poll();
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  // Effect 2: re-fetch whenever a relevant SSE event lands (new draft, critique, final).
  useEffect(() => {
    if (!lastEventType || !REFETCH_TRIGGER_TYPES.has(lastEventType)) return;
    void refetchRef.current();
  }, [eventCount, lastEventType]);

  // Effect 3: always do one final fetch when the stream terminates so the approved
  // version is shown even if we missed the last event.
  useEffect(() => {
    if (streamStatus === "done" || streamStatus === "error") {
      void refetchRef.current();
    }
  }, [streamStatus]);

  const markdown = useMemo(
    () =>
      report?.markdown ??
      report?.sections.map((section) => `## ${section.title}\n\n`).join("\n") ??
      "",
    [report],
  );

  if (loading && !report) {
    const progress = streamStatus === "streaming"
      ? `Agent running (${eventCount} events)…`
      : "Loading report…";
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <AgentTracePanel jobId={reportId} traceState={traceState} />
        <section className="card-surface min-h-[70vh] flex items-center justify-center text-sm text-[var(--text-muted)]">
          {progress}
        </section>
      </div>
    );
  }
  if (error && !report) return <p className="text-red-500">{error}</p>;
  if (!report) return <p className="text-red-500">Report not found</p>;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
      <AgentTracePanel jobId={report.job_id} traceState={traceState} />
      <section className="card-surface min-h-[70vh]">
        <div className="mb-4 flex flex-wrap gap-2">
          {(["report", "sources", "guardrails", "rubric", "versions", "feedback"] as const).map((candidate) => (
            <button
              className={`rounded px-3 py-1 text-sm ${tab === candidate ? "bg-[var(--surface-raised)]" : ""}`}
              key={candidate}
              onClick={() => setTab(candidate)}
              type="button"
            >
              {candidate}
            </button>
          ))}
        </div>
        {tab === "report" ? <ReportContent markdown={markdown} report={report} /> : null}
        {tab === "sources" ? <SourcesTab sources={report.sources} /> : null}
        {tab === "guardrails" ? <GuardrailsTab guardrails={report.guardrails} /> : null}
        {tab === "rubric" ? <RubricTab rubric={report.rubric} /> : null}
        {tab === "versions" ? <VersionsTab markdown={markdown} versions={versions} /> : null}
        {tab === "feedback" ? <FeedbackForm reportId={report.id} /> : null}
        <DiagnosticsFooter report={report} />
      </section>
    </div>
  );
}
