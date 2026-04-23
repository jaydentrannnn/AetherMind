"use client";

import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Report } from "@/lib/types";
import { CitationPopover } from "./citation-popover";

const markdownComponents: Components = {
  a: ({ href, children, ...props }) => {
    const external = Boolean(href && /^https?:\/\//i.test(href));
    return (
      <a
        href={href}
        rel={external ? "noopener noreferrer" : undefined}
        target={external ? "_blank" : undefined}
        {...props}
      >
        {children}
      </a>
    );
  },
};

export function ReportContent({ report, markdown }: { report: Report; markdown: string }): JSX.Element {
  return (
    <article className="prose max-w-none">
      <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
        {markdown}
      </ReactMarkdown>
      <div className="mt-3 flex flex-wrap gap-2">
        {report.sources.slice(0, 6).map((source) => (
          <CitationPopover key={source.id} source={source} sourceId={source.id} />
        ))}
      </div>
    </article>
  );
}
