"""Source domain allow/deny policy helpers."""

from __future__ import annotations

from urllib.parse import urlparse

from app.schemas import PolicyViolation, Source


class SourcePolicy:
    """Evaluate source URLs against allow/deny host policies."""

    @staticmethod
    def _host(url: str | None) -> str:
        """Extract and normalize the hostname from a URL."""
        if not url:
            return ""
        return (urlparse(url).hostname or "").lower()

    @staticmethod
    def _matches(host: str, pattern: str) -> bool:
        """Return true when host equals or is a subdomain of pattern."""
        normalized_pattern = pattern.lower().lstrip(".")
        return host == normalized_pattern or host.endswith(f".{normalized_pattern}")

    @classmethod
    def is_allowed(cls, url: str | None, allow: list[str], deny: list[str]) -> bool:
        """Return whether a URL host passes deny-first allowlist policy."""
        host = cls._host(url)
        if not host:
            return False
        if any(cls._matches(host, entry) for entry in deny):
            return False
        if not allow:
            return True
        return any(cls._matches(host, entry) for entry in allow)

    @classmethod
    def filter_sources(
        cls,
        sources: list[Source],
        allow: list[str],
        deny: list[str],
    ) -> tuple[list[Source], list[PolicyViolation]]:
        """Split sources into policy-compliant entries and violation records."""
        allowed: list[Source] = []
        violations: list[PolicyViolation] = []
        for source in sources:
            host = cls._host(source.url_or_doi)
            if not host:
                violations.append(
                    PolicyViolation(
                        source_id=source.id,
                        url=source.url_or_doi,
                        reason="invalid_url",
                    )
                )
                continue
            if any(cls._matches(host, entry) for entry in deny):
                violations.append(
                    PolicyViolation(source_id=source.id, url=source.url_or_doi, reason="deny_match")
                )
                continue
            if allow and not any(cls._matches(host, entry) for entry in allow):
                violations.append(
                    PolicyViolation(source_id=source.id, url=source.url_or_doi, reason="not_in_allow")
                )
                continue
            allowed.append(source)
        return allowed, violations
# Allow/deny domains — guardrails (plan §7).
