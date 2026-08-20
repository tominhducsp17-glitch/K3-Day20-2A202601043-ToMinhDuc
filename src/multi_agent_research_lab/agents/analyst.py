"""Analyst agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """You are a critical analytical agent for deep technical evaluation.
Analyze research notes and source documents to extract structured insights:
1. Core Claims & Theses: What are the primary factual assertions?
2. Comparative Analysis: Compare viewpoints, methodologies, and trade-offs.
3. Evidence Strength & Verification: Evaluate whether claims are well-supported.
4. Gaps & Failure Modes: What is missing or needs caution?

Provide a structured, insightful analysis with explicit sections."""


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = AgentName.ANALYST.value

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""
        logger.info("Analyst evaluating research notes for query: '%s'", state.request.query)

        research_context = state.research_notes or "No research notes provided."
        user_prompt = (
            f"Original Query: {state.request.query}\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Synthesized Research Notes:\n{research_context}\n\n"
            "Please perform a deep technical analysis, comparing approaches and trade-offs."
        )

        response = self.llm_client.complete(
            system_prompt=ANALYST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        state.analysis_notes = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "analyst_completed",
            {"cost_usd": response.cost_usd},
        )
        logger.info("Analyst completed analysis.")
        return state
