import type { Source } from "@/lib/types";
import { getSourceDisplayLabel, isExternalHttpUrl } from "@/lib/source-display";

export function SourcesTab({ sources }: { sources: Source[] }): JSX.Element {
  return (
    <div className="space-y-3">
      {sources.map((source) => {
        const label = getSourceDisplayLabel(source);
        const isLinkable = isExternalHttpUrl(source.url);
        return (
          <div className="rounded border p-3" key={source.id}>
            <h4 className="font-medium">
              {isLinkable ? (
                <a
                  className="text-[var(--accent-token)] hover:underline"
                  data-testid="source-link"
                  href={source.url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {label}
                </a>
              ) : (
                label
              )}
            </h4>
            <p className="text-xs text-[var(--text-muted)]">{source.domain || "Unknown domain"}</p>
            <p className="text-xs text-[var(--text-dim)]">Source ID: {source.id}</p>
          </div>
        );
      })}
    </div>
  );
}
