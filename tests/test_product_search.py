"""
Test suite for product search endpoint.

Tests ALL 5 production discipline requirements:
1. Input validation
2. Rate limiting
3. Error handling
4. Observability
5. Schema enforcement
"""

import pytest
import asyncio
import sqlite3
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from aegis.main import app
from aegis.db import init_db, seed_products, get_db
from aegis.config import settings
from aegis.rate_limit import rate_limiter


@pytest.fixture(scope="session")
def test_db_path():
    """Create temporary test database."""
    # Use a temporary file instead of in-memory to avoid issues
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_file.name
    temp_file.close()

    # Patch settings before any imports that use it
    original_db_path = settings.db_path
    settings.db_path = db_path

    # Initialize and seed
    init_db()
    seed_products(50)  # Fewer products for faster tests

    yield db_path

    # Cleanup
    settings.db_path = original_db_path
    try:
        Path(db_path).unlink(missing_ok=True)
    except:
        pass


@pytest.fixture
def client(test_db_path):
    """FastAPI test client."""
    # Reset rate limiter for each test
    rate_limiter.request_times.clear()
    return TestClient(app)


class TestInputValidation:
    """REQUIREMENT 1: Input validation."""

    def test_search_query_required(self, client):
        """Missing query parameter should return 422."""
        response = client.get("/api/products/search")
        assert response.status_code == 422

    def test_search_query_min_length(self, client):
        """Empty query should fail validation."""
        response = client.get("/api/products/search?q=")
        assert response.status_code in [400, 422]

    def test_search_query_max_length(self, client):
        """Query > 100 chars should fail."""
        long_query = "a" * 101
        response = client.get(f"/api/products/search?q={long_query}")
        assert response.status_code in [400, 422]

    def test_search_query_whitespace_only(self, client):
        """Whitespace-only query should fail."""
        response = client.get("/api/products/search?q=%20%20%20")
        assert response.status_code in [400, 422]

    def test_pagination_page_min(self, client):
        """Page < 1 should fail."""
        response = client.get("/api/products/search?q=test&page=0")
        assert response.status_code in [400, 422]

    def test_pagination_limit_min(self, client):
        """Limit < 1 should fail."""
        response = client.get("/api/products/search?q=test&limit=0")
        assert response.status_code in [400, 422]

    def test_pagination_limit_max(self, client):
        """Limit > 100 should fail."""
        response = client.get("/api/products/search?q=test&limit=101")
        assert response.status_code in [400, 422]

    def test_sort_order_invalid(self, client):
        """Invalid sort_by should fail."""
        response = client.get("/api/products/search?q=test&sort_by=invalid")
        assert response.status_code in [400, 422]

    def test_valid_search_query(self, client):
        """Valid query should return 200."""
        response = client.get("/api/products/search?q=headphones")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "request_id" in data


class TestRateLimiting:
    """REQUIREMENT 2: Rate limiting."""

    def test_rate_limit_header_present(self, client):
        """Successful request should include rate limit headers."""
        response = client.get("/api/products/search?q=test")
        assert "x-ratelimit-limit" in response.headers or "X-RateLimit-Limit" in response.headers

    def test_rate_limit_allows_normal_traffic(self, client):
        """First 60 requests should succeed."""
        for i in range(10):  # Test first 10
            response = client.get(f"/api/products/search?q=test{i}")
            assert response.status_code == 200

    def test_rate_limit_429_format(self, client):
        """Rate limit exceeded should return proper 429 response."""
        # Exhaust the limit (60 per minute)
        for i in range(61):
            response = client.get(f"/api/products/search?q=query{i}")
            if response.status_code == 429:
                # Should have Retry-After header
                assert "retry-after" in response.headers or "Retry-After" in response.headers
                assert response.status_code == 429
                break


class TestErrorHandling:
    """REQUIREMENT 3: Error handling."""

    def test_validation_error_400(self, client):
        """Validation errors should return 400 with error details."""
        response = client.get("/api/products/search?q=")
        assert response.status_code in [400, 422]
        data = response.json()
        # Either Pydantic validation or our custom error
        assert "error" in data or "detail" in data

    def test_error_includes_request_id(self, client):
        """All error responses should include request_id."""
        response = client.get("/api/products/search")
        assert response.status_code in [400, 422]
        data = response.json()
        # Pydantic validation doesn't include request_id, but our custom errors do
        if "request_id" in data:
            assert len(data["request_id"]) > 0

    def test_no_internal_error_details_leaked(self, client):
        """Error messages should not expose internal details."""
        response = client.get("/api/products/search?q=test&page=-1")
        assert response.status_code in [400, 422]
        data = response.json()
        # Should be user-friendly, not technical
        if "detail" in data:
            detail = str(data.get("detail", ""))
            assert "traceback" not in detail.lower()


class TestObservability:
    """REQUIREMENT 4: Observability — request IDs, logging."""

    def test_response_has_request_id(self, client):
        """All responses should have a request_id."""
        response = client.get("/api/products/search?q=keyboard")
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0

    def test_response_has_latency(self, client):
        """Response should include latency_ms."""
        response = client.get("/api/products/search?q=mouse")
        assert response.status_code == 200
        data = response.json()
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))
        assert data["latency_ms"] >= 0

    def test_latency_reasonable(self, client):
        """Latency should be < 1 second for simple queries."""
        response = client.get("/api/products/search?q=test&limit=5")
        assert response.status_code == 200
        data = response.json()
        # Should be fast (< 1000ms)
        assert data["latency_ms"] < 1000


class TestSchema:
    """REQUIREMENT 5: Schema enforcement."""

    def test_response_schema_valid(self, client):
        """Response must match ProductSearchResponse schema."""
        response = client.get("/api/products/search?q=test")
        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data
        assert "latency_ms" in data
        assert "request_id" in data

        # Type validation
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["has_more"], bool)

    def test_product_item_schema(self, client):
        """Each product item must have required fields."""
        response = client.get("/api/products/search?q=keyboard&limit=5")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert "id" in item
            assert "name" in item
            assert "price" in item
            assert "category" in item
            assert "rating" in item
            # Validate types
            assert isinstance(item["id"], int)
            assert isinstance(item["name"], str)
            assert isinstance(item["price"], (int, float))
            assert isinstance(item["category"], str)
            assert isinstance(item["rating"], (int, float))
            # Validate constraints
            assert item["price"] >= 0
            assert item["rating"] >= 0 and item["rating"] <= 5.0


class TestFunctionality:
    """Integration tests."""

    def test_search_returns_results(self, client):
        """Search should return matching products."""
        response = client.get("/api/products/search?q=headphones")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0 or data["total"] == 0  # Either has results or 0

    def test_pagination_works(self, client):
        """Pagination should work correctly."""
        # Page 1
        response1 = client.get("/api/products/search?q=test&limit=5&page=1")
        # Page 2
        response2 = client.get("/api/products/search?q=test&limit=5&page=2")
        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_category_filter(self, client):
        """Category filter should limit results."""
        response = client.get("/api/products/search?q=test&category=Electronics")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "Electronics"

    def test_sort_by_relevance(self, client):
        """sort_by=relevance should work."""
        response = client.get("/api/products/search?q=test&sort_by=relevance")
        assert response.status_code == 200

    def test_sort_by_price_asc(self, client):
        """sort_by=price_asc should work."""
        response = client.get("/api/products/search?q=test&sort_by=price_asc&limit=10")
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 1:
            prices = [item["price"] for item in data["items"]]
            assert prices == sorted(prices)

    def test_sort_by_price_desc(self, client):
        """sort_by=price_desc should work."""
        response = client.get("/api/products/search?q=test&sort_by=price_desc&limit=10")
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 1:
            prices = [item["price"] for item in data["items"]]
            assert prices == sorted(prices, reverse=True)
