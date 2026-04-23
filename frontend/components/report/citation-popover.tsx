"use client";

import type { Source } from "@/lib/types";

export function CitationPopover({ sourceId, source }: { sourceId: string; source?: Source }): JSX.Element {
  if (!source) {
    return (
      <span className="rounded-full border px-2 py-0.5 text-xs text-unverified" data-testid="citation-chip">
        [{sourceId}]
      </span>
    );
  }

  return (
    <span
      className="group relative inline-flex cursor-help rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-0.5 text-xs text-[var(--accent-token)]"
      data-testid="citation-chip"
    >
      [{sourceId.slice(0, 6)}]
      <span className="pointer-events-none absolute left-0 top-6 z-20 hidden w-72 rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] p-3 text-xs group-hover:block">
        <div className="font-semibold">{source.title}</div>
        <div className="mt-1 line-clamp-3 text-[var(--text-muted)]">{source.snippet ?? "No snippet provided."}</div>
        <div className="mt-2 text-[var(--text-dim)]">{source.verified ? "Verified" : "Unverified"}</div>
      </span>
    </span>
  );
}
