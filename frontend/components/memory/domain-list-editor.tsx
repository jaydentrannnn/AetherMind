interface DomainListEditorProps {
  allowDomains: string[];
  denyDomains: string[];
  onAllowChange: (value: string[]) => void;
  onDenyChange: (value: string[]) => void;
}

export function DomainListEditor({
  allowDomains,
  denyDomains,
  onAllowChange,
  onDenyChange,
}: DomainListEditorProps): JSX.Element {
  const parse = (value: string): string[] =>
    value
      .split(",")
      .map((domain) => domain.trim())
      .filter(Boolean);

  return (
    <div className="card-surface space-y-4">
      <div>
        <h2 className="text-sm font-semibold">Allow domains</h2>
        <input
          className="mt-1 w-full rounded border bg-[var(--surface)] p-2 text-sm"
          defaultValue={allowDomains.join(",")}
          onBlur={(event) => onAllowChange(parse(event.target.value))}
          placeholder="comma separated"
          type="text"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          {allowDomains.map((domain) => (
            <span className="badge badge-neutral" data-testid="domain-chip" key={`allow-${domain}`}>
              {domain}
            </span>
          ))}
        </div>
      </div>
      <div>
        <h2 className="text-sm font-semibold">Deny domains</h2>
        <input
          className="mt-1 w-full rounded border bg-[var(--surface)] p-2 text-sm"
          data-testid="domain-list-add"
          defaultValue={denyDomains.join(",")}
          onBlur={(event) => onDenyChange(parse(event.target.value))}
          placeholder="comma separated"
          type="text"
        />
        <div className="mt-2 flex flex-wrap gap-2">
          {denyDomains.map((domain) => (
            <span className="badge badge-blocked" data-testid="domain-chip" key={`deny-${domain}`}>
              {domain}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
