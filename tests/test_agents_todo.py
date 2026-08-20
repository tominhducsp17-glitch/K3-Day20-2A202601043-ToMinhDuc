"""Unit tests for agents and supervisor routing policy."""

from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    compute_citation_coverage,
    compute_quality_score,
)
from multi_agent_research_lab.services.search_client import SearchClient


def test_supervisor_routing_policy() -> None:
    """Test state-dependent routing decisions in SupervisorAgent."""
    supervisor = SupervisorAgent(max_iterations=6)

    # 1. New state without sources should route to researcher
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    assert supervisor.decide_route(state) == "researcher"
    state = supervisor.run(state)
    assert state.route_history[-1] == "researcher"

    # 2. State with sources but no analysis should route to analyst
    state.sources = [
        SourceDocument(
            title="GraphRAG Paper",
            snippet="Graph based RAG is effective.",
            url="https://example.com",
        )
    ]
    assert supervisor.decide_route(state) == "analyst"
    state = supervisor.run(state)
    assert state.route_history[-1] == "analyst"

    # 3. State with analysis but no final answer should route to writer
    state.analysis_notes = "Key claim: GraphRAG improves multi-hop synthesis."
    assert supervisor.decide_route(state) == "writer"
    state = supervisor.run(state)
    assert state.route_history[-1] == "writer"

    # 4. State with final answer should route to done
    state.final_answer = "Comprehensive summary with citations [1]."
    assert supervisor.decide_route(state) == "done"

    # 5. Guardrail test: exceeding max iterations stops the workflow
    state.iteration = 6
    assert supervisor.decide_route(state) == "done"


def test_search_client_fallback() -> None:
    """Test that search client returns valid SourceDocuments even in fallback."""
    client = SearchClient(api_key=None)
    results = client.search(query="Multi-Agent Systems", max_results=3)
    assert len(results) > 0
    assert isinstance(results[0], SourceDocument)
    assert results[0].title
    assert results[0].snippet


def test_citation_coverage_and_quality() -> None:
    """Test evaluation scoring metrics."""
    state = ResearchState(
        request=ResearchQuery(query="Multi-agent design patterns"),
        sources=[
            SourceDocument(
                title="Anthropic Agents",
                url="https://anthropic.com",
                snippet="Agent patterns",
            ),
            SourceDocument(
                title="LangGraph Docs",
                url="https://langchain.com",
                snippet="Graph workflow",
            ),
        ],
        final_answer=(
            "According to Anthropic Agents [1], workflows should have clear roles. "
            "LangGraph Docs [2] provide graphs."
        ),
    )
    coverage = compute_citation_coverage(state)
    assert coverage == 1.0

    score = compute_quality_score(state)
    assert score >= 7.0
