# Lab 20: Multi-Agent Research System Starter

Starter repo cho bài lab **Multi-Agent Systems**: xây dựng hệ thống nghiên cứu gồm **Supervisor + Researcher + Analyst + Writer** và benchmark với single-agent baseline.

> Mục tiêu của repo này là cung cấp **production-grade skeleton** để học viên phát triển code cá nhân. Các phần logic quan trọng được để ở dạng `TODO` để học viên tự triển khai.

## Learning outcomes

Sau 2 giờ lab, học viên cần có thể:

1. Thiết kế role rõ ràng cho nhiều agent.
2. Xây dựng shared state đủ thông tin cho handoff.
3. Thêm guardrail tối thiểu: max iterations, timeout, retry/fallback, validation.
4. Trace được luồng chạy và giải thích agent nào làm gì.
5. Benchmark single-agent vs multi-agent theo quality, latency, cost.

## Architecture mục tiêu

```text
User Query
   |
   v
Supervisor / Router
   |------> Researcher Agent  -> research_notes
   |------> Analyst Agent     -> analysis_notes
   |------> Writer Agent      -> final_answer
   |
   v
Trace + Benchmark Report
```

## Cấu trúc repo

```text
.
├── src/multi_agent_research_lab/
│   ├── agents/              # Agent interfaces + skeletons
│   ├── core/                # Config, state, schemas, errors
│   ├── graph/               # LangGraph workflow skeleton
│   ├── services/            # LLM, search, storage clients
│   ├── evaluation/          # Benchmark/evaluation skeleton
│   ├── observability/       # Logging/tracing hooks
│   └── cli.py               # CLI entrypoint
├── configs/                 # YAML configs for lab variants
├── docs/                    # Lab guide, rubric, design notes
├── tests/                   # Unit tests for skeleton behavior
├── notebooks/               # Optional notebook entrypoint
├── scripts/                 # Helper scripts
├── .env.example             # Environment variables template
├── pyproject.toml           # Python project config
├── Dockerfile               # Containerized dev/runtime
└── Makefile                 # Common commands
```

## Quickstart

### 1. Tạo môi trường

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev,llm]"
cp .env.example .env
```

### 2. Cấu hình API keys

Mở `.env` và điền key cần thiết.

```bash
OPENAI_API_KEY=...
# optional
LANGSMITH_API_KEY=...
TAVILY_API_KEY=...
```

### 3. Chạy smoke test

```bash
make test
python -m multi_agent_research_lab.cli --help
```

### 4. Chạy baseline skeleton

```bash
python -m multi_agent_research_lab.cli baseline \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"
```

Lệnh này chỉ chạy khung baseline tối giản. Học viên cần tự triển khai logic LLM thực tế trong `src/multi_agent_research_lab/services/llm_client.py`.

### 5. Chạy multi-agent skeleton

```bash
python -m multi_agent_research_lab.cli multi-agent \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"
```

Mặc định lệnh sẽ báo các `TODO` cần làm. Đây là chủ đích của starter repo.

## Milestones trong 2 giờ lab

| Thời lượng | Milestone | File gợi ý |
|---:|---|---|
| 0-15' | Setup, chạy baseline skeleton | `cli.py`, `services/llm_client.py` |
| 15-45' | Build Supervisor / router | `agents/supervisor.py`, `graph/workflow.py` |
| 45-75' | Thêm Researcher, Analyst, Writer | `agents/*.py`, `core/state.py` |
| 75-95' | Trace + benchmark single vs multi | `observability/tracing.py`, `evaluation/benchmark.py` |
| 95-115' | Peer review theo rubric | `docs/peer_review_rubric.md` |
| 115-120' | Exit ticket | `docs/lab_guide.md` |

## Quy ước production trong repo

- Tách rõ `agents`, `services`, `core`, `graph`, `evaluation`, `observability`.
- Không hard-code API key trong code.
- Tất cả input/output chính dùng Pydantic schema.
- Có type hints, linting, formatting, unit test tối thiểu.
- Có logging/tracing hook ngay từ đầu.
- Không để agent chạy vô hạn: dùng `max_iterations`, `timeout_seconds`.
- Có benchmark report thay vì chỉ demo output đẹp.

## TODO chính cho học viên

Tìm trong code các marker:

```bash
grep -R "TODO(student)" -n src tests docs
```

Các phần học viên cần tự làm:

1. Implement LLM client.
2. Implement web/search client hoặc mock search source.
3. Implement routing decision trong Supervisor.
4. Implement từng worker agent.
5. Build LangGraph workflow.
6. Thêm tracing provider thật: LangSmith, Langfuse hoặc OpenTelemetry.
7. Viết benchmark report.

## Deliverables & Submission Summary

Hệ thống đã được hoàn thiện đầy đủ 100% theo các yêu cầu của Lab 20:

1. **GitHub Repo cá nhân:** Toàn bộ source code trong `src/multi_agent_research_lab/` (Supervisor, Researcher, Analyst, Writer, Critic, LangGraph Workflow, LLM & Search clients) đã hoàn thành, vượt qua 100% `pytest` và `ruff`.
2. **LangSmith Trace Evidence:**
   - **Public Trace URL:** [LangSmith Multi-Agent Execution Trace](https://smith.langchain.com/public/7aa75c6e-a3dc-4dda-9b40-72ecd1fdae83/r/01a01d55-be26-7831-802e-5c5767cae371?start_time=2026-08-20T04%3A02%3A33.638088Z)
   - **Run ID:** `01a01d55-be26-7831-802e-5c5767cae371`
   - **Trace Screenshot:**
   
   ![LangSmith Trace Evidence](reports/trace_evidence.png)

3. **Báo cáo Benchmark chi tiết:** Xem tại [`reports/benchmark_report.md`](reports/benchmark_report.md) (bao gồm bảng so sánh định lượng Latency, Cost, Quality, Citation Coverage, Failure Rate giữa Single-Agent vs Multi-Agent).
4. **Phân tích Failure Modes & Exit Ticket:** Đã hoàn thành trong [`reports/benchmark_report.md`](reports/benchmark_report.md) và [`docs/lab_guide.md`](docs/lab_guide.md).


## References

- Anthropic: Building effective agents — https://www.anthropic.com/engineering/building-effective-agents
- OpenAI Agents SDK orchestration/handoffs — https://developers.openai.com/api/docs/guides/agents/orchestration
- LangGraph concepts — https://langchain-ai.github.io/langgraph/concepts/
- LangSmith tracing — https://docs.smith.langchain.com/
- Langfuse tracing — https://langfuse.com/docs
