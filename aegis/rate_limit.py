"""
Rate limiting middleware for production discipline.

Implements: 60 requests per minute per IP address.
Prevents abuse of public endpoints like /api/products/search.

This is a simple in-memory implementation. For production at scale,
use Redis or a dedicated service.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status

logger = logging.getLogger("aegis1.rate_limit")


class RateLimiter:
    """Simple per-IP rate limiter — 60 requests per 60 seconds."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        # ip -> [(timestamp, ...)]
        self.request_times: Dict[str, List[float]] = defaultdict(list)

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For if present."""
        # If behind proxy
        if request.headers.get("x-forwarded-for"):
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        # Direct connection
        if request.client:
            return request.client.host
        # Fallback
        return "unknown"

    def is_allowed(self, client_ip: str) -> tuple[bool, int, int]:
        """
        Check if request is allowed.

        Returns:
            (is_allowed, remaining_requests, reset_seconds)
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries
        self.request_times[client_ip] = [
            t for t in self.request_times[client_ip] if t > cutoff
        ]

        current_count = len(self.request_times[client_ip])
        remaining = max(0, self.requests_per_minute - current_count)

        if current_count >= self.requests_per_minute:
            # Find when oldest request expires
            oldest = min(self.request_times[client_ip])
            reset_seconds = int(oldest + self.window_seconds - now + 1)
            logger.warning(
                "Rate limit exceeded for %s (%d requests in 60s)",
                client_ip,
                current_count,
            )
            return False, remaining, reset_seconds

        # Record this request
        self.request_times[client_ip].append(now)
        return True, remaining - 1, 0

    async def __call__(self, request: Request):
        """Middleware callable — raises 429 if limit exceeded."""
        client_ip = self.get_client_ip(request)
        allowed, remaining, reset_seconds = self.is_allowed(client_ip)

        if not allowed:
            logger.error(
                "Rate limit exceeded: %s, reset in %d seconds",
                client_ip,
                reset_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {reset_seconds} seconds.",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(reset_seconds),
                },
            )

        # Attach headers to response (via dependency)
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + 60),
        }


# Global instance
rate_limiter = RateLimiter(requests_per_minute=60)
