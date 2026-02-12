"""
Observability layer — request IDs, structured logging, tracing.

This module enforces that every request is traceable without access to the database.
Makes it possible to debug production issues from logs alone.
"""

import uuid
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger("aegis1.search")


def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return str(uuid.uuid4())


def log_search_request(
    request_id: str,
    query: str,
    page: int,
    limit: int,
    category: Optional[str],
    client_ip: str,
) -> None:
    """
    Log structured data about a search request.

    Structured logging means fields are separated, not concatenated strings.
    This allows log aggregation systems (Splunk, DataDog, CloudWatch) to index
    and search on individual fields.
    """
    logger.info(
        "Search request started",
        extra={
            "request_id": request_id,
            "query": query[:100],  # Truncate long queries
            "page": page,
            "limit": limit,
            "category": category,
            "client_ip": client_ip,
        },
    )


def log_search_response(
    request_id: str,
    query: str,
    result_count: int,
    total_count: int,
    latency_ms: float,
    category: Optional[str] = None,
    sort_by: str = "relevance",
) -> None:
    """Log structured data about search response."""
    logger.info(
        "Search request completed",
        extra={
            "request_id": request_id,
            "query": query[:100],
            "result_count": result_count,
            "total_count": total_count,
            "latency_ms": round(latency_ms, 2),
            "category": category,
            "sort_by": sort_by,
        },
    )


def log_search_error(
    request_id: str,
    query: str,
    error_type: str,
    error_message: str,
    latency_ms: float,
) -> None:
    """Log search endpoint errors."""
    logger.error(
        "Search request failed",
        extra={
            "request_id": request_id,
            "query": query[:100],
            "error_type": error_type,
            "error_message": error_message,
            "latency_ms": round(latency_ms, 2),
        },
        exc_info=False,  # Don't include traceback for validation errors
    )


def log_validation_error(
    request_id: str,
    field: str,
    value: str,
    reason: str,
) -> None:
    """Log input validation errors (no stack trace needed)."""
    logger.warning(
        "Search validation failed",
        extra={
            "request_id": request_id,
            "field": field,
            "value": value[:50] if value else None,
            "reason": reason,
        },
    )


class SearchLatencyTracker:
    """Track and record search latencies for observability."""

    def __init__(self, request_id: str, query: str):
        self.request_id = request_id
        self.query = query
        self.start_time = time.monotonic()
        self.stages: Dict[str, float] = {}

    def mark(self, stage: str) -> None:
        """Mark a stage completion."""
        elapsed_ms = (time.monotonic() - self.start_time) * 1000
        self.stages[stage] = elapsed_ms

    def total_ms(self) -> float:
        """Get total elapsed time in milliseconds."""
        return (time.monotonic() - self.start_time) * 1000

    def log_breakdown(self) -> None:
        """Log latency breakdown for debugging."""
        logger.debug(
            "Search latency breakdown",
            extra={
                "request_id": self.request_id,
                "query": self.query[:100],
                "stages": self.stages,
                "total_ms": round(self.total_ms(), 2),
            },
        )
