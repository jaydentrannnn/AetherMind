import type { Source } from "@/lib/types";

export function SourcesTab({ sources }: { sources: Source[] }): JSX.Element {
  return (
    <div className="space-y-3">
      {sources.map((source) => (
        <div className="rounded border p-3" key={source.id}>
          <h4 className="font-medium">{source.title}</h4>
          <p className="text-xs text-[var(--text-muted)]">{source.url}</p>
        </div>
      ))}
    </div>
  );
}
