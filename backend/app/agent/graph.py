"""LangGraph assembly for planner/research/synthesizer/critic/memory loop."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Literal

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agent.depth import normalize_depth
from app.agent.nodes.critic import critic_node
from app.agent.nodes.guardrails import guardrails_node
from app.agent.nodes.memory_writer import memory_writer_node
from app.agent.nodes.planner import planner_node
from app.agent.nodes.researcher import researcher_node
from app.agent.nodes.synthesizer import synthesizer_node
from app.agent.state import AgentState
from app.config import settings
from app.llm.router import Router, router as default_router


def _fan_out_from_plan(state: AgentState) -> list[Send]:
    """Create one researcher send call per planned sub-question."""
    depth = normalize_depth(state.get("depth"))
    return [
        Send(
            "researcher",
            {
                "topic": state["topic"],
                "depth": depth,
                "sub_question": sub_question,
            },
        )
        for sub_question in state.get("plan", [])
    ]


def _route_after_critic(
    state: AgentState,
) -> Literal["synthesizer", "memory_writer"] | list[Send]:
    """Return the next graph transition selected by the critic decision."""
    next_action = state.get("next_action", "memory_writer")
    if next_action == "researcher":
        return _fan_out_from_plan(state)
    if next_action not in {"synthesizer", "memory_writer"}:
        return "memory_writer"
    return next_action


async def _build_checkpointer() -> AsyncSqliteSaver:
    """Open an async SQLite connection and return an AsyncSqliteSaver."""
    checkpoint_path = Path(settings.AGENT_CHECKPOINT_PATH)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(checkpoint_path))
    return AsyncSqliteSaver(conn)


def build_graph(*, llm_router: Router | None = None, checkpointer: BaseCheckpointSaver | None = None):
    """Compile and return the phase-5 LangGraph with checkpointing.

    Pass an explicit checkpointer (e.g. InMemorySaver) in tests; production
    callers should await _build_checkpointer() and pass the result here.
    """
    selected_router = llm_router or default_router
    graph = StateGraph(AgentState)
    graph.add_node("planner", partial(planner_node, llm_router=selected_router))
    graph.add_node("researcher", researcher_node)
    graph.add_node("synthesizer", partial(synthesizer_node, llm_router=selected_router))
    graph.add_node("guardrails", partial(guardrails_node, llm_router=selected_router))
    graph.add_node("critic", partial(critic_node, llm_router=selected_router))
    graph.add_node("memory_writer", memory_writer_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", _fan_out_from_plan, ["researcher"])
    graph.add_edge("researcher", "synthesizer")
    graph.add_edge("synthesizer", "guardrails")
    graph.add_edge("guardrails", "critic")
    graph.add_conditional_edges("critic", _route_after_critic)
    graph.add_edge("memory_writer", END)

    return graph.compile(checkpointer=checkpointer)
