"use client";

import type { Report } from "@/lib/types";

export function DiagnosticsFooter({ report }: { report: Report }): JSX.Element {
  const copy = (value?: string): void => {
    if (!value) return;
    void navigator.clipboard.writeText(value);
  };

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-[var(--border-subtle)] pt-3 text-xs text-[var(--text-dim)]">
      <span>Diagnostics</span>
      <span>· trace_id:</span>
      <button className="text-[var(--accent-token)]" onClick={() => copy(report.trace_id)} type="button">
        {report.trace_id ?? "n/a"}
      </button>
      <span>· req:</span>
      <button className="text-[var(--accent-token)]" onClick={() => copy(report.request_id)} type="button">
        {report.request_id ?? "n/a"}
      </button>
    </div>
  );
}
