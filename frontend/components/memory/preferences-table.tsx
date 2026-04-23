import type { Preference } from "@/lib/types";

interface PreferencesTableProps {
  preferences: Preference[];
  onChange: (preferences: Preference[]) => void;
}

export function PreferencesTable({ preferences, onChange }: PreferencesTableProps): JSX.Element {
  return (
    <div className="card-surface">
      <h2 className="mb-3 text-sm font-semibold">Preferences</h2>
      <div className="space-y-2">
        {preferences.map((preference, index) => (
          <div className="grid grid-cols-[1fr_2fr_auto] gap-2" data-testid="preference-row" key={`${preference.key}-${index}`}>
            <input
              className="rounded border bg-[var(--surface)] p-2 text-sm"
              onChange={(event) =>
                onChange(
                  preferences.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, key: event.target.value } : item,
                  ),
                )
              }
              value={preference.key}
            />
            <input
              className="rounded border bg-[var(--surface)] p-2 text-sm"
              onChange={(event) =>
                onChange(
                  preferences.map((item, itemIndex) =>
                    itemIndex === index ? { ...item, value: event.target.value } : item,
                  ),
                )
              }
              value={preference.value}
            />
            <span className="badge badge-neutral self-center">{preference.source}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
