"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ResearchJobSummary } from "@/lib/types";

const RECENT_LIMIT = 6;

/**
 * Sidebar-style list of the most recent research jobs from GET /reports.
 */
export function RecentResearchList(): JSX.Element {
  const [rows, setRows] = useState<ResearchJobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async (): Promise<void> => {
      try {
        const list = await api.getReportsList(RECENT_LIMIT);
        if (!cancelled) {
          setRows(list);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setRows([]);
          setError(err instanceof ApiError ? err.message : "Could not load recent jobs");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-xs uppercase tracking-wide text-[var(--text-dim)]">Recent</h2>
        <Link className="text-xs text-[var(--accent-token)] hover:underline" href="/reports">
          All reports
        </Link>
      </div>
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
      {rows === null && !error ? <p className="text-xs text-[var(--text-muted)]">Loading…</p> : null}
      {rows && rows.length === 0 && !error ? (
        <p className="text-xs text-[var(--text-muted)]">No jobs yet. Submit a topic above.</p>
      ) : null}
      {rows && rows.length > 0 ? (
        <div className="space-y-2">
          {rows.map((item) => (
            <Link
              className="block rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-2 hover:bg-[var(--surface-raised)]"
              href={`/reports/${item.job_id}`}
              key={item.job_id}
            >
              <div className="text-sm line-clamp-2">{item.topic}</div>
              <div className="text-xs text-[var(--text-dim)]">
                {item.status}
                {item.created_at ? ` · ${item.created_at.slice(0, 10)}` : ""}
              </div>
            </Link>
          ))}
        </div>
      ) : null}
    </section>
  );
}
