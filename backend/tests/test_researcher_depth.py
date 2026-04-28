"""Tests for depth-aware researcher tool kwargs."""

from __future__ import annotations

from app.agent.nodes.researcher import _tool_kwargs


def test_researcher_quick_uses_lower_search_caps() -> None:
    """Quick depth should lower search result budget and keep basic web depth."""
    web_kwargs = _tool_kwargs("web_search", "q", depth="quick")
    arxiv_kwargs = _tool_kwargs("arxiv_search", "q", depth="quick")
    assert web_kwargs is not None
    assert arxiv_kwargs is not None
    assert web_kwargs["max_results"] == 3
    assert web_kwargs["search_depth"] == "basic"
    assert arxiv_kwargs["max_results"] == 3


def test_researcher_deep_uses_higher_search_caps() -> None:
    """Deep depth should raise search result budget and use advanced web depth."""
    web_kwargs = _tool_kwargs("web_search", "q", depth="deep")
    arxiv_kwargs = _tool_kwargs("arxiv_search", "q", depth="deep")
    assert web_kwargs is not None
    assert arxiv_kwargs is not None
    assert web_kwargs["max_results"] == 8
    assert web_kwargs["search_depth"] == "advanced"
    assert arxiv_kwargs["max_results"] == 8


def test_fetch_url_kwargs_accepts_explicit_http_url() -> None:
    """fetch_url should pass through explicit HTTP(S) URLs."""
    fetch_kwargs = _tool_kwargs("fetch_url", "https://example.com/article", depth="standard")
    assert fetch_kwargs == {"url": "https://example.com/article"}


def test_fetch_url_kwargs_normalizes_bare_domain() -> None:
    """fetch_url should normalize bare domains to HTTPS."""
    fetch_kwargs = _tool_kwargs("fetch_url", "example.com/path", depth="standard")
    assert fetch_kwargs == {"url": "https://example.com/path"}


def test_fetch_url_kwargs_skips_plain_language_question() -> None:
    """fetch_url should be skipped when no URL-like token exists."""
    fetch_kwargs = _tool_kwargs(
        "fetch_url",
        "What are key findings about transformer scaling laws?",
        depth="standard",
    )
    assert fetch_kwargs is None


def test_pdf_loader_kwargs_accepts_pdf_url_and_rejects_plain_language() -> None:
    """pdf_loader should only route when a concrete PDF target is present."""
    pdf_kwargs = _tool_kwargs(
        "pdf_loader",
        "Read https://example.com/papers/attention.pdf for details.",
        depth="standard",
    )
    assert pdf_kwargs == {"path_or_url": "https://example.com/papers/attention.pdf"}

    skipped_kwargs = _tool_kwargs(
        "pdf_loader",
        "Summarize the main points from that report.",
        depth="standard",
    )
    assert skipped_kwargs is None

