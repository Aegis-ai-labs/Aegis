# AEGIS1 Database Schema Requirements

## Overview
This document defines the database schema requirements for AEGIS1's core data operations. These schemas are validated by the RED phase test suite in `tests/test_db_red_phase.py`.

## Core Tables

### 1. `health_logs` - Health Metrics Storage
Stores time-series health measurements for trend analysis and insights.

**Schema:**
```sql
CREATE TABLE health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    notes TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_metric ON health_logs(metric, timestamp);
```

**Columns:**
- `id`: Unique identifier (auto-increment)
- `metric`: Type of measurement (e.g., "sleep_hours", "steps", "heart_rate", "mood", "weight", "water", "exercise_minutes")
- `value`: Numeric measurement value (REAL for precision)
- `notes`: Optional text notes about the measurement (defaults to empty string)
- `timestamp`: When measurement was recorded (auto-set to CURRENT_TIMESTAMP)

**Constraints:**
- `metric` and `value` are NOT NULL
- `notes` defaults to empty string if not provided
- `timestamp` defaults to current time if not provided
- Index on `(metric, timestamp)` for efficient queries by metric type and date range

**Usage:**
- Track daily health metrics (sleep, exercise, mood, vitals)
- Support time-series analysis by metric
- Enable date-range queries for dashboard and reports

---

### 2. `expenses` - Financial Tracking
Stores individual expense transactions for spending analysis and budget tracking.

**Schema:**
```sql
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expense_cat ON expenses(category, timestamp);
```

**Columns:**
- `id`: Unique identifier (auto-increment)
- `amount`: Transaction amount in primary currency (REAL for precision)
- `category`: Expense category (e.g., "Food", "Transport", "Entertainment", "Shopping", "Utilities")
- `description`: Optional brief description of expense
- `timestamp`: When expense occurred (auto-set to CURRENT_TIMESTAMP)

**Constraints:**
- `amount` and `category` are NOT NULL
- `amount` should typically be positive (validated in application layer)
- `description` defaults to empty string
- `timestamp` defaults to current time
- Index on `(category, timestamp)` for efficient category-based aggregations

**Usage:**
- Track all expense transactions
- Aggregate spending by category
- Calculate totals over time periods
- Identify spending patterns and trends

---

### 3. `conversations` - Conversation History
Stores conversation exchanges with Claude for context and memory management.

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model_used TEXT DEFAULT '',
    latency_ms REAL DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `id`: Unique identifier (auto-increment)
- `role`: Speaker role ("user" or "assistant")
- `content`: Full text of the message/response
- `model_used`: Model that generated response (e.g., "claude-3-5-sonnet", "claude-3-haiku")
- `latency_ms`: Response time in milliseconds
- `timestamp`: When message was sent/received

**Constraints:**
- `role` and `content` are NOT NULL
- `model_used` defaults to empty string
- `latency_ms` defaults to 0
- `timestamp` defaults to current time

**Usage:**
- Maintain conversation history for context window management
- Track which model generated responses
- Measure and monitor API latency
- Support context retrieval for follow-up queries

---

### 4. `embeddings` - Semantic Memory (NEW - Required by RED Phase)
Stores vector embeddings of conversations for semantic search and similarity-based retrieval.

**Schema:**
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    text_content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_embeddings_conv ON embeddings(conversation_id);
```

**Columns:**
- `id`: Unique identifier (auto-increment)
- `conversation_id`: Foreign key reference to `conversations.id`
- `text_content`: The text that was embedded (for reference)
- `embedding`: Vector embedding stored as BLOB (JSON serialized)
- `metadata`: JSON metadata about embedding (model, dimensions, etc.)
- `created_at`: When embedding was stored

**Constraints:**
- `text_content` and `embedding` are NOT NULL
- `metadata` defaults to empty string
- `created_at` defaults to CURRENT_TIMESTAMP
- Foreign key to `conversations(id)` with ON DELETE CASCADE
- Index on `conversation_id` for join operations

**Usage:**
- Store embeddings of all conversations for semantic search
- Support retrieval of contextually similar past conversations
- Enable memory recall based on semantic similarity
- Implement long-term context preservation

---

### 5. `user_insights` - Generated Insights
Stores AI-generated insights about user behavior patterns.

**Schema:**
```sql
CREATE TABLE user_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_insights_created ON user_insights(created_at);
```

**Columns:**
- `id`: Unique identifier
- `insight`: The insight text generated by AI
- `created_at`: When insight was generated

**Constraints:**
- `insight` is NOT NULL
- `created_at` defaults to CURRENT_TIMESTAMP

---

## Required Indexes

The following indexes MUST be created for query performance:

| Index Name | Table | Columns | Purpose |
|---|---|---|---|
| `idx_health_metric` | `health_logs` | `(metric, timestamp)` | Fast queries by metric type and date range |
| `idx_expense_cat` | `expenses` | `(category, timestamp)` | Fast aggregations by category and date |
| `idx_insights_created` | `user_insights` | `(created_at)` | Chronological retrieval of insights |
| `idx_embeddings_conv` | `embeddings` | `(conversation_id)` | Join with conversations table |

---

## Critical Operations

### Health Log Queries
```sql
-- Get sleep hours for last 7 days
SELECT * FROM health_logs
WHERE metric = 'sleep_hours'
AND timestamp > datetime('now', '-7 days')
ORDER BY timestamp DESC;

-- Aggregate daily sleep average
SELECT DATE(timestamp) as date, AVG(value) as avg_sleep
FROM health_logs
WHERE metric = 'sleep_hours'
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

### Expense Queries
```sql
-- Sum spending by category this month
SELECT category, SUM(amount) as total, COUNT(*) as count
FROM expenses
WHERE timestamp > datetime('now', '-1 month')
GROUP BY category
ORDER BY total DESC;

-- Daily spending trend
SELECT DATE(timestamp) as date, SUM(amount) as total
FROM expenses
GROUP BY DATE(timestamp)
ORDER BY date DESC;
```

### Embedding Queries
```sql
-- Retrieve embeddings for a conversation
SELECT * FROM embeddings
WHERE conversation_id = ?
ORDER BY created_at DESC;

-- Get all embeddings for search
SELECT * FROM embeddings
ORDER BY created_at DESC
LIMIT 100;
```

---

## Transaction Safety Requirements

1. **Atomic Multi-Inserts**: Multiple health/expense inserts must be atomic
2. **Foreign Key Constraints**: Embeddings must enforce FK to conversations
3. **Rollback Support**: Failed transactions must rollback cleanly
4. **Concurrent Access**: Should support safe concurrent reads/writes (SQLite WAL mode)

---

## Data Type Specifications

| Type | Used For | Precision Notes |
|---|---|---|
| INTEGER | IDs, counts | Standard 64-bit |
| TEXT | Strings, categories, content | UTF-8 |
| REAL | Amounts, measurements | Double precision (8 bytes) |
| BLOB | Embeddings | Variable, JSON serialized |
| DATETIME | Timestamps | ISO 8601 format |

---

## Schema Validation

All schemas are validated by:
- `tests/test_db_red_phase.py` - RED phase tests (currently failing)
- `tests/test_db.py` - Integration tests (current passing tests)

Run validation:
```bash
pytest tests/test_db_red_phase.py -v  # RED phase tests
pytest tests/test_db.py -v            # Existing tests
```

---

## Migration Path

When updating schema:
1. Create new table/index with new name
2. Migrate data (if needed)
3. Update application code to use new table
4. Drop old table after verification
5. Document in migration log

Example:
```sql
-- Add new column to health_logs
ALTER TABLE health_logs ADD COLUMN unit_of_measure TEXT DEFAULT '';

-- Create index on new column
CREATE INDEX idx_health_unit ON health_logs(metric, unit_of_measure);
```

---

## Performance Targets

- Single metric time-series query: < 10ms for 1 year of data
- Category spending aggregation: < 50ms for 10k expenses
- Embedding similarity search: < 100ms for 10k embeddings
- Concurrent inserts: Support 100+ per second

All performance targets assume proper indexing and WAL mode for file-based databases.
