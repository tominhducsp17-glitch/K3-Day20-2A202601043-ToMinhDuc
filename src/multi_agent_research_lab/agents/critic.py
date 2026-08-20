"""Critic agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """You are a rigorous factual critic and evaluation agent.
Your responsibility is to review the generated final answer against sources and research notes.

Evaluate:
1. Citation Faithfulness: Are citations ([1], [2], etc.) accurate and grounded in sources?
2. Completeness & Hallucination: Does the answer address the query without fabricating facts?
3. Quality Score: Rate the final answer on a scale of 1 to 10.

Format your output as:
Score: <number 1-10>
Findings: <bullet points>"""


class CriticAgent(BaseAgent):
    """Evaluates final answer quality, citation coverage, and factual grounding."""

    name = AgentName.CRITIC.value

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Evaluate `state.final_answer`."""
        logger.info("Critic reviewing final answer for query: '%s'", state.request.query)

        if not state.final_answer:
            logger.warning("No final answer found to review.")
            return state

        sources_summary = "\n".join(
            f"[{i}] {src.title}: {src.snippet[:200]}" for i, src in enumerate(state.sources, 1)
        )

        user_prompt = (
            f"Original Query: {state.request.query}\n\n"
            f"Retrieved Sources:\n{sources_summary}\n\n"
            f"Generated Final Answer:\n{state.final_answer}\n\n"
            "Please critique the answer for citation accuracy and assign a quality score (1-10)."
        )

        response = self.llm_client.complete(
            system_prompt=CRITIC_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "critic_completed",
            {"cost_usd": response.cost_usd},
        )
        logger.info("Critic completed review.")
        return state
