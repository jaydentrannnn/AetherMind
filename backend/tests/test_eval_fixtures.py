"""Tests for eval fixture loading helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval.fixtures import load_fixtures


def _write_fixture(path: Path, payload: object) -> None:
    """Write JSON payload to a fixture file path."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_fixtures_reads_valid_cases(tmp_path: Path) -> None:
    """Loader should parse and validate JSON array fixture cases."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixture(
        fixture_path,
        [
            {
                "case_id": "1",
                "question": "q",
                "answer": "a",
                "contexts": ["ctx"],
                "citations": [{"source_id": "s1", "snippet": "ctx"}],
            }
        ],
    )
    rows = load_fixtures(fixture_path)
    assert len(rows) == 1
    assert rows[0].case_id == "1"


def test_load_fixtures_applies_max_cases(tmp_path: Path) -> None:
    """Loader should respect the max_cases limiter."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixture(
        fixture_path,
        [
            {"case_id": "1", "question": "q", "answer": "a"},
            {"case_id": "2", "question": "q", "answer": "a"},
        ],
    )
    rows = load_fixtures(fixture_path, max_cases=1)
    assert [row.case_id for row in rows] == ["1"]


def test_load_fixtures_requires_array_payload(tmp_path: Path) -> None:
    """Loader should fail on non-array JSON payloads."""
    fixture_path = tmp_path / "fixtures.json"
    _write_fixture(fixture_path, {"case_id": "x"})
    with pytest.raises(ValueError, match="top-level JSON array"):
        load_fixtures(fixture_path)
