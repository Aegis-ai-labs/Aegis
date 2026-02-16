# Database Schema & Implementation Guide

**Project:** AEGIS1 - Health & Wealth Tracking
**Database:** SQLite3
**Phase:** GREEN (Implementation)

---

## Current Database Schema

The test suite expects the following database structure to exist in SQLite.

### Table 1: health_logs

**Purpose:** Store individual health metric data points

```sql
CREATE TABLE IF NOT EXISTS health_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    notes TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_health_metric ON health_logs(metric, timestamp);
CREATE INDEX IF NOT EXISTS idx_health_timestamp ON health_logs(timestamp);
```

**Column Details:**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `metric` | TEXT | NOT NULL | Type of metric (see valid values below) |
| `value` | REAL | NOT NULL | Numeric value of the metric |
| `notes` | TEXT | DEFAULT '' | Optional user notes |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When recorded |

**Valid Metric Values:**
```python
VALID_METRICS = {
    "sleep_hours": {"type": float, "min": 3.0, "max": 12.0, "unit": "hours"},
    "steps": {"type": int, "min": 0, "max": 20000, "unit": "count"},
    "heart_rate": {"type": int, "min": 40, "max": 120, "unit": "bpm"},
    "mood": {"type": str, "enum": ["great", "good", "okay", "tired", "stressed"]},
    "weight": {"type": float, "min": 80.0, "max": 400.0, "unit": "lbs"},
    "water": {"type": int, "min": 0, "max": 20, "unit": "glasses"},
    "exercise_minutes": {"type": int, "min": 0, "max": 300, "unit": "minutes"}
}
```

**Example Data:**
```sql
INSERT INTO health_logs (metric, value, notes, timestamp)
VALUES ('sleep_hours', 7.5, 'good sleep', '2024-02-13 08:00:00');

INSERT INTO health_logs (metric, value, notes, timestamp)
VALUES ('mood', 'great', '', '2024-02-13 09:00:00');

INSERT INTO health_logs (metric, value, notes, timestamp)
VALUES ('steps', 8432, '', '2024-02-13 23:59:00');

INSERT INTO health_logs (metric, value, notes, timestamp)
VALUES ('heart_rate', 72, 'resting', '2024-02-13 08:15:00');
```

**Query Examples:**

Get today's sleep data:
```sql
SELECT value, notes, timestamp
FROM health_logs
WHERE metric = 'sleep_hours'
  AND DATE(timestamp) = DATE('now')
ORDER BY timestamp DESC;
```

Get 7-day average for sleep:
```sql
SELECT AVG(value) as avg_sleep
FROM health_logs
WHERE metric = 'sleep_hours'
  AND DATE(timestamp) >= DATE('now', '-7 days');
```

Get mood distribution for the week:
```sql
SELECT value as mood, COUNT(*) as count
FROM health_logs
WHERE metric = 'mood'
  AND DATE(timestamp) >= DATE('now', '-7 days')
GROUP BY value
ORDER BY count DESC;
```

---

### Table 2: expenses

**Purpose:** Track financial transactions

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expense_cat ON expenses(category, timestamp);
CREATE INDEX IF NOT EXISTS idx_expense_timestamp ON expenses(timestamp);
```

**Column Details:**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| `amount` | REAL | NOT NULL | Dollar amount (e.g., 19.99) |
| `category` | TEXT | NOT NULL | Expense category (see valid values) |
| `description` | TEXT | DEFAULT '' | Optional details |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When recorded |

**Valid Categories:**
```python
VALID_CATEGORIES = [
    "food",           # Groceries, restaurants, delivery
    "transport",      # Gas, transit, rideshare, parking
    "shopping",       # Clothing, household items, gifts
    "health",         # Medical, pharmacy, fitness
    "entertainment",  # Movies, concerts, games, streaming
    "utilities"       # Electric, water, internet, phone
]
```

**Example Data:**
```sql
INSERT INTO expenses (amount, category, description, timestamp)
VALUES (45.50, 'food', 'dinner out', '2024-02-13 19:30:00');

INSERT INTO expenses (amount, category, description, timestamp)
VALUES (3.50, 'transport', 'bus fare', '2024-02-13 08:15:00');

INSERT INTO expenses (amount, category, description, timestamp)
VALUES (89.99, 'shopping', 'new shoes', '2024-02-13 14:00:00');

INSERT INTO expenses (amount, category, description, timestamp)
VALUES (12.50, 'food', 'lunch', '2024-02-13 12:00:00');
```

**Query Examples:**

Get today's total spending:
```sql
SELECT SUM(amount) as total_today, COUNT(*) as transaction_count
FROM expenses
WHERE DATE(timestamp) = DATE('now');
```

Get spending by category for the month:
```sql
SELECT category, SUM(amount) as total
FROM expenses
WHERE DATE(timestamp) >= DATE('now', 'start of month')
GROUP BY category
ORDER BY total DESC;
```

Get top 5 most expensive transactions:
```sql
SELECT amount, category, description, timestamp
FROM expenses
ORDER BY amount DESC
LIMIT 5;
```

---

## Database Implementation Tasks

### Task 1: Fix Async/Sync Mismatch

**Current Problem:**
```python
# In aegis/db.py - SYNCHRONOUS
def get_db() -> sqlite3.Connection:
    return _db_connection

# In aegis/tools/health.py - ASYNC
async def log_health(...):
    db = await get_db()  # ❌ Can't await sync function
```

**Solution Option A: Remove Await (Simple)**
```python
# In aegis/tools/health.py
async def log_health(...):
    db = get_db()  # Remove 'await'
    # ... rest of code
```

**Solution Option B: Make get_db() Async (Recommended)**
```python
# In aegis/db.py
async def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(settings.db_path)
        _db_connection.row_factory = sqlite3.Row
        if settings.db_path != ":memory:":
            _db_connection.execute("PRAGMA journal_mode=WAL")
    return _db_connection  # No change needed here
```

Then update all tool calls:
```python
# In aegis/tools/health.py, aegis/tools/wealth.py
async def log_health(...):
    db = await get_db()  # Now this works
```

---

### Task 2: Implement Missing get_health_by_date()

**Expected in tools but missing in db:**
```python
async def log_health(...):
    db = await get_db()
    # ... calls:
    await db.log_health(...)  # ❌ This method doesn't exist
```

**Implementation:**
```python
# Add to aegis/db.py or create wrapper module

def log_health_metric(
    date: str,
    sleep_hours: float = None,
    steps: int = None,
    heart_rate_avg: int = None,
    mood: str = None,
    notes: str = None
) -> int:
    """Insert health metrics. Returns inserted row ID."""
    conn = get_db()

    # Insert each non-None metric
    row_id = None
    if sleep_hours is not None:
        cursor = conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("sleep_hours", sleep_hours, notes or "", date)
        )
        row_id = cursor.lastrowid
        conn.commit()

    if steps is not None:
        cursor = conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("steps", steps, notes or "", date)
        )
        row_id = cursor.lastrowid
        conn.commit()

    if heart_rate_avg is not None:
        cursor = conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("heart_rate", heart_rate_avg, notes or "", date)
        )
        row_id = cursor.lastrowid
        conn.commit()

    if mood is not None:
        cursor = conn.execute(
            "INSERT INTO health_logs (metric, value, notes, timestamp) VALUES (?, ?, ?, ?)",
            ("mood", mood, notes or "", date)
        )
        row_id = cursor.lastrowid
        conn.commit()

    return row_id

def get_health_by_date(date: str) -> dict:
    """Get all health data for a specific date."""
    conn = get_db()
    cursor = conn.execute(
        "SELECT metric, value, notes, timestamp FROM health_logs WHERE DATE(timestamp) = ?",
        (date,)
    )
    rows = cursor.fetchall()

    result = {}
    for row in rows:
        metric = row[0]
        value = row[1]
        if metric not in result:
            result[metric] = []
        result[metric].append({
            "value": value,
            "notes": row[2],
            "timestamp": row[3]
        })

    return result

def get_recent_health(days: int = 7) -> list:
    """Get all health data from last N days."""
    conn = get_db()
    cursor = conn.execute(
        """SELECT metric, value, notes, timestamp
           FROM health_logs
           WHERE DATE(timestamp) >= DATE('now', ? || ' days')
           ORDER BY timestamp DESC""",
        (f"-{days}",)
    )
    return [dict(row) for row in cursor.fetchall()]
```

---

### Task 3: Implement Missing Expense Methods

**Expected in tools but missing:**
```python
async def track_expense(...):
    db = await get_db()
    # ... calls:
    await db.track_expense(...)  # ❌ This method doesn't exist
```

**Implementation:**
```python
# Add to aegis/db.py

def track_expense_record(
    date: str,
    amount: float,
    category: str,
    description: str = None
) -> int:
    """Insert expense record. Returns inserted row ID."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO expenses (amount, category, description, timestamp) VALUES (?, ?, ?, ?)",
        (amount, category, description or "", date)
    )
    conn.commit()
    return cursor.lastrowid

def get_expenses_by_date(date: str) -> list:
    """Get all expenses for a specific date."""
    conn = get_db()
    cursor = conn.execute(
        """SELECT id, amount, category, description, timestamp
           FROM expenses
           WHERE DATE(timestamp) = ?
           ORDER BY timestamp DESC""",
        (date,)
    )
    return [dict(row) for row in cursor.fetchall()]

def get_spending_by_category(start_date: str, end_date: str) -> dict:
    """Get spending totals by category in date range."""
    conn = get_db()
    cursor = conn.execute(
        """SELECT category, SUM(amount) as total
           FROM expenses
           WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
           GROUP BY category
           ORDER BY total DESC""",
        (start_date, end_date)
    )
    return {row[0]: row[1] for row in cursor.fetchall()}
```

---

### Task 4: Implement calculate_savings_goal()

**Missing function in wealth module:**

```python
# Add to aegis/tools/wealth.py

async def calculate_savings_goal(
    target_amount: float,
    target_months: int,
    monthly_income: float,
) -> dict[str, Any]:
    """
    Calculate monthly savings needed to reach a financial goal.

    Args:
        target_amount: Total amount to save (e.g., 1200.00)
        target_months: Number of months to save (e.g., 6)
        monthly_income: Monthly income (e.g., 4000.00)

    Returns:
        {
            "status": "ok",
            "monthly_savings_needed": 200.00,
            "target_amount": 1200.00,
            "target_months": 6,
            "feasible": True,
            "percentage_of_income": 5.0,
            "remaining_after_savings": 3800.00
        }

    Raises:
        ValueError: If target_months <= 0 or monthly_income < 0
    """
    # Validation
    if target_months <= 0:
        raise ValueError("target_months must be positive")
    if monthly_income < 0:
        raise ValueError("monthly_income cannot be negative")
    if target_amount <= 0:
        raise ValueError("target_amount must be positive")

    # Calculate
    monthly_savings_needed = target_amount / target_months
    feasible = monthly_savings_needed <= monthly_income
    percentage_of_income = (
        (monthly_savings_needed / monthly_income) * 100
        if monthly_income > 0
        else 0
    )
    remaining_after_savings = monthly_income - monthly_savings_needed

    return {
        "status": "ok",
        "monthly_savings_needed": round(monthly_savings_needed, 2),
        "target_amount": round(target_amount, 2),
        "target_months": target_months,
        "feasible": feasible,
        "percentage_of_income": round(percentage_of_income, 1),
        "remaining_after_savings": round(remaining_after_savings, 2),
    }
```

**Add to tool registry (aegis/tools/registry.py):**
```python
{
    "name": "calculate_savings_goal",
    "description": "Calculate monthly savings needed to reach a financial goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "target_amount": {
                "type": "number",
                "description": "Total amount to save (e.g., 1200)"
            },
            "target_months": {
                "type": "integer",
                "description": "Number of months to save (e.g., 6)"
            },
            "monthly_income": {
                "type": "number",
                "description": "Monthly income (e.g., 4000)"
            },
        },
        "required": ["target_amount", "target_months", "monthly_income"],
    },
}
```

And add to handlers:
```python
_HANDLERS: dict[str, Any] = {
    # ... existing handlers ...
    "calculate_savings_goal": wealth.calculate_savings_goal,
}
```

---

### Task 5: Add Input Validation

**Current issue:** No validation of inputs

**Solution: Add validators**

```python
# Add to aegis/tools/wealth.py

def validate_expense(amount: float, category: str) -> None:
    """Validate expense inputs. Raises ValueError if invalid."""
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    if amount > 1_000_000:
        raise ValueError(f"Amount seems too large: {amount}")

    valid_categories = {"food", "transport", "shopping", "health", "entertainment", "utilities"}
    if category not in valid_categories:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {valid_categories}")

# Add to aegis/tools/health.py

def validate_health_metric(metric: str, value: float) -> None:
    """Validate health metric. Raises ValueError if invalid."""
    validators = {
        "sleep_hours": lambda v: 3 <= v <= 12,
        "steps": lambda v: 0 <= v <= 20000,
        "heart_rate": lambda v: 40 <= v <= 120,
        "mood": lambda v: v in ["great", "good", "okay", "tired", "stressed"],
        "weight": lambda v: 80 <= v <= 400,
        "water": lambda v: 0 <= v <= 20,
        "exercise_minutes": lambda v: 0 <= v <= 300,
    }

    if metric not in validators:
        raise ValueError(f"Unknown metric: {metric}")

    if not validators[metric](value):
        raise ValueError(f"Invalid value for {metric}: {value}")
```

---

## Testing Database Operations

### Test Insert + Query Roundtrip

```python
# In test file
def test_health_log_roundtrip():
    """Test that logged data can be retrieved."""
    # Insert
    row_id = log_health_metric(
        date="2024-02-13",
        sleep_hours=7.5,
        notes="good"
    )
    assert row_id > 0

    # Query
    data = get_health_by_date("2024-02-13")
    assert "sleep_hours" in data
    assert data["sleep_hours"][0]["value"] == 7.5
    assert data["sleep_hours"][0]["notes"] == "good"
```

### Test Aggregation Queries

```python
def test_spending_aggregation():
    """Test category aggregation."""
    # Setup
    track_expense_record("2024-02-13", 45.00, "food")
    track_expense_record("2024-02-13", 12.00, "food")
    track_expense_record("2024-02-13", 50.00, "transport")

    # Query
    by_cat = get_spending_by_category("2024-02-13", "2024-02-13")

    # Verify
    assert by_cat["food"] == 57.00
    assert by_cat["transport"] == 50.00
```

---

## Performance Considerations

### Index Strategy

The schema includes these indexes for query performance:

```sql
-- Metric-based queries (common for health analysis)
CREATE INDEX idx_health_metric ON health_logs(metric, timestamp);

-- Time-based queries (common for date ranges)
CREATE INDEX idx_health_timestamp ON health_logs(timestamp);
CREATE INDEX idx_expense_timestamp ON expenses(timestamp);

-- Category aggregation (common for spending reports)
CREATE INDEX idx_expense_cat ON expenses(category, timestamp);
```

### Query Optimization Tips

1. **Use DATE() function sparingly:**
   ```sql
   -- Good: uses index
   WHERE timestamp >= '2024-02-10' AND timestamp < '2024-02-17'

   -- Bad: prevents index use
   WHERE DATE(timestamp) >= DATE('now', '-7 days')
   ```

2. **Group by category for summaries:**
   ```sql
   -- Efficient: grouped aggregation
   SELECT category, SUM(amount)
   FROM expenses
   WHERE timestamp >= ? AND timestamp <= ?
   GROUP BY category
   ```

3. **Limit results for top N queries:**
   ```sql
   SELECT * FROM expenses ORDER BY amount DESC LIMIT 10
   ```

---

## Summary Checklist

- [ ] Verify health_logs table exists with correct schema
- [ ] Verify expenses table exists with correct schema
- [ ] Create all required indexes
- [ ] Test INSERT operations
- [ ] Test SELECT queries with date ranges
- [ ] Test GROUP BY aggregations
- [ ] Implement database wrapper functions
- [ ] Fix async/sync mismatch in tools
- [ ] Add input validation
- [ ] Implement calculate_savings_goal()
- [ ] Run all 50 RED phase tests → All PASS

---

Generated by Claude Code - Database Schema Guide
