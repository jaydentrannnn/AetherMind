"""Unit tests for API payload transforms."""

from __future__ import annotations

from app.api import transforms
from app.schemas import Source


def test_source_to_ui_normalizes_raw_doi_to_clickable_url() -> None:
    """Raw DOI strings should become clickable doi.org URLs."""
    source = Source(
        id="src-doi-1",
        source_type="url",
        title=None,
        url_or_doi="10.1038/s41586-024-00001-0",
    )
    payload = transforms.source_to_ui(source)
    assert payload["url"] == "https://doi.org/10.1038/s41586-024-00001-0"
    assert payload["domain"] == "doi.org"
    assert payload["title"] == "doi.org"


def test_source_to_ui_normalizes_doi_host_without_scheme() -> None:
    """doi.org values without a scheme should be normalized to https links."""
    source = Source(
        id="src-doi-2",
        source_type="url",
        title="Nature paper",
        url_or_doi="doi.org/10.48550/arXiv.1706.03762",
    )
    payload = transforms.source_to_ui(source)
    assert payload["url"] == "https://doi.org/10.48550/arXiv.1706.03762"
    assert payload["domain"] == "doi.org"
    assert payload["title"] == "Nature paper"


def test_source_to_ui_keeps_http_link_and_domain() -> None:
    """Valid HTTP(S) URLs should pass through unchanged."""
    source = Source(
        id="src-web-1",
        source_type="web_search",
        title="Example",
        url_or_doi="https://example.com/path",
    )
    payload = transforms.source_to_ui(source)
    assert payload["url"] == "https://example.com/path"
    assert payload["domain"] == "example.com"
    assert payload["title"] == "Example"


def test_source_to_ui_falls_back_to_source_id_when_no_title_or_url() -> None:
    """Sources without title/domain/url should still render a readable fallback label."""
    source = Source(
        id="abcdef123456",
        source_type="url",
        title="Untitled Source",
        url_or_doi=None,
    )
    payload = transforms.source_to_ui(source)
    assert payload["url"] == ""
    assert payload["domain"] == ""
    assert payload["title"] == "Source abcdef12"
