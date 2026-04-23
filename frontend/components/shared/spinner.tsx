export function Spinner({ size = 14 }: { size?: number }): JSX.Element {
  return (
    <span
      className="inline-block animate-spin rounded-full border-2 border-[var(--accent-subtle)] border-t-[var(--accent-token)]"
      style={{ height: size, width: size }}
    />
  );
}
