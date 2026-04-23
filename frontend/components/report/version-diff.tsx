"use client";

import { useMemo } from "react";
import { diff_match_patch } from "diff-match-patch";

export function VersionDiff({ previous, current }: { previous: string; current: string }): JSX.Element {
  const html = useMemo(() => {
    const dmp = new diff_match_patch();
    const diffs = dmp.diff_main(previous, current);
    dmp.diff_cleanupSemantic(diffs);
    return diffs
      .map(([op, text]) => {
        if (op === -1) return `<del>${text}</del>`;
        if (op === 1) return `<ins>${text}</ins>`;
        return `<span>${text}</span>`;
      })
      .join("");
  }, [previous, current]);

  return (
    <div
      className="prose max-w-none rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)]/30 p-3 [&_del]:bg-red-500/15 [&_del]:text-[var(--text)] [&_ins]:bg-emerald-500/15 [&_ins]:text-[var(--text)]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
