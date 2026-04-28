"""Fixture loading helpers for offline eval runs."""

from __future__ import annotations

import json
from pathlib import Path

from app.eval.models import EvalFixtureCase


def default_fixtures_path() -> Path:
    """Return the canonical smoke-fixture path shipped with the eval package."""
    return Path(__file__).resolve().parent / "fixtures" / "smoke.json"


def load_fixtures(path: str | Path, *, max_cases: int | None = None) -> list[EvalFixtureCase]:
    """Load and validate eval fixture cases from JSON file."""
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Fixture file must contain a top-level JSON array")
    cases = [EvalFixtureCase.model_validate(item) for item in payload]
    if max_cases is not None and max_cases >= 0:
        return cases[:max_cases]
    return cases
