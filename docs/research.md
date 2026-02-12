# Research: Product Search Endpoint Implementation

## Current State Analysis

### Stack
- **Framework**: FastAPI 0.104+
- **Database**: SQLite with aiosqlite, WAL mode
- **Validation**: Pydantic 2.0+
- **Logging**: Python standard logging
- **Environment**: .env based config (pydantic-settings)

### Existing Patterns
1. **Health check & status endpoints** (/health, /api/status) exist
2. **WebSocket implementation** shows structured state management and logging
3. **Database layer**: sync sqlite3 in db.py, but project uses async elsewhere
4. **Error handling**: try/except with logging, no silent failures
5. **Observability**: Latency tracking with stats, detailed logging
6. **Config**: Environment-driven via pydantic-settings

### What's Missing for Production Search
1. **No search endpoint** exists yet
2. **No rate limiting middleware**
3. **No explicit input validation schemas** beyond what Pydantic provides
4. **No observability hooks** (request IDs, structured logging)
5. **No async DB queries** - db.py is sync only

## Production Discipline Requirements

### 1. Input Validation
- Search query string (required, length bounds)
- Pagination params (page, limit with reasonable defaults/max)
- Sort order (enum: relevance, price_asc, price_desc, name)
- Filters (category, price range) — all must be validated

### 2. Rate Limiting
- Need to prevent abuse: 60 searches per minute per IP
- Implement via middleware or decorator
- Include X-RateLimit-* headers in response

### 3. Error Handling
- Validation errors → 400 with schema
- DB errors → 500 with logging (no internal details exposed)
- Rate limit exceeded → 429
- All errors logged with context

### 4. Observability
- Request ID generated for tracking
- Structured logging (query, filters, results count, latency)
- Response includes debug headers (in dev mode)
- Latency metrics tracked

### 5. Schema
- Pydantic models for:
  - ProductSearchRequest (query, filters, pagination)
  - ProductItem (id, name, price, category, rating)
  - ProductSearchResponse (items, total, page, latency_ms)
- Database schema: products table with proper indexing

## Temptations to Resist (Baseline Shortcuts)

1. **Skip input validation** ("FastAPI validates automatically")
   - Reality: Only validates type; doesn't sanitize or enforce business rules
   - Temptation pressure: "Just need to ship by EOD, validation can wait"

2. **Skip rate limiting** ("We're behind a proxy")
   - Reality: Proxy may not exist or misconfigured; direct abuse possible
   - Temptation pressure: "Nobody's hitting our endpoint yet"

3. **Add logging later** ("Let's get it working first")
   - Reality: Later never comes; impossible to debug without logs
   - Temptation pressure: "Adds 10 more LOC, defer it"

4. **Store DB query directly in endpoint** ("Quick and dirty")
   - Reality: Couples endpoint to schema, no reusability, hard to test
   - Temptation pressure: "Function extraction is premature optimization"

5. **Skip error handling** ("FastAPI has defaults")
   - Reality: Defaults are generic; will leak internals or confuse clients
   - Temptation pressure: "Exception handlers are boilerplate"

## Decision: Full Implementation Required

**None of the 5 can be optional.** Time pressure is the enemy here. CLAUDE.md says: "Never implement without an approved plan. If something breaks → switch back to Plan mode and re-plan."

This discipline is exactly what separates shipping 3 times instead of once because debugging failures takes 6x longer.
