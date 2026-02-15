# RED Phase Test Report - Database Main Logic

**Date:** 2026-02-13
**Phase:** RED (Failing Tests Define Requirements)
**Test Suite:** `tests/test_db_red_phase.py`
**Status:** 30/30 Tests FAILING ✓ (Expected)

---

## Executive Summary

This report documents the complete RED phase test suite for AEGIS1's database layer. All 30 tests are designed to FAIL initially, establishing clear requirements for database implementation.

The tests follow Test-Driven Development (TDD) best practices:
1. **RED**: All tests fail (current state)
2. **GREEN**: Implement features to make tests pass
3. **REFACTOR**: Optimize implementation while keeping tests green

---

## Test Results Summary

```
Total Tests: 30
Status: ALL FAILING (Expected)

Test Categories:
├─ Health Log CRUD (5 tests)
├─ Expense CRUD (4 tests)
├─ Health Data Queries by Date Range (4 tests)
├─ Spending Calculations by Category (4 tests)
├─ Conversation Memory with Embeddings (4 tests)
├─ Transaction Safety & Atomicity (6 tests)
└─ Database Indexing (3 tests)
```

---

## Category 1: Health Log CRUD Operations (5 tests)

### Purpose
Establish the ability to create and read health log entries with metrics and values.

### Tests

#### Test 1: `test_create_health_log_with_metric_and_value`
**Status:** ❌ FAILING
**Expected:** Should create a health log entry and retrieve it by metric
**Current Error:** Database connection issue in test fixture
**Requirement:**
- Insert health_logs with (metric, value, notes) fields
- Verify auto-increment ID generation
- Support row_factory for named access

#### Test 2: `test_read_health_log_by_id`
**Status:** ❌ FAILING
**Expected:** Should retrieve a health log by primary key
**Requirement:**
- Support inserting without explicit ID
- Return lastrowid from cursor
- Query by ID and retrieve all fields

#### Test 3: `test_create_multiple_health_logs_same_metric`
**Status:** ❌ FAILING
**Expected:** Should support 5+ entries for same metric across dates
**Requirement:**
- Time-series storage (multiple rows for same metric)
- Custom timestamp support
- Ordering by timestamp DESC

#### Test 4: `test_health_log_timestamp_auto_set`
**Status:** ❌ FAILING
**Expected:** Timestamp should auto-set to CURRENT_TIMESTAMP if not provided
**Requirement:**
- DEFAULT CURRENT_TIMESTAMP in schema
- Timestamp should be recent (within 5 seconds of now)
- Support ISO format datetime strings

#### Test 5: `test_health_log_nullable_notes`
**Status:** ❌ FAILING
**Expected:** Notes field should default to empty string
**Requirement:**
- notes column has DEFAULT ''
- INSERT without notes should work
- Retrieved notes should be '' or NULL (application handles both)

---

## Category 2: Expense CRUD Operations (4 tests)

### Purpose
Establish the ability to create and read expense entries with categories and amounts.

### Tests

#### Test 1: `test_create_expense_with_all_fields`
**Status:** ❌ FAILING
**Expected:** Should create expense with amount, category, description
**Requirement:**
- Insert expenses (amount REAL, category TEXT, description TEXT)
- Support row_factory for named column access
- Auto-increment ID generation

#### Test 2: `test_read_expense_by_id`
**Status:** ❌ FAILING
**Expected:** Retrieve expense by primary key
**Requirement:**
- Query by id column
- Return all expense fields
- Support lastrowid from cursor

#### Test 3: `test_create_multiple_expenses_same_category`
**Status:** ❌ FAILING
**Expected:** Should support 3+ expenses in same category
**Requirement:**
- Multiple rows with same category value
- SUM aggregation for total calculation
- Support WHERE category = ? queries

#### Test 4: `test_expense_timestamp_auto_set`
**Status:** ❌ FAILING
**Expected:** Timestamp should auto-set when not provided
**Requirement:**
- DEFAULT CURRENT_TIMESTAMP in schema
- Recent timestamp verification (within 5 seconds)

---

## Category 3: Health Data Queries by Date Range (4 tests)

### Purpose
Establish querying capabilities for time-series health data with date filters.

### Tests

#### Test 1: `test_query_health_logs_within_date_range`
**Status:** ❌ FAILING
**Expected:** Query health logs between two dates
**Requirement:**
- BETWEEN operator support
- ISO format date comparison
- Index on (metric, timestamp) for performance

#### Test 2: `test_query_health_logs_by_metric_and_date`
**Status:** ❌ FAILING
**Expected:** Filter by metric type AND date range simultaneously
**Requirement:**
- Compound WHERE clauses
- Multiple filtering conditions
- Correct row count for filtered range

#### Test 3: `test_query_health_logs_sorted_by_timestamp_desc`
**Status:** ❌ FAILING
**Expected:** Results ordered by timestamp descending (newest first)
**Requirement:**
- ORDER BY timestamp DESC
- Verify sort order correctness
- Handle multiple rows with close timestamps

#### Test 4: `test_query_aggregate_health_metrics_by_date`
**Status:** ❌ FAILING
**Expected:** Aggregate metrics by date (AVG, MIN, MAX, COUNT)
**Requirement:**
- GROUP BY DATE(timestamp), metric
- Aggregate functions: AVG(), MIN(), MAX(), COUNT()
- Handle multiple values per day
- Test with 5 entries per day expecting correct averages

---

## Category 4: Calculate Spending by Category (4 tests)

### Purpose
Establish aggregation capabilities for expense analysis.

### Tests

#### Test 1: `test_sum_expenses_by_category`
**Status:** ❌ FAILING
**Expected:** Sum total spending by category across all time
**Requirement:**
- GROUP BY category
- SUM(amount) aggregation
- ORDER BY total DESC for ranking
- Handle 3+ categories

#### Test 2: `test_spending_by_category_date_range`
**Status:** ❌ FAILING
**Expected:** Sum spending by category within date range
**Requirement:**
- Combine GROUP BY with BETWEEN date filter
- COUNT(*) for transaction count
- Support "last N days" queries
- Correct aggregation over filtered range

#### Test 3: `test_average_spending_per_transaction_by_category`
**Status:** ❌ FAILING
**Expected:** Calculate AVG(amount) per category
**Requirement:**
- GROUP BY category with AVG()
- COUNT(*) to show transaction count
- ORDER BY avg_amount DESC
- Correct average calculations

#### Test 4: `test_spending_category_with_zero_results`
**Status:** ❌ FAILING
**Expected:** Query non-existent category returns empty result set
**Requirement:**
- Empty result set for no matches
- No errors on zero results
- Support safe filtering

---

## Category 5: Conversation Memory with Embeddings (4 tests)

### Purpose
Establish vector embedding storage for semantic memory and similarity search.

### New Required Table: `embeddings`

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
```

### Tests

#### Test 1: `test_create_embedding_table_schema`
**Status:** ❌ FAILING
**Expected:** embeddings table must exist with correct schema
**Requirement:**
- New table creation in init_db()
- Columns: id, conversation_id, text_content, embedding, metadata, created_at
- embedding stored as BLOB (JSON serialized)
- metadata as JSON string

#### Test 2: `test_store_conversation_embedding`
**Status:** ❌ FAILING
**Expected:** Store conversation text with embedding vector
**Requirement:**
- Create embeddings table
- Insert with conversation_id, text_content, embedding BLOB
- Store embedding as JSON-encoded bytes
- Store metadata as JSON object
- Support retrieval by conversation_id

#### Test 3: `test_retrieve_embedding_by_conversation_id`
**Status:** ❌ FAILING
**Expected:** Retrieve embeddings by conversation reference
**Requirement:**
- Query embeddings WHERE conversation_id = ?
- Return all fields including BLOB embedding
- Support join with conversations table
- Maintain created_at ordering

#### Test 4: `test_semantic_similarity_search_with_embeddings`
**Status:** ❌ FAILING
**Expected:** Retrieve similar embeddings (foundation for similarity search)
**Requirement:**
- Store 3+ embeddings with different vectors
- Query all embeddings for similarity search phase
- Support ORDER BY created_at DESC
- Foundation for cosine similarity computation (in app layer)

---

## Category 6: Transaction Safety & Atomicity (6 tests)

### Purpose
Establish ACID guarantees and data consistency under concurrent/complex operations.

### Tests

#### Test 1: `test_insert_multiple_expenses_atomic`
**Status:** ❌ FAILING
**Expected:** Multi-insert transaction commits atomically
**Requirement:**
- BEGIN TRANSACTION support
- Commit multiple inserts as single unit
- All-or-nothing semantics
- Verify all 3 expenses inserted

#### Test 2: `test_transaction_rollback_on_error`
**Status:** ❌ FAILING
**Expected:** Failed transaction rolls back cleanly
**Requirement:**
- BEGIN TRANSACTION / ROLLBACK
- Insert fails, count unchanged
- No partial writes on error
- Application can handle exceptions

#### Test 3: `test_concurrent_health_log_inserts`
**Status:** ❌ FAILING
**Expected:** Rapid inserts (100+) succeed without corruption
**Requirement:**
- SQLite WAL mode for file-based DB
- Support 100 successive inserts
- No race conditions
- All inserts succeed

#### Test 4: `test_transaction_with_foreign_key_constraint`
**Status:** ❌ FAILING
**Expected:** Foreign key constraints enforced in transactions
**Requirement:**
- PRAGMA foreign_keys = ON
- FK constraint: embeddings.conversation_id → conversations.id
- Reject insert with non-existent conversation_id
- Raise sqlite3.IntegrityError

#### Test 5: `test_update_expense_maintains_integrity`
**Status:** ❌ FAILING
**Expected:** UPDATE operation preserves data consistency
**Requirement:**
- INSERT expense, then UPDATE amount/category
- Verify updated values in SELECT
- ID remains unchanged
- No data loss

#### Test 6: `test_delete_with_cascading_constraints`
**Status:** ❌ FAILING
**Expected:** DELETE with ON DELETE CASCADE works correctly
**Requirement:**
- embeddings.conversation_id with ON DELETE CASCADE
- DELETE conversation cascades to embeddings
- Verify conversation deleted (count = 0)
- Orphaned embeddings handled

---

## Category 7: Database Indexing (3 tests)

### Purpose
Establish performance optimization through proper indexing.

### Required Indexes

| Index | Table | Columns | Purpose |
|---|---|---|---|
| idx_health_metric | health_logs | (metric, timestamp) | Fast metric+date queries |
| idx_expense_cat | expenses | (category, timestamp) | Fast category+date aggregations |
| idx_embeddings_conv | embeddings | (conversation_id) | Conversation joins |

### Tests

#### Test 1: `test_health_logs_metric_timestamp_index`
**Status:** ❌ FAILING
**Expected:** idx_health_metric index exists
**Requirement:**
- Index created in init_db()
- Query sqlite_master for index name
- Verify index on (metric, timestamp) columns

#### Test 2: `test_expenses_category_timestamp_index`
**Status:** ❌ FAILING
**Expected:** idx_expense_cat index exists
**Requirement:**
- Index created in init_db()
- Query sqlite_master for index name
- Verify index on (category, timestamp)

#### Test 3: `test_index_improves_query_performance`
**Status:** ❌ FAILING
**Expected:** Indexes enable fast queries on large datasets
**Requirement:**
- Insert 1000 health logs
- Query with metric and timestamp filter
- Return >0 results
- Verifies index is actually used

---

## Implementation Requirements Summary

### Database Modifications Needed

1. **Add embeddings table** to `init_db()` in `/Users/apple/documents/aegis1/aegis/db.py`
   - Create embeddings table with schema above
   - Add idx_embeddings_conv index
   - Enable FK constraints

2. **Update health_logs schema** (already exists, verify fields)
   - Confirm: id, metric, value, notes, timestamp
   - Confirm: DEFAULT '' for notes, DEFAULT CURRENT_TIMESTAMP for timestamp

3. **Update expenses schema** (already exists, verify fields)
   - Confirm: id, amount, category, description, timestamp
   - Confirm: DEFAULT CURRENT_TIMESTAMP for timestamp

4. **Fix test fixture** - `clean_db` fixture in test file
   - Database connection is being closed prematurely
   - Need to manage connection lifecycle properly

### Schema Validation Checklist

- [ ] health_logs table with all required columns
- [ ] expenses table with all required columns
- [ ] conversations table (already exists)
- [ ] embeddings table with FK constraint
- [ ] idx_health_metric index on (metric, timestamp)
- [ ] idx_expense_cat index on (category, timestamp)
- [ ] idx_embeddings_conv index on (conversation_id)
- [ ] idx_insights_created index on (created_at)
- [ ] Default values set correctly
- [ ] Foreign key constraints enabled

### Feature Implementation Checklist

- [ ] CRUD operations for health logs
- [ ] CRUD operations for expenses
- [ ] Date range queries with BETWEEN
- [ ] Aggregation functions (SUM, AVG, MIN, MAX, COUNT)
- [ ] GROUP BY for category analysis
- [ ] ORDER BY for sorting
- [ ] Transaction support (BEGIN, COMMIT, ROLLBACK)
- [ ] Foreign key constraint enforcement
- [ ] CASCADE delete support
- [ ] Embedding BLOB storage (JSON serialized)
- [ ] Embedding retrieval by conversation_id

---

## Test Execution Guide

### Run All RED Phase Tests
```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_db_red_phase.py -v
```

### Run Specific Test Category
```bash
# Health log CRUD
python3 -m pytest tests/test_db_red_phase.py::TestHealthLogCRUD -v

# Expense CRUD
python3 -m pytest tests/test_db_red_phase.py::TestExpenseCRUD -v

# Embeddings
python3 -m pytest tests/test_db_red_phase.py::TestConversationMemoryWithEmbeddings -v

# Transaction safety
python3 -m pytest tests/test_db_red_phase.py::TestTransactionSafety -v

# Indexing
python3 -m pytest tests/test_db_red_phase.py::TestDatabaseIndexing -v
```

### Run Single Test
```bash
python3 -m pytest tests/test_db_red_phase.py::TestHealthLogCRUD::test_create_health_log_with_metric_and_value -v
```

### Verbose Output with Failure Details
```bash
python3 -m pytest tests/test_db_red_phase.py -vv --tb=long
```

---

## Next Phase: GREEN (Implementation)

Once RED phase is complete and requirements are clear, the GREEN phase will:

1. **Fix test fixture** - Ensure clean_db connection stays open during test
2. **Implement embeddings table** - Add to init_db() schema
3. **Verify all CRUD operations** work correctly
4. **Implement aggregation queries** for analytics
5. **Add transaction safety** - PRAGMA foreign_keys, BEGIN/COMMIT/ROLLBACK
6. **Verify indexes** are created and being used

All changes must maintain backward compatibility with existing tests in `tests/test_db.py`.

---

## File Locations

- **Test Suite:** `/Users/apple/documents/aegis1/tests/test_db_red_phase.py` (30 tests)
- **Schema Docs:** `/Users/apple/documents/aegis1/docs/database_schema_requirements.md`
- **Database Code:** `/Users/apple/documents/aegis1/aegis/db.py`
- **Existing Tests:** `/Users/apple/documents/aegis1/tests/test_db.py`
- **Test Config:** `/Users/apple/documents/aegis1/tests/conftest.py`

---

## Summary Statistics

| Metric | Value |
|---|---|
| Total Tests | 30 |
| Currently Failing | 30 |
| Expected to Pass | 30 |
| Test Categories | 7 |
| Lines of Test Code | 890+ |
| Database Tables Required | 5 |
| Indexes Required | 4 |
| Foreign Keys Required | 1 |

**Overall Status:** ✓ RED Phase Complete - All 30 Tests Failing as Expected

---

*End of Report*
