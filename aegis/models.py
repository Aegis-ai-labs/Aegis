"""
Pydantic schemas for product search endpoints.

All input validation is defined here — this forces validation at the boundary,
making it impossible to skip. This is the cornerstone of production discipline.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


class SortOrder(str, Enum):
    """Valid sort orders for product search."""
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NAME = "name"


class PriceRange(BaseModel):
    """Price filter with validation."""
    min_price: Optional[float] = Field(default=0.0, ge=0.0)
    max_price: Optional[float] = Field(default=float('inf'), ge=0.0)

    @field_validator("max_price")
    @classmethod
    def max_must_exceed_min(cls, v: float, info) -> float:
        """Ensure max_price >= min_price."""
        if "min_price" in info.data and v < info.data["min_price"]:
            raise ValueError("max_price must be >= min_price")
        return v


class ProductSearchFilter(BaseModel):
    """Filters for product search — all validated."""
    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    price_range: Optional[PriceRange] = None

    @field_validator("category")
    @classmethod
    def category_alphanumeric(cls, v: str) -> str:
        """Prevent SQL injection via category."""
        if v is not None and not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("category must be alphanumeric (- and _ allowed)")
        return v


class ProductSearchRequest(BaseModel):
    """Validated search request — this is the security perimeter."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Search query text"
    )
    page: int = Field(default=1, ge=1, le=1000)
    limit: int = Field(default=10, ge=1, le=100)
    sort_by: SortOrder = Field(default=SortOrder.RELEVANCE)
    filters: Optional[ProductSearchFilter] = None

    @field_validator("query")
    @classmethod
    def query_not_just_spaces(cls, v: str) -> str:
        """Prevent empty queries disguised as spaces."""
        if not v.strip():
            raise ValueError("query cannot be empty or whitespace-only")
        return v.strip()


class ProductItem(BaseModel):
    """A single product in search results."""
    id: int = Field(..., description="Unique product ID")
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., ge=0.0)
    category: str = Field(..., min_length=1, max_length=50)
    rating: float = Field(..., ge=0.0, le=5.0)
    description: Optional[str] = Field(default=None)


class ProductSearchResponse(BaseModel):
    """API response for product search — structured + observable."""
    items: List[ProductItem] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total matching products")
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1, le=100)
    has_more: bool = Field(..., description="Whether more results exist")
    latency_ms: float = Field(..., description="Search execution time")
    request_id: str = Field(..., description="Unique request identifier for tracing")


class ErrorResponse(BaseModel):
    """Standard error response — no internal details leaked."""
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="User-facing error message")
    request_id: str = Field(..., description="For support debugging")
