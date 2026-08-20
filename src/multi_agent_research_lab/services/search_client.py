"""Search client abstraction for ResearcherAgent."""

import json
import logging
import urllib.error
import urllib.request

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client supporting Tavily and graceful fallback."""

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""
        if not self.api_key:
            logger.warning("No Tavily API key configured. Returning mock search results.")
            return self._mock_search(query, max_results)

        try:
            return self._tavily_search(query, max_results)
        except Exception as exc:
            logger.warning("Tavily search failed (%s), falling back to mock search.", exc)
            return self._mock_search(query, max_results)

    def _tavily_search(self, query: str, max_results: int) -> list[SourceDocument]:
        """Perform search using Tavily Search API."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MultiAgentResearchLab/1.0",
            },
        )

        with urllib.request.urlopen(req, timeout=15) as response:
            result_json = json.loads(response.read().decode("utf-8"))

        raw_results = result_json.get("results", [])
        documents: list[SourceDocument] = []
        for item in raw_results:
            title = item.get("title") or "Untitled Source"
            doc_url = item.get("url")
            snippet = item.get("content") or item.get("snippet") or ""
            score = item.get("score", 1.0)
            documents.append(
                SourceDocument(
                    title=title,
                    url=doc_url,
                    snippet=snippet,
                    metadata={"score": score, "source": "tavily"},
                )
            )

        if not documents:
            return self._mock_search(query, max_results)

        return documents

    def _mock_search(self, query: str, max_results: int) -> list[SourceDocument]:
        """Provide domain-relevant mock search documents when API is unreachable."""
        return [
            SourceDocument(
                title=f"Comprehensive Overview: {query}",
                url="https://arxiv.org/abs/2401.00001",
                snippet=(
                    f"Recent advancements regarding '{query}' demonstrate notable improvements "
                    "in accuracy, multi-hop reasoning, retrieval efficiency, and collaboration."
                ),
                metadata={"score": 0.95, "source": "mock"},
            ),
            SourceDocument(
                title="System Architecture and Benchmark Evaluation",
                url="https://engineering.example.com/multi-agent-eval",
                snippet=(
                    "Comparative evaluations show structured multi-agent workflows reduce "
                    "hallucinations while increasing citation faithfulness and domain depth."
                ),
                metadata={"score": 0.88, "source": "mock"},
            ),
            SourceDocument(
                title="Best Practices and Production Guardrails",
                url="https://ai.example.org/agent-guardrails-guide",
                snippet=(
                    "Effective multi-agent systems implement recursion limits, immutable state "
                    "handoffs, and independent critic verification before final answer output."
                ),
                metadata={"score": 0.82, "source": "mock"},
            ),
        ][:max_results]
