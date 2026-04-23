import type { RecalledMemory } from "@/lib/types";

interface SemanticSearchPanelProps {
  query: string;
  results: RecalledMemory[];
  onQueryChange: (value: string) => void;
  onSearch: () => void;
}

export function SemanticSearchPanel({
  query,
  results,
  onQueryChange,
  onSearch,
}: SemanticSearchPanelProps): JSX.Element {
  return (
    <div className="card-surface">
      <h2 className="mb-2 text-sm font-semibold">Semantic search</h2>
      <div className="flex gap-2">
        <input
          className="w-full rounded border bg-[var(--surface)] p-2 text-sm"
          data-testid="memory-search-input"
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search past reports..."
          value={query}
        />
        <button className="rounded border px-3 py-1 text-sm" onClick={onSearch} type="button">
          Search
        </button>
      </div>
      <ul className="mt-3 space-y-2">
        {results.map((result) => (
          <li className="rounded border p-2 text-sm" data-testid="memory-search-result" key={result.id}>
            <div className="font-medium">{result.title}</div>
            <div className="text-xs text-[var(--text-muted)]">{result.snippet}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
