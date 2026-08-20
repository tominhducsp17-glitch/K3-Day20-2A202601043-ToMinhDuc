"""LangGraph workflow implementation."""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import setup_tracing

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph with LangGraph orchestration."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.supervisor = SupervisorAgent(max_iterations=self.settings.max_iterations)
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self.critic = CriticAgent()

    def build(self) -> Any:
        """Create and compile the LangGraph workflow graph."""
        graph = StateGraph(dict)

        # Define wrapper node functions
        def supervisor_node(state_dict: dict[str, Any]) -> dict[str, Any]:
            state = ResearchState.model_validate(state_dict)
            updated_state = self.supervisor.run(state)
            return updated_state.model_dump()

        def researcher_node(state_dict: dict[str, Any]) -> dict[str, Any]:
            state = ResearchState.model_validate(state_dict)
            updated_state = self.researcher.run(state)
            return updated_state.model_dump()

        def analyst_node(state_dict: dict[str, Any]) -> dict[str, Any]:
            state = ResearchState.model_validate(state_dict)
            updated_state = self.analyst.run(state)
            return updated_state.model_dump()

        def writer_node(state_dict: dict[str, Any]) -> dict[str, Any]:
            state = ResearchState.model_validate(state_dict)
            updated_state = self.writer.run(state)
            # Optionally run critic to review
            critiqued_state = self.critic.run(updated_state)
            return critiqued_state.model_dump()

        # Add nodes
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("researcher", researcher_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("writer", writer_node)

        # Set entry point
        graph.set_entry_point("supervisor")

        # Routing decision logic
        def route_condition(state_dict: dict[str, Any]) -> str:
            route_history = state_dict.get("route_history", [])
            if not route_history:
                return "researcher"
            last_decision = route_history[-1]
            if last_decision in ("researcher", "analyst", "writer"):
                return last_decision
            return "done"

        # Conditional edges from supervisor
        graph.add_conditional_edges(
            "supervisor",
            route_condition,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )

        # Edges back to supervisor from workers
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""
        setup_tracing()
        app = self.build()
        logger.info("Executing MultiAgentWorkflow graph for query: %s", state.request.query)

        initial_dict = state.model_dump()
        result_dict = app.invoke(initial_dict)

        final_state = ResearchState.model_validate(result_dict)
        logger.info(
            "Workflow finished with %d iterations. Route history: %s",
            final_state.iteration,
            " -> ".join(final_state.route_history),
        )
        return final_state
