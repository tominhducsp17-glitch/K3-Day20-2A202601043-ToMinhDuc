# Multi-Agent Research System Design Document

## Problem

Xây dựng một trợ lý nghiên cứu tự động (**Autonomous Research Assistant**) có khả năng tiếp nhận các truy vấn kỹ thuật chuyên sâu, tự động tìm kiếm nguồn thông tin tin cậy trên internet, phân tích và phản biện các góc nhìn, sau đó tổng hợp thành báo cáo hoàn chỉnh có trích dẫn nguồn rõ ràng và được chấm điểm chất lượng.

## Why Multi-Agent?

Single-Agent thường gặp hiện tượng "lost-in-the-middle", dễ sinh ảo giác (hallucination), trích dẫn nguồn không chính xác hoặc bỏ sót các phân tích đối sánh khi phải thực hiện quá nhiều tác vụ (tìm kiếm, đánh giá, tổng hợp, trích dẫn) trong cùng một ngữ cảnh prompt. Phân tách thành kiến trúc Multi-Agent giúp:
- Chuyên biệt hóa trách nhiệm (Separation of Concerns).
- Tối ưu hóa context window cho từng nhiệm vụ.
- Thiết lập các chặng kiểm duyệt (Guardrails & Critic Verification).

## Agent Roles

| Agent | Responsibility | Input | Output | Failure Mode & Mitigation |
|---|---|---|---|---|
| **Supervisor** | Điều phối luồng làm việc, quyết định agent tiếp theo | `ResearchState` | Cập nhật `route_history` | *Lặp vô hạn:* Giới hạn `max_iterations=6`. |
| **Researcher** | Tìm kiếm web (Tavily), thu thập nguồn | `request.query` | `sources`, `research_notes` | *Nguồn rác/lỗi mạng:* Fallback mock synthesizer. |
| **Analyst** | Phân tích đối sánh, đánh giá độ tin cậy | `research_notes` | `analysis_notes` | *Bỏ sót phản biện:* System prompt chuyên sâu. |
| **Writer** | Soạn thảo báo cáo chuẩn, gắn trích dẫn | Notes & Sources | `final_answer` (với citations `[1]`, `[2]`) | *Sai số trích dẫn:* Đánh chỉ mục rõ ràng. |
| **Critic** | Thẩm định tính trung thực, chấm điểm 1-10 | `final_answer`, `sources` | `AgentResult` (Score & Findings) | *Đánh giá thiên vị:* Tiêu chuẩn rubric rõ ràng. |

## Shared State (`ResearchState`)

- `request`: Chứa câu hỏi nghiên cứu ban đầu (`ResearchQuery`).
- `iteration`: Số vòng lặp đã chạy (dùng cho guardrail).
- `route_history`: Lưu vết lịch sử chuyển giao giữa các agent.
- `sources`: Danh sách tài liệu thu thập được (`list[SourceDocument]`).
- `research_notes`: Bản ghi thô tổng hợp từ các nguồn tìm kiếm.
- `analysis_notes`: Báo cáo phân tích đối sánh của Analyst.
- `final_answer`: Báo cáo cuối cùng do Writer tạo ra.
- `agent_results`: Kết quả chi tiết và metadata (tokens, chi phí) của từng agent.
- `trace`: Lịch sử các sự kiện phục vụ tracing.

## Routing Policy

Luồng tuần tự có điều kiện được điều phối bởi Supervisor:
1. `Start` $\rightarrow$ `Supervisor`
2. Nếu chưa có `sources` $\rightarrow$ `Researcher` $\rightarrow$ `Supervisor`
3. Nếu chưa có `analysis_notes` $\rightarrow$ `Analyst` $\rightarrow$ `Supervisor`
4. Nếu chưa có `final_answer` $\rightarrow$ `Writer` $\rightarrow$ `Critic` $\rightarrow$ `Supervisor`
5. Nếu đã hoàn tất hoặc đạt `max_iterations` $\rightarrow$ `Done` (`END`).

## Guardrails

- **Max Iterations:** Cố định tối đa 6 vòng lặp.
- **Timeout:** 60 giây cho mỗi lượt gọi mạng.
- **Retry:** Tự động thử lại 3 lần với exponential backoff (`tenacity`).
- **Fallback:** Tự động chuyển sang cơ chế tổng hợp nội bộ nếu API bị gián đoạn.
- **Validation:** Pydantic schema kiểm tra chặt chẽ đầu vào/đầu ra.

## Benchmark Plan

- **Queries:** Các truy vấn kỹ thuật (e.g. GraphRAG state-of-the-art, Vector RAG vs GraphRAG).
- **Metrics:**
  1. *Latency (s)*: Thời gian phản hồi tổng thể.
  2. *Estimated Cost ($)*: Chi phí token ước tính.
  3. *Quality Score (0-10)*: Đánh giá chất lượng và độ sâu kỹ thuật.
  4. *Citation Coverage (%)*: Tỷ lệ nguồn được trích dẫn chính xác.
  5. *Failure Rate (%)*: Tỷ lệ lỗi trong quá trình thực thi.
