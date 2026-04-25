"use client";

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Report } from "@/lib/types";
import { CitationPopover } from "./citation-popover";

const FENCED_CODE_BLOCK_PATTERN = /(```[\s\S]*?```)/g;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const ORDINAL_CITATION_PATTERN = /\[\s*(\d+)\s*\]/g;

function replaceInlineCitationCodes(
  markdown: string,
  sourceIdByLower: Map<string, string>,
  sourceOrdinalById: Map<string, number>,
  sourceIdByOrdinal: Map<number, string>,
): string {
  if (!markdown) {
    return markdown;
  }
  const hasUuidSources = sourceIdByLower.size > 0;
  const hasOrdinalSources = sourceIdByOrdinal.size > 0;
  if (!hasUuidSources && !hasOrdinalSources) {
    return markdown;
  }

  const alternation = hasUuidSources
    ? Array.from(sourceIdByLower.values())
        .sort((left, right) => right.length - left.length)
        .map(escapeRegExp)
        .join("|")
    : "";
  const uuidPattern = alternation
    ? new RegExp(
        `\\[(?:source(?:_id)?\\s*[:=]\\s*)?(${alternation})\\]|\\bsource(?:_id)?\\s*[:=]\\s*(${alternation})\\b`,
        "gi",
      )
    : null;

  return markdown
    .split(FENCED_CODE_BLOCK_PATTERN)
    .map((segment, index) => {
      if (index % 2 === 1) {
        return segment;
      }
      let next = segment;
      if (uuidPattern) {
        next = next.replace(uuidPattern, (match, bracketedId: string, prefixedId: string) => {
          const candidateId = (bracketedId || prefixedId || "").toLowerCase();
          const canonicalId = sourceIdByLower.get(candidateId);
          if (!canonicalId) return match;
          const ordinal = sourceOrdinalById.get(canonicalId);
          if (!ordinal) return match;
          return `[${ordinal}](/__source__/${encodeURIComponent(canonicalId)})`;
        });
      }
      if (hasOrdinalSources) {
        next = next.replace(ORDINAL_CITATION_PATTERN, (match, digits: string) => {
          const ordinal = Number.parseInt(digits, 10);
          const canonicalId = sourceIdByOrdinal.get(ordinal);
          if (!canonicalId) return match;
          return `[${ordinal}](/__source__/${encodeURIComponent(canonicalId)})`;
        });
      }
      return next;
    })
    .join("");
}

export function ReportContent({ report, markdown }: { report: Report; markdown: string }): JSX.Element {
  const sourceById = useMemo(
    () => new Map(report.sources.map((source) => [source.id, source])),
    [report.sources],
  );
  const sourceIdByLower = useMemo(
    () => new Map(report.sources.map((source) => [source.id.toLowerCase(), source.id])),
    [report.sources],
  );
  const sourceOrdinalById = useMemo(
    () => new Map(report.sources.map((source, index) => [source.id, index + 1])),
    [report.sources],
  );
  const sourceIdByOrdinal = useMemo(
    () => new Map(report.sources.map((source, index) => [index + 1, source.id])),
    [report.sources],
  );
  const renderedMarkdown = useMemo(
    () => replaceInlineCitationCodes(markdown, sourceIdByLower, sourceOrdinalById, sourceIdByOrdinal),
    [markdown, sourceIdByLower, sourceOrdinalById, sourceIdByOrdinal],
  );
  const markdownComponents = useMemo<Components>(
    () => ({
      a: ({ href, children, ...props }) => {
        if (href?.startsWith("/__source__/")) {
          const sourceId = decodeURIComponent(href.slice("/__source__/".length));
          const source = sourceById.get(sourceId);
          const ordinal = sourceOrdinalById.get(sourceId);
          return (
            <CitationPopover
              chipLabel={ordinal ? `[${ordinal}]` : `[${sourceId}]`}
              source={source}
              sourceId={sourceId}
            />
          );
        }
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
    }),
    [sourceById, sourceOrdinalById],
  );

  return (
    <article className="prose max-w-none">
      <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
        {renderedMarkdown}
      </ReactMarkdown>
    </article>
  );
}
