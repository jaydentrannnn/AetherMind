"use client";

import type { Source } from "@/lib/types";
import { getSourceDisplayLabel, isExternalHttpUrl } from "@/lib/source-display";

export function CitationPopover({
  sourceId,
  source,
  chipLabel,
}: {
  sourceId: string;
  source?: Source;
  chipLabel?: string;
}): JSX.Element {
  const renderedChipLabel = chipLabel ?? (source ? getSourceDisplayLabel(source) : `[${sourceId}]`);

  if (!source) {
    return (
      <span className="rounded-full border px-2 py-0.5 text-xs text-unverified" data-testid="citation-chip">
        {renderedChipLabel}
      </span>
    );
  }

  const label = getSourceDisplayLabel(source);
  const isLinkable = isExternalHttpUrl(source.url);

  const tooltip = (
    <span className="pointer-events-none absolute left-0 top-6 z-20 hidden w-72 rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] p-3 text-xs group-hover:block">
      <span className="block font-semibold">{label}</span>
      <span className="mt-1 block text-[var(--text-dim)]">{source.domain}</span>
      <span className="mt-1 block line-clamp-3 text-[var(--text-muted)]">
        {source.snippet ?? "No snippet provided."}
      </span>
      <span className="mt-2 block text-[var(--text-dim)]">
        {source.verified ? "Verified" : "Unverified"}
      </span>
      <span className="mt-1 block text-[var(--text-dim)]">Source ID: {source.id}</span>
      {isLinkable ? (
        <span className="mt-1 block text-[var(--text-dim)]">Click chip to open source</span>
      ) : null}
    </span>
  );

  const chipClassName = "group relative inline-flex max-w-72 items-center rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-0.5 text-xs text-[var(--accent-token)]";

  if (isLinkable) {
    return (
      <a
        aria-label={`Open source ${label}`}
        className={`${chipClassName} cursor-pointer hover:underline`}
        data-testid="citation-chip"
        href={source.url}
        rel="noopener noreferrer"
        target="_blank"
      >
        <span className="truncate">{renderedChipLabel}</span>
        {tooltip}
      </a>
    );
  }

  return (
    <span className={`${chipClassName} cursor-help`} data-testid="citation-chip">
      <span className="truncate">{renderedChipLabel}</span>
      {tooltip}
    </span>
  );
}
