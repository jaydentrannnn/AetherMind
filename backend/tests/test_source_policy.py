"""Tests for allow/deny source domain policy behavior."""

from __future__ import annotations

from app.guardrails.source_policy import SourcePolicy
from app.schemas import Source


def test_deny_suffix_blocks_subdomain() -> None:
    """Deny list entries should block matching subdomains."""
    source = Source(source_type="web_search", url_or_doi="https://foo.example.com/path")
    _, violations = SourcePolicy.filter_sources([source], allow=[], deny=["example.com"])
    assert len(violations) == 1
    assert violations[0].reason == "deny_match"


def test_allow_only_allows_listed_hosts() -> None:
    """Allow list should reject hosts not explicitly included."""
    source = Source(source_type="web_search", url_or_doi="https://other.com/path")
    _, violations = SourcePolicy.filter_sources([source], allow=["example.com"], deny=[])
    assert len(violations) == 1
    assert violations[0].reason == "not_in_allow"


def test_deny_wins_over_allow() -> None:
    """Deny matches should take precedence over allow matches."""
    source = Source(source_type="web_search", url_or_doi="https://example.com")
    _, violations = SourcePolicy.filter_sources([source], allow=["example.com"], deny=["example.com"])
    assert len(violations) == 1
    assert violations[0].reason == "deny_match"


def test_empty_policy_allows_source() -> None:
    """Empty allow/deny policies should permit valid host URLs."""
    source = Source(source_type="web_search", url_or_doi="https://example.com")
    allowed, violations = SourcePolicy.filter_sources([source], allow=[], deny=[])
    assert len(allowed) == 1
    assert violations == []


def test_invalid_url_records_violation() -> None:
    """Malformed URL strings should emit invalid_url policy violations."""
    source = Source(source_type="web_search", url_or_doi="not a url")
    _, violations = SourcePolicy.filter_sources([source], allow=[], deny=[])
    assert len(violations) == 1
    assert violations[0].reason == "invalid_url"
