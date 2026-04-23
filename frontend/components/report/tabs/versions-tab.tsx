import type { ReportVersionMeta } from "@/lib/types";
import { VersionDiff } from "../version-diff";

export function VersionsTab({
  versions,
  markdown,
}: {
  versions: ReportVersionMeta[];
  markdown: string;
}): JSX.Element {
  return (
    <div className="space-y-3">
      <select className="rounded border bg-[var(--surface)] p-2 text-sm" data-testid="version-select">
        {versions.map((version) => (
          <option key={version.id} value={version.id}>
            {version.label}
          </option>
        ))}
      </select>
      <VersionDiff current={markdown} previous={versions[0]?.summary_diff ?? ""} />
    </div>
  );
}
