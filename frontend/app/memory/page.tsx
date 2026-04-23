"use client";

import { useEffect, useMemo, useState } from "react";
import { DomainListEditor } from "@/components/memory/domain-list-editor";
import { PreferencesTable } from "@/components/memory/preferences-table";
import { SemanticSearchPanel } from "@/components/memory/semantic-search-panel";
import { api } from "@/lib/api";
import type { MemoryPreferences, Preference, RecalledMemory } from "@/lib/types";

function toPreferencesPayload(
  preferences: Preference[],
  allowDomains: string[],
  denyDomains: string[],
): MemoryPreferences {
  return {
    preferences,
    allow_domains: allowDomains,
    deny_domains: denyDomains,
  };
}

export default function MemoryPage(): JSX.Element {
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [allowDomains, setAllowDomains] = useState<string[]>([]);
  const [denyDomains, setDenyDomains] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RecalledMemory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setLoading(true);
      try {
        const prefs = await api.getPreferences();
        if (!cancelled) {
          setPreferences(prefs.preferences);
          setAllowDomains(prefs.allow_domains);
          setDenyDomains(prefs.deny_domains);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const payload = useMemo(
    () => toPreferencesPayload(preferences, allowDomains, denyDomains),
    [preferences, allowDomains, denyDomains],
  );

  const save = async (): Promise<void> => {
    await api.savePreferences(payload);
  };

  const search = async (): Promise<void> => {
    const response = await api.searchMemory(query);
    setResults(response.results);
  };

  if (loading) return <p>Loading memory...</p>;

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Memory & Preferences</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <PreferencesTable onChange={setPreferences} preferences={preferences} />
        <DomainListEditor
          allowDomains={allowDomains}
          denyDomains={denyDomains}
          onAllowChange={setAllowDomains}
          onDenyChange={setDenyDomains}
        />
      </div>
      <button className="rounded border px-3 py-1 text-sm" data-testid="preference-save" onClick={save} type="button">
        Save preferences
      </button>

      <SemanticSearchPanel onQueryChange={setQuery} onSearch={search} query={query} results={results} />
    </section>
  );
}
