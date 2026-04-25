"""Depth contract and deterministic profiles for the research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DepthLevel = Literal["quick", "standard", "deep"]
WebSearchDepth = Literal["basic", "advanced"]


@dataclass(frozen=True)
class DepthProfile:
    """Deterministic knobs used to enforce one depth tier."""

    planner_min_subquestions: int
    planner_max_subquestions: int
    search_max_results: int
    synth_target_sections_min: int
    synth_target_sections_max: int
    critic_min_markdown_chars: int
    critic_min_substantive_sections: int
    extra_revisions: int = 0
    web_search_depth: WebSearchDepth = "basic"


DEPTH_PROFILES: dict[DepthLevel, DepthProfile] = {
    "quick": DepthProfile(
        planner_min_subquestions=3,
        planner_max_subquestions=3,
        search_max_results=3,
        synth_target_sections_min=3,
        synth_target_sections_max=3,
        critic_min_markdown_chars=500,
        critic_min_substantive_sections=2,
        extra_revisions=0,
        web_search_depth="basic",
    ),
    "standard": DepthProfile(
        planner_min_subquestions=4,
        planner_max_subquestions=6,
        search_max_results=5,
        synth_target_sections_min=4,
        synth_target_sections_max=6,
        critic_min_markdown_chars=800,
        critic_min_substantive_sections=3,
        extra_revisions=0,
        web_search_depth="basic",
    ),
    "deep": DepthProfile(
        planner_min_subquestions=6,
        planner_max_subquestions=8,
        search_max_results=8,
        synth_target_sections_min=6,
        synth_target_sections_max=8,
        critic_min_markdown_chars=1400,
        critic_min_substantive_sections=5,
        extra_revisions=1,
        web_search_depth="advanced",
    ),
}


def normalize_depth(raw: str | None) -> DepthLevel:
    """Normalize a possibly-missing depth value to one supported tier."""
    if raw in DEPTH_PROFILES:
        return raw
    return "standard"


def profile_for_depth(depth: DepthLevel | str | None) -> DepthProfile:
    """Return the deterministic profile for the resolved depth tier."""
    return DEPTH_PROFILES[normalize_depth(depth if isinstance(depth, str) else None)]

