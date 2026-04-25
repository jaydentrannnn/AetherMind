import type { Source } from "@/lib/types";

const HTTP_URL_PATTERN = /^https?:\/\/\S+$/i;

/**
 * Returns a user-facing source label with graceful fallbacks.
 */
export function getSourceDisplayLabel(source: Pick<Source, "id" | "title" | "domain" | "url">): string {
  const title = source.title.trim();
  if (title && title.toLowerCase() !== "untitled source") {
    return title;
  }

  const domain = source.domain.trim();
  if (domain) {
    return domain;
  }

  const url = source.url.trim();
  if (url) {
    return url;
  }

  return `Source ${source.id.slice(0, 8)}`;
}

/**
 * Checks whether a URL string is an external HTTP(S) link.
 */
export function isExternalHttpUrl(url: string): boolean {
  return HTTP_URL_PATTERN.test(url.trim());
}
