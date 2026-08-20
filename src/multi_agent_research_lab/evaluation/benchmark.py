"""Benchmark execution and metric calculation for single-agent vs multi-agent."""

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def compute_citation_coverage(state: ResearchState) -> float:
    """Compute ratio of sources cited in the final answer."""
    if not state.sources or not state.final_answer:
        return 0.0

    cited_count = 0
    answer_text = state.final_answer.lower()

    for i, src in enumerate(state.sources, 1):
        # Check bracketed numeric citations [1], [2], etc.
        numeric_citation = f"[{i}]"
        title_snippet = src.title.lower()[:20] if len(src.title) > 20 else src.title.lower()

        if numeric_citation in state.final_answer or (
            title_snippet and title_snippet in answer_text
        ):
            cited_count += 1

    return min(1.0, cited_count / len(state.sources))


def compute_quality_score(state: ResearchState) -> float:
    """Compute overall quality score (0.0 - 10.0) from critic notes or structural heuristics."""
    if not state.final_answer or len(state.final_answer.strip()) < 50:
        return 0.0

    # Look for Critic agent score if available
    for res in state.agent_results:
        if res.agent == "critic":
            match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", res.content)
            if match:
                try:
                    return min(10.0, max(0.0, float(match.group(1))))
                except ValueError:
                    pass

    # Heuristic fallback score
    score = 6.0
    word_count = len(state.final_answer.split())
    if word_count >= 250:
        score += 1.5
    elif word_count >= 100:
        score += 0.5

    if re.search(r"\[\d+\]", state.final_answer):
        score += 1.5

    has_sections = "#" in state.final_answer
    has_refs = "reference" in state.final_answer.lower() or "source" in state.final_answer.lower()
    if has_sections and has_refs:
        score += 1.0

    return min(10.0, max(1.0, score))


def calculate_total_cost(state: ResearchState) -> float:
    """Sum up estimated cost from all agent interactions."""
    total_cost = 0.0
    for res in state.agent_results:
        cost = res.metadata.get("cost_usd")
        if cost and isinstance(cost, (int, float)):
            total_cost += float(cost)
    return total_cost


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Execute runner, measure metrics, and return final state with BenchmarkMetrics."""
    started = perf_counter()
    has_error = False
    try:
        state = runner(query)
        if not state.final_answer:
            has_error = True
    except Exception as exc:
        has_error = True
        state = ResearchState(
            request={"query": query},
            errors=[str(exc)],
        )

    latency = perf_counter() - started
    cost = calculate_total_cost(state)
    coverage = compute_citation_coverage(state)
    quality = compute_quality_score(state)
    failure_rate = 1.0 if has_error else 0.0

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        citation_coverage=coverage,
        failure_rate=failure_rate,
        notes=f"Iterations: {state.iteration}, Sources: {len(state.sources)}",
    )
    return state, metrics
