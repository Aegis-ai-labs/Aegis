# GREEN Phase Implementation Guide

**Status:** Ready for GREEN Phase Implementation
**Test Suite:** 30 RED Phase tests awaiting implementation
**Objective:** Make all tests pass while maintaining existing functionality

---

## Overview

This guide provides step-by-step instructions to implement database functionality and transition all 30 RED phase tests to GREEN (passing).

The implementation follows TDD principles:
- Tests define requirements
- Code implements those requirements
- All changes verified by tests

---

## Phase 1: Test Fixture Correction

### Issue
Database connection is closing prematurely in test fixture.

### Fix
Modify `/Users/apple/documents/aegis1/tests/test_db_red_phase.py` fixture:

**Current (Broken):**
```python
@pytest.fixture
def clean_db(test_settings):
    """Fixture providing a fresh in-memory database for each test."""
    import aegis.db
    aegis.db._db_connection = None

    init_db()
    conn = get_db()
    yield conn

    # Cleanup
    aegis.db._db_connection = None
```

**Issue:** init_db() calls `conn.close()` at the end, closing the connection before test runs.

**Solution:** Refactor init_db() to not close the connection, or create a separate initialization function.

---

## Phase 2: Add Embeddings Table

### Implementation
Modify `/Users/apple/documents/aegis1/aegis/db.py` - update `init_db()` function:

**Add to the CREATE TABLE section:**
```python
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    text_content TEXT NOT NULL,
    embedding BLOB NOT NULL,
    metadata TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_conv ON embeddings(conversation_id);
```

### Verification
After implementation, run:
```bash
python3 -m pytest tests/test_db_red_phase.py::TestConversationMemoryWithEmbeddings::test_create_embedding_table_schema -v
```

Expected result: PASSING ✓

---

## Phase 3: Enable Transaction Safety

### Implementation
Add to database initialization and connection setup:

**In `get_db()` function:**
```python
def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(settings.db_path)
        _db_connection.row_factory = sqlite3.Row

        # Enable foreign key support for cascading operations
        _db_connection.execute("PRAGMA foreign_keys = ON")

        if settings.db_path != ":memory:":
            _db_connection.execute("PRAGMA journal_mode=WAL")
    return _db_connection
```

### Verification
```bash
python3 -m pytest tests/test_db_red_phase.py::TestTransactionSafety -v
```

Expected: 6 tests passing (some or all)

---

## Phase 4: Health Log Operations

### Verify Schema
Check that health_logs table in `init_db()` has:

```python
CREATE TABLE IF NOT EXISTS health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    notes TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Test Coverage
Run all health log tests:
```bash
python3 -m pytest tests/test_db_red_phase.py::TestHealthLogCRUD -v
python3 -m pytest tests/test_db_red_phase.py::TestHealthDataQueryByDateRange -v
```

### Key Operations to Verify
- INSERT health logs
- SELECT by ID
- SELECT by metric
- SELECT with date range
- GROUP BY with aggregations (AVG, MIN, MAX)
- ORDER BY timestamp

---

## Phase 5: Expense Operations

### Verify Schema
Check that expenses table has:

```python
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Test Coverage
```bash
python3 -m pytest tests/test_db_red_phase.py::TestExpenseCRUD -v
python3 -m pytest tests/test_db_red_phase.py::TestCalculateSpendingByCategory -v
```

### Key Operations to Verify
- INSERT expenses
- SELECT by ID and category
- SUM(amount) by category
- AVG(amount) by category
- COUNT(*) transactions
- Date range filtering

---

## Phase 6: Verify All Indexes

### Required Indexes
All must exist in init_db():

```python
CREATE INDEX IF NOT EXISTS idx_health_metric ON health_logs(metric, timestamp);
CREATE INDEX IF NOT EXISTS idx_expense_cat ON expenses(category, timestamp);
CREATE INDEX IF NOT EXISTS idx_embeddings_conv ON embeddings(conversation_id);
CREATE INDEX IF NOT EXISTS idx_insights_created ON user_insights(created_at);
```

### Verification
```bash
python3 -m pytest tests/test_db_red_phase.py::TestDatabaseIndexing -v
```

Expected: 3/3 tests passing

---

## Phase 7: Embedding Operations

### Implementation
Ensure embeddings table supports:

**BLOB Storage Pattern:**
```python
import json

# Create embedding
embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
embedding_json = json.dumps(embedding_vector)
embedding_bytes = embedding_json.encode('utf-8')

# Store
db.execute(
    "INSERT INTO embeddings (conversation_id, text_content, embedding) VALUES (?, ?, ?)",
    (conv_id, text, embedding_bytes)
)

# Retrieve and decode
result = db.execute("SELECT embedding FROM embeddings WHERE id = ?", (id,)).fetchone()
retrieved_vector = json.loads(result['embedding'].decode('utf-8'))
```

### Test Coverage
```bash
python3 -m pytest tests/test_db_red_phase.py::TestConversationMemoryWithEmbeddings -v
```

---

## Phase 8: Transaction Safety Verification

### Key Test Scenarios

**1. Atomic Multi-Insert:**
```python
db.execute("BEGIN TRANSACTION")
# Multiple inserts
db.commit()
# All succeed or all fail
```

**2. Rollback on Error:**
```python
try:
    db.execute("BEGIN TRANSACTION")
    # Operations that may fail
    db.commit()
except Exception:
    db.rollback()
    # Database unchanged
```

**3. Foreign Key Constraints:**
```python
db.execute("PRAGMA foreign_keys = ON")
# Try to insert with invalid FK
# Should raise sqlite3.IntegrityError
```

**4. Cascade Delete:**
```python
# Delete conversation should delete embeddings
db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
# Embeddings with conversation_id should also be deleted
```

### Test Coverage
```bash
python3 -m pytest tests/test_db_red_phase.py::TestTransactionSafety -v
```

Expected: 6/6 passing

---

## Complete Implementation Checklist

### Pre-Implementation
- [ ] Read all test descriptions in test_db_red_phase.py
- [ ] Review schema requirements in database_schema_requirements.md
- [ ] Understand current database code in aegis/db.py
- [ ] Run tests to see current failures: `pytest tests/test_db_red_phase.py -v`

### Phase 1: Fixtures
- [ ] Fix clean_db fixture database connection handling
- [ ] Ensure connection stays open during test execution
- [ ] Reset global _db_connection between tests

### Phase 2: Schema
- [ ] Add embeddings table to init_db()
- [ ] Verify all columns: id, conversation_id, text_content, embedding, metadata, created_at
- [ ] Add FOREIGN KEY constraint with ON DELETE CASCADE
- [ ] Create idx_embeddings_conv index

### Phase 3: Transaction Safety
- [ ] Enable PRAGMA foreign_keys = ON in get_db()
- [ ] Ensure PRAGMA journal_mode=WAL for file-based DBs
- [ ] Support BEGIN TRANSACTION / COMMIT / ROLLBACK
- [ ] Verify cascading delete works

### Phase 4: Health Logs
- [ ] Verify health_logs schema completeness
- [ ] Test CREATE operations (INSERT)
- [ ] Test READ operations (SELECT by ID)
- [ ] Test date range queries (BETWEEN)
- [ ] Test aggregations (AVG, MIN, MAX, COUNT)
- [ ] Test GROUP BY operations

### Phase 5: Expenses
- [ ] Verify expenses schema completeness
- [ ] Test CREATE operations
- [ ] Test READ operations
- [ ] Test category aggregations
- [ ] Test spending calculations
- [ ] Test date range filtering

### Phase 6: Embeddings
- [ ] Create embeddings table
- [ ] Test BLOB storage (JSON serialized)
- [ ] Test retrieval by conversation_id
- [ ] Test metadata storage
- [ ] Verify created_at timestamps

### Phase 7: Indexes
- [ ] Create idx_health_metric
- [ ] Create idx_expense_cat
- [ ] Create idx_embeddings_conv
- [ ] Create idx_insights_created
- [ ] Verify index performance on large datasets

### Final Verification
- [ ] Run all 30 RED tests: should all be PASSING
- [ ] Run existing tests: `pytest tests/test_db.py -v` (should still PASS)
- [ ] Run all database tests: `pytest tests/test_db*.py -v`
- [ ] Check test coverage: `pytest tests/test_db_red_phase.py --cov=aegis.db`

---

## Test Execution Guide

### During Implementation

**After each major change:**
```bash
# Run specific category
python3 -m pytest tests/test_db_red_phase.py::TestHealthLogCRUD -v

# Check passing vs failing
python3 -m pytest tests/test_db_red_phase.py -q

# Detailed output on first failure
python3 -m pytest tests/test_db_red_phase.py -x -vv
```

### Progress Tracking

```bash
# Count passing tests
python3 -m pytest tests/test_db_red_phase.py -q 2>&1 | grep "passed"

# Expected progression:
# Phase 1: 0/30 passing
# Phase 2: 1/30 passing (embeddings table exists)
# Phase 3: 7/30 passing (transaction safety)
# Phase 4: 12/30 passing (health logs)
# Phase 5: 16/30 passing (expenses)
# Phase 6: 20/30 passing (embeddings)
# Phase 7: 23/30 passing (indexes)
# Phase 8: 30/30 passing ✓ ALL GREEN
```

### Final Verification

```bash
# Run all database tests
python3 -m pytest tests/test_db.py tests/test_db_red_phase.py -v

# Should see:
# - test_db.py: all PASSED (existing tests)
# - test_db_red_phase.py: all PASSED (new tests)
# Total: 30+ tests all PASSING
```

---

## Common Issues and Solutions

### Issue: "Cannot operate on a closed database"
**Solution:** Check that init_db() doesn't call conn.close() before tests run. Use a separate session-level fixture.

### Issue: "table X already exists"
**Solution:** Use `CREATE TABLE IF NOT EXISTS` for idempotency.

### Issue: "UNIQUE constraint failed"
**Solution:** Ensure test fixture cleans up/resets properly between tests. Use in-memory :memory: DB.

### Issue: "no such table: embeddings"
**Solution:** Ensure embeddings table is created in init_db() before any tests run.

### Issue: "FOREIGN KEY constraint failed"
**Solution:** Ensure PRAGMA foreign_keys = ON is enabled before tests run.

### Issue: "Index already exists"
**Solution:** Use `CREATE INDEX IF NOT EXISTS` for all indexes.

---

## Success Criteria

### Phase GREEN is COMPLETE when:

1. **All 30 tests PASSING**
   ```bash
   pytest tests/test_db_red_phase.py -v
   # Expected: 30 PASSED
   ```

2. **No regression in existing tests**
   ```bash
   pytest tests/test_db.py -v
   # Expected: All PASSED (existing count)
   ```

3. **Code quality maintained**
   - No hardcoded strings (use parameterization)
   - Proper error handling
   - No console.log or debug prints
   - Clean, readable SQL

4. **Performance acceptable**
   - Index tests show performance improvement
   - 1000+ inserts complete quickly
   - 100 concurrent inserts without issues

---

## Next Phase: REFACTOR

Once all tests pass (GREEN phase):

1. **Clean up test code** - remove duplication
2. **Optimize database queries** - ensure indexes are used
3. **Improve error messages** - more user-friendly
4. **Add docstrings** - document complex operations
5. **Performance review** - profile slow queries

---

## Files to Modify

1. `/Users/apple/documents/aegis1/aegis/db.py` - Main implementation
   - Fix get_db() for transaction safety
   - Add embeddings table to init_db()
   - Enable foreign keys

2. `/Users/apple/documents/aegis1/tests/test_db_red_phase.py` - Already created
   - May need fixture adjustments

3. `/Users/apple/documents/aegis1/tests/conftest.py` - Test configuration
   - May need session-level database initialization

---

## References

- **Test Suite:** `/Users/apple/documents/aegis1/tests/test_db_red_phase.py`
- **Schema Requirements:** `/Users/apple/documents/aegis1/docs/database_schema_requirements.md`
- **Test Report:** `/Users/apple/documents/aegis1/docs/RED_PHASE_TEST_REPORT.md`
- **Database Code:** `/Users/apple/documents/aegis1/aegis/db.py`
- **Config:** `/Users/apple/documents/aegis1/aegis/config.py`

---

## Summary

This guide provides a structured approach to implement all database functionality required by the 30 RED phase tests. Follow the phases in order, verify each step with tests, and maintain all passing tests throughout.

**Estimated Time:** 2-4 hours for complete implementation
**Complexity:** Medium (straightforward SQL, careful fixture management)
**Risk:** Low (comprehensive tests catch all issues)

**Start:** Phase 1 - Test Fixture Correction
**End:** All 30 tests PASSING ✓

---

*GREEN Phase Implementation Ready*
