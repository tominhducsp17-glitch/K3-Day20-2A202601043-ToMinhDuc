"""Tracing hooks with LangSmith integration."""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    """Set up LangSmith or provider-specific tracing environment."""
    settings = get_settings()

    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langsmith_tracing else "false"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        os.environ["LANGSMITH_TRACING"] = "true" if settings.langsmith_tracing else "false"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        logger.info(
            "LangSmith tracing enabled for project: %s",
            settings.langsmith_project,
        )


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Span context for tracing execution durations and payloads."""
    setup_tracing()
    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": None,
    }
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
