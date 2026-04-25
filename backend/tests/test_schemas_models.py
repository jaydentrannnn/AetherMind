"""Validation tests for Phase 3 schema models."""

from __future__ import annotations

import uuid

from app.schemas import Critique, Preference, Report, Rubric, Source, ToolResult


def test_report_round_trip_dump_and_validate() -> None:
    """Ensure report payloads serialize and validate without field loss."""
    report = Report(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        title="Latency tradeoffs",
        markdown="# Findings",
        sections=[],
    )
    dumped = report.model_dump()
    restored = Report.model_validate(dumped)
    assert restored.title == "Latency tradeoffs"
    assert restored.version == 1


def test_report_coerces_invalid_llm_uuid_fields_to_none() -> None:
    """Synthesis must not fail when the model emits fake UUID-looking strings."""
    report = Report.model_validate(
        {
            "id": "8f9a2b3c-4d5e-6f7g-8h9i-0j1k2l3m4n5o",
            "job_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
            "title": "Test",
            "markdown": "# Body",
            "sections": [],
        }
    )
    assert report.id is None
    assert report.job_id is None
    assert report.title == "Test"


def test_rubric_score_bounds_are_enforced() -> None:
    """Ensure rubric dimensions are constrained to the documented 0..5 range."""
    critique = Critique(
        score=4.0,
        approved=True,
        directives=["Ship as-is"],
        rubric=Rubric(
            accuracy=5,
            completeness=4,
            citation_integrity=4,
            bias=5,
            structure=5,
        ),
    )
    assert critique.rubric is not None
    assert critique.rubric.accuracy == 5


def test_preference_defaults_source_to_user() -> None:
    """Ensure preference records default to explicit user-supplied origin."""
    pref = Preference(user_id=uuid.uuid4(), key="tone", value="concise")
    assert pref.source == "user"


def test_tool_result_wraps_typed_source() -> None:
    """Ensure tool outputs carry a valid typed source payload."""
    source = Source(source_type="web_search", title="Example")
    result = ToolResult(content="ok", source=source)
    assert result.source.source_type == "web_search"
