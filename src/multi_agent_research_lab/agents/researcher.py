"""Researcher agent implementation."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """You are an expert research agent.
Your mission is to analyze collected raw search snippets and synthesize concise research notes.
Focus on identifying:
1. Core definitions, background, and state-of-the-art concepts.
2. Key mechanisms, architectures, or empirical findings.
3. Relevant citations or source references ([Source 1], [Source 2], etc.).

Format your output clearly with markdown bullet points and source references."""


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = AgentName.RESEARCHER.value

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        logger.info("Researcher running search for query: '%s'", state.request.query)

        sources = self.search_client.search(
            query=state.request.query,
            max_results=state.request.max_sources,
        )
        state.sources = sources

        sources_context = []
        for i, src in enumerate(sources, 1):
            url_str = f" ({src.url})" if src.url else ""
            sources_context.append(f"[Source {i}]: {src.title}{url_str}\nSnippet: {src.snippet}")
        combined_sources = "\n\n".join(sources_context)

        user_prompt = (
            f"User Research Query: {state.request.query}\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Raw Sources Found:\n{combined_sources}\n\n"
            "Please generate detailed, structured research notes from these sources."
        )

        response = self.llm_client.complete(
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        state.research_notes = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=response.content,
                metadata={
                    "sources_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "researcher_completed",
            {"sources_count": len(sources), "cost_usd": response.cost_usd},
        )
        logger.info("Researcher completed. Extracted %d sources.", len(sources))
        return state
