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

