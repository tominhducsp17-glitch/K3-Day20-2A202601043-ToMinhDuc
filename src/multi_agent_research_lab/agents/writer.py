"""Writer agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

WRITER_SYSTEM_PROMPT = """You are a senior technical author and synthesizer.
Your goal is to write a cohesive, concise final research summary based on notes.

Requirements:
1. Brief overview and key points.
2. Use bracketed numeric citations (e.g. [1], [2]).
3. Conclude with a short 'References' list."""


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = AgentName.WRITER.value

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""
        logger.info("Writer synthesizing final answer for query: '%s'", state.request.query)

        sources_summary = []
        for i, src in enumerate(state.sources[:3], 1):
            url_part = f" - URL: {src.url}" if src.url else ""
            sources_summary.append(f"[{i}] {src.title}{url_part}")
        sources_list_text = "\n".join(sources_summary) or "No external sources available."

        # Keep context concise to stay within token budgets
        res_notes = (state.research_notes or "N/A")[:600]
        ana_notes = (state.analysis_notes or "N/A")[:600]

        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Sources:\n{sources_list_text}\n\n"
            f"Research Notes:\n{res_notes}\n\n"
            f"Analysis Notes:\n{ana_notes}\n\n"
            "Write a concise final research report with [1], [2] citations and References list."
        )

        response = self.llm_client.complete(
            system_prompt=WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        state.final_answer = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "writer_completed",
            {"cost_usd": response.cost_usd},
        )
        logger.info("Writer completed synthesis.")
        return state
