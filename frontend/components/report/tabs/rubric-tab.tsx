import type { Rubric } from "@/lib/types";

export function RubricTab({ rubric }: { rubric?: Rubric }): JSX.Element {
  return <pre className="overflow-auto rounded border p-3 text-xs">{JSON.stringify(rubric ?? {}, null, 2)}</pre>;
}
