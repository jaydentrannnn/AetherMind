"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ResearchJobSummary } from "@/lib/types";

/**
 * Reports index: lists research jobs from GET /reports with links to each job’s report view.
 */
export default function ReportsIndexPage(): JSX.Element {
  const [rows, setRows] = useState<ResearchJobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async (): Promise<void> => {
      try {
        const list = await api.getReportsList(50);
        if (!cancelled) {
          setRows(list);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setRows(null);
          setError(err instanceof ApiError ? err.message : "Failed to load reports");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold">Reports</h1>
        <p className="text-sm text-[var(--text-muted)]">
          Open a research job to view its live trace, synthesized report, and versions.
        </p>
      </div>

      {error ? (
        <p className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] p-4 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      {rows === null && !error ? (
        <p className="text-sm text-[var(--text-muted)]">Loading…</p>
      ) : null}

      {rows && rows.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          No research jobs yet.{" "}
          <Link className="text-[var(--accent-token)] underline-offset-2 hover:underline" href="/">
            Start one from Research
          </Link>
          .
        </p>
      ) : null}

      {rows && rows.length > 0 ? (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li key={row.job_id}>
              <Link
                className="block rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-3 transition-colors hover:bg-[var(--surface-raised)]"
                href={`/reports/${row.job_id}`}
              >
                <div className="text-sm font-medium">{row.topic}</div>
                <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-[var(--text-dim)]">
                  <span>{row.status}</span>
                  <span>{row.created_at || "—"}</span>
                  {row.latest_report_id ? <span>Report saved</span> : <span>In progress or pending</span>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
