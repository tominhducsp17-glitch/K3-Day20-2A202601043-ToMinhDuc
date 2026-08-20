"""Supervisor / router implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = AgentName.SUPERVISOR.value

    def __init__(self, max_iterations: int | None = None) -> None:
        settings = get_settings()
        self.max_iterations = max_iterations or settings.max_iterations

    def decide_route(self, state: ResearchState) -> str:
        """Determine the next node to execute in the workflow."""
        if state.iteration >= self.max_iterations:
            logger.warning(
                "Max iterations (%d) reached. Routing to finalization/done guardrail.",
                self.max_iterations,
            )
            return "done"

        if not state.sources:
            return AgentName.RESEARCHER.value

        if not state.analysis_notes:
            return AgentName.ANALYST.value

        if not state.final_answer:
            return AgentName.WRITER.value

        return "done"

    def run(self, state: ResearchState) -> ResearchState:
        """Evaluate state and record next routing decision."""
        next_route = self.decide_route(state)
        state.record_route(next_route)
        state.add_trace_event(
            "supervisor_routing",
            {
                "decision": next_route,
                "iteration": state.iteration,
                "has_sources": bool(state.sources),
                "has_analysis": bool(state.analysis_notes),
                "has_answer": bool(state.final_answer),
            },
        )
        logger.info(
            "Supervisor (iter %d): next route -> %s",
            state.iteration,
            next_route,
        )
        return state
