"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def run_single_agent_baseline(query_str: str) -> ResearchState:
    """Execute single-agent baseline equipped with search tool."""
    request = _parse_query(query_str)
    state = ResearchState(request=request)
    search_client = SearchClient()
    llm = LLMClient()

    # Step 1: Tool call - search web for sources
    sources = search_client.search(query=request.query, max_results=request.max_sources)
    state.sources = sources

    sources_context = []
    for i, src in enumerate(sources[:3], 1):
        url_str = f" ({src.url})" if src.url else ""
        sources_context.append(f"[{i}] {src.title}{url_str}\nSnippet: {src.snippet[:200]}")
    combined_sources = "\n\n".join(sources_context)

    # Step 2: Single-pass LLM prompt doing all research, analysis, and writing at once
    system_prompt = (
        "You are a single-agent research assistant with a web search tool. "
        "Review the retrieved search tool results and produce a concise answer with citations."
    )
    user_prompt = (
        f"Query: {request.query}\n\n"
        f"Search Results:\n{combined_sources}\n\n"
        "Please provide a complete research summary with inline citations and references list."
    )


    response = llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
    state.final_answer = response.content
    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=response.content,
            metadata={
                "tool_used": "SearchClient",
                "sources_count": len(sources),
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
    )
    state.iteration = 1
    state.record_route("single_agent_with_search")
    return state



def run_multi_agent_workflow(query_str: str) -> ResearchState:
    """Execute multi-agent workflow."""
    request = _parse_query(query_str)
    state = ResearchState(request=request)
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline LLM call."""
    _init()
    console.print(f"[bold cyan]Running Single-Agent Baseline for:[/bold cyan] {query}\n")

    started = perf_counter()
    state = run_single_agent_baseline(query)
    duration = perf_counter() - started

    console.print(
        Panel(
            state.final_answer or "No output",
            title="Single-Agent Baseline Response",
            border_style="green",
        )
    )
    console.print(f"[dim]Completed in {duration:.2f}s | Iteration: {state.iteration}[/dim]")


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the complete multi-agent workflow (Supervisor -> Researcher -> Analyst -> Writer)."""
    _init()
    console.print(f"[bold green]Running Multi-Agent Workflow for:[/bold green] {query}\n")

    started = perf_counter()
    state = run_multi_agent_workflow(query)
    duration = perf_counter() - started

    # Summary table
    table = Table(title="Execution Summary", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total Latency", f"{duration:.2f}s")
    table.add_row("Route History", " ➔ ".join(state.route_history))
    table.add_row("Sources Retrieved", str(len(state.sources)))
    table.add_row("Agent Iterations", str(state.iteration))

    console.print(table)
    console.print("\n")
    console.print(
        Panel(
            state.final_answer or "No output",
            title="Final Multi-Agent Answer",
            border_style="cyan",
        )
    )


@app.command()
def benchmark(
    query: Annotated[
        str,
        typer.Option("--query", "-q", help="Research query to benchmark"),
    ] = "Research GraphRAG state-of-the-art and write a 400-word summary with citations",
    output_file: Annotated[
        str,
        typer.Option("--output", "-o", help="Path to output markdown report"),
    ] = "reports/benchmark_report.md",
) -> None:
    """Benchmark Single-Agent vs Multi-Agent and save markdown report."""
    _init()
    console.print(f"[bold magenta]Starting Benchmark Comparison:[/bold magenta] {query}\n")

    console.print("[cyan]1/2 Running Single-Agent Baseline...[/cyan]")
    _, baseline_metrics = run_benchmark("Single-Agent Baseline", query, run_single_agent_baseline)

    console.print("[green]2/2 Running Multi-Agent Workflow...[/green]")
    _, multi_metrics = run_benchmark(
        "Multi-Agent (Supervisor+Researcher+Analyst+Writer)",
        query,
        run_multi_agent_workflow,
    )

    report_md = render_markdown_report([baseline_metrics, multi_metrics])

    # Append failure mode analysis and exit ticket
    additional_analysis = """
## 3. Failure Mode Analysis & Solutions

During multi-agent orchestration, several critical failure modes were identified and mitigated:

1. **Infinite Routing Loop (Supervisor <-> Researcher):**
   - *Failure Mode:* If a search yields empty results, the supervisor might loop infinitely.
   - *Mitigation:* Enforced strict `max_iterations=6` in `SupervisorAgent` with fallback.

2. **Context Dilution / Handoff Loss:**
   - *Failure Mode:* Crucial citations get lost passing large unstructured strings.
   - *Mitigation:* Enforced structured `ResearchState` schema with explicit typed fields.

3. **Rate Limiting & Network Glitches:**
   - *Failure Mode:* Transient 429 or timeouts when agents make sequential API calls.
   - *Mitigation:* Implemented `@retry` with exponential backoff using `tenacity`.

---

## 4. Exit Ticket Answers

### Question 1: Case nào NÊN dùng multi-agent? Vì sao?
> **Trả lời:**
> Nên dùng multi-agent cho các bài toán nghiên cứu sâu, phân tích phức tạp đa bước (Complex
> Research, Multi-perspective Synthesis, Fact Verification).
> **Lý do:** Tách biệt vai trò (Researcher tìm kiếm, Analyst phản biện, Writer biên tập) giúp mỗi
> prompt có context window gọn gàng, giảm thiểu "lost-in-the-middle" và hallucination, đồng thời
> chèn được guardrail và critic review ở từng giai đoạn.

### Question 2: Case nào KHÔNG NÊN dùng multi-agent? Vì sao?
> **Trả lời:**
> Không nên dùng multi-agent cho các tác vụ đơn giản, phản hồi thời gian thực cần độ trễ thấp
> (Single Q&A, Translation, Code Completion, Chatbot thông thường).
> **Lý do:** Multi-agent làm tăng độ trễ (nhiều LLM call tuần tự) và tăng chi phí token.
> Với tác vụ đơn giản, single-agent prompt tốt là hoàn toàn đủ và tối ưu hơn về kinh tế.
"""
    final_report = report_md + additional_analysis

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_report, encoding="utf-8")

    console.print(
        Panel.fit(
            f"Benchmark Report successfully written to [bold green]{output_file}[/bold green]",
            title="Benchmark Complete",
            style="green",
        )
    )
    console.print(final_report)


if __name__ == "__main__":
    app()
