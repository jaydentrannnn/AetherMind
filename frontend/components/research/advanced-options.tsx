"use client";

import { useState } from "react";

type Depth = "quick" | "standard" | "deep";
type ToolsState = { web: boolean; arxiv: boolean; pdf: boolean; url: boolean; code: boolean };

interface AdvancedOptionsProps {
  depth: Depth;
  tools: ToolsState;
  domains: string[];
  onDepthChange: (value: Depth) => void;
  onToolsChange: (value: ToolsState) => void;
  onDomainsChange: (value: string[]) => void;
}

export function AdvancedOptions({
  depth,
  tools,
  domains,
  onDepthChange,
  onToolsChange,
  onDomainsChange,
}: AdvancedOptionsProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const [domainInput, setDomainInput] = useState("");
  const depthLabels: Depth[] = ["quick", "standard", "deep"];

  const addDomain = (): void => {
    const value = domainInput.trim().replace(/^https?:\/\//, "").split("/")[0];
    if (!value || domains.includes(value)) return;
    onDomainsChange([...domains, value]);
    setDomainInput("");
  };

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-4">
      <button className="text-sm font-medium" onClick={() => setOpen((prev) => !prev)} type="button">
        Advanced options ({depth})
      </button>
      {open ? (
        <div className="mt-4 space-y-4">
          <label className="block text-sm">
            Depth
            <input
              className="mt-2 w-full"
              max={2}
              min={0}
              onChange={(event) => onDepthChange(depthLabels[Number(event.target.value)])}
              step={1}
              type="range"
              value={depthLabels.indexOf(depth)}
            />
          </label>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            {Object.entries(tools).map(([key, enabled]) => (
              <label className="flex items-center gap-2 text-sm" key={key}>
                <input
                  checked={enabled}
                  onChange={(event) =>
                    onToolsChange({ ...tools, [key]: event.target.checked } as ToolsState)
                  }
                  type="checkbox"
                />
                {key}
              </label>
            ))}
          </div>
          <div>
            <label className="text-sm">Preferred domains</label>
            <div className="mt-2 flex gap-2">
              <input
                className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-3 py-2 text-sm"
                onChange={(event) => setDomainInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === ",") {
                    event.preventDefault();
                    addDomain();
                  }
                }}
                placeholder="nature.com"
                value={domainInput}
              />
              <button className="rounded-md border px-3 py-2 text-sm" onClick={addDomain} type="button">
                Add
              </button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {domains.map((domain) => (
                <span
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] bg-[var(--surface-raised)] px-2 py-0.5 text-xs"
                  key={domain}
                >
                  {domain}
                  <button onClick={() => onDomainsChange(domains.filter((value) => value !== domain))} type="button">
                    x
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
