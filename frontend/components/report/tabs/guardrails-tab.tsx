import type { GuardrailReport } from "@/lib/types";

export function GuardrailsTab({ guardrails }: { guardrails?: GuardrailReport }): JSX.Element {
  return <pre className="overflow-auto rounded border p-3 text-xs">{JSON.stringify(guardrails ?? {}, null, 2)}</pre>;
}
