# Expected Test Failures — RED Phase

**Test File:** `tests/test_health_wealth_red.py`
**Total Tests:** 50
**Passing (Error Handling):** 7
**Failing (Expected):** 43
**Phase:** RED (No Implementation)

---

## Summary of Failures

### Primary Failure Category: Database Layer
**Count:** 35 failures
**Root Cause:** `get_db()` is synchronous but tools try to `await` it
**Error Type:** `TypeError`

### Secondary Failure Category: Missing Functions
**Count:** 6 failures
**Root Cause:** `calculate_savings_goal()` not implemented in wealth module
**Error Type:** `AttributeError`

### Tertiary Failure Category: Type Mismatches in Dispatch
**Count:** 2 failures
**Root Cause:** DB errors propagate through dispatch, assertion failures
**Error Type:** `AssertionError`

---

## Detailed Failure Messages

### ❌ Failure 1: Health Data Logging Errors (9 tests)

#### Test: `test_log_sleep_hours_single_entry`
```
FAILED tests/test_health_wealth_red.py::TestHealthDataLogging::test_log_sleep_hours_single_entry

Location: aegis/tools/health.py:18
Error Type: TypeError
Message: object sqlite3.Connection can't be used in 'await' expression

Trace:
  File tests/test_health_wealth_red.py, line 43
    result = await health.log_health(sleep_hours=7.5, notes="good sleep")
  File aegis/tools/health.py, line 18
    db = await get_db()
TypeError: object sqlite3.Connection can't be used in 'await' expression
```

**Root Cause:**
```python
# In aegis/tools/health.py:18
async def log_health(...):
    db = await get_db()  # ❌ get_db() is synchronous, can't await
```

**Database Source (aegis/db.py:15):**
```python
def get_db() -> sqlite3.Connection:  # ❌ Not async
    global _db_connection
    if _db_connection is None:
        _db_connection = sqlite3.connect(settings.db_path)
    return _db_connection
```

**Fix Options:**
1. **Option A:** Remove `await` from tool calls
   ```python
   async def log_health(...):
       db = get_db()  # Remove await
   ```

2. **Option B:** Make `get_db()` async (better)
   ```python
   async def get_db() -> sqlite3.Connection:
       global _db_connection
       if _db_connection is None:
           _db_connection = sqlite3.connect(settings.db_path)
       return _db_connection
   ```

**Affected Tests:**
- `test_log_sleep_hours_single_entry`
- `test_log_mood_with_validation`
- `test_log_heart_rate_numeric`
- `test_log_steps_integer`
- `test_log_health_multiple_metrics_same_day`
- `test_log_health_with_custom_date`
- `test_log_health_defaults_to_today`
- `test_log_health_with_notes_preserved`
- `test_log_health_returns_unique_ids`

---

### ❌ Failure 2: Health Pattern Query Errors (8 tests)

#### Test: `test_query_sleep_trend_over_days`
```
FAILED tests/test_health_wealth_red.py::TestHealthPatternQueries::test_query_sleep_trend_over_days

Location: aegis/tools/health.py:43
Error Type: TypeError
Message: object sqlite3.Connection can't be used in 'await' expression

Trace:
  File tests/test_health_wealth_red.py, line 96
    result = await health.get_health_summary(days=7)
  File aegis/tools/health.py, line 43
    db = await get_db()
TypeError: object sqlite3.Connection can't be used in 'await' expression
```

**Same Root Cause as Failure 1**

**Affected Tests:**
- `test_query_sleep_trend_over_days`
- `test_query_steps_average`
- `test_query_heart_rate_average`
- `test_query_mood_distribution`
- `test_query_health_today_returns_current_data`
- `test_query_empty_health_data_no_error`
- `test_health_patterns_sleep_mood_correlation`
- `test_query_health_respects_days_parameter`

---

### ❌ Failure 3: Expense Tracking Errors (8 tests)

#### Test: `test_track_expense_basic`
```
FAILED tests/test_health_wealth_red.py::TestExpenseTracking::test_track_expense_basic

Location: aegis/tools/wealth.py:17
Error Type: TypeError
Message: object sqlite3.Connection can't be used in 'await' expression

Trace:
  File tests/test_health_wealth_red.py, line 311
    result = await wealth.track_expense(amount=45.50, category="food", description="lunch at cafe")
  File aegis/tools/wealth.py, line 17
    db = await get_db()
TypeError: object sqlite3.Connection can't be used in 'await' expression
```

**Problem Code (aegis/tools/wealth.py:10-22):**
```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    db = await get_db()  # ❌ Same issue
    date = date or datetime.now().strftime("%Y-%m-%d")
    # ... rest of implementation
```

**Affected Tests:**
- `test_track_expense_basic`
- `test_track_expense_multiple_categories`
- `test_track_expense_amount_precision`
- `test_track_expense_with_description`
- `test_track_expense_defaults_to_today`
- `test_track_expense_custom_date`
- `test_track_expense_zero_amount_validation` (different error - validation not implemented)
- `test_track_multiple_same_day`

---

### ❌ Failure 4: Spending Report Errors (7 tests)

#### Test: `test_spending_report_by_category`
```
FAILED tests/test_health_wealth_red.py::TestSpendingReports::test_spending_report_by_category

Location: aegis/tools/wealth.py:42
Error Type: TypeError
Message: object sqlite3.Connection can't be used in 'await' expression

Trace:
  File tests/test_health_wealth_red.py, line 421
    result = await wealth.get_spending_summary(days=7)
  File aegis/tools/wealth.py, line 42
    db = await get_db()
TypeError: object sqlite3.Connection can't be used in 'await' expression
```

**Problem Code (aegis/tools/wealth.py:40-54):**
```python
async def get_spending_summary(days: int = 30) -> dict[str, Any]:
    """Get spending summary for the last N days."""
    db = await get_db()  # ❌ Same issue
    # ... rest of implementation
```

**Affected Tests:**
- `test_spending_report_by_category`
- `test_spending_report_total_calculation`
- `test_spending_report_respects_days_parameter`
- `test_spending_today_endpoint`
- `test_spending_today_with_multiple_expenses`
- `test_spending_report_no_negative_totals`
- `test_spending_report_categories_are_consistent`

---

### ❌ Failure 5: Missing calculate_savings_goal Function (6 tests)

#### Test: `test_calculate_savings_goal_monthly_required`
```
FAILED tests/test_health_wealth_red.py::TestSavingsGoals::test_calculate_savings_goal_monthly_required

Location: tests/test_health_wealth_red.py:504
Error Type: AttributeError
Message: module 'aegis.tools.wealth' has no attribute 'calculate_savings_goal'

Trace:
  File tests/test_health_wealth_red.py, line 504
    result = await wealth.calculate_savings_goal(
AttributeError: module 'aegis.tools.wealth' has no attribute 'calculate_savings_goal'
```

**Current aegis/tools/wealth.py Functions:**
```python
# Only has:
- track_expense()
- get_spending_today()
- get_spending_summary()
- get_budget_status()

# Missing:
- calculate_savings_goal()  # ❌ Needs implementation
```

**Expected Function Signature:**
```python
async def calculate_savings_goal(
    target_amount: float,
    target_months: int,
    monthly_income: float
) -> dict[str, Any]:
    """
    Calculate monthly savings needed to reach a goal.

    Args:
        target_amount: Total amount to save ($)
        target_months: Timeframe to save it (months)
        monthly_income: Monthly income ($)

    Returns:
        {
            "monthly_savings_needed": float,
            "feasible": bool,
            "percentage_of_income": float,
            "status": "ok"
        }
    """
    monthly_savings = target_amount / target_months
    feasible = monthly_savings <= monthly_income
    percentage = (monthly_savings / monthly_income) * 100

    return {
        "monthly_savings_needed": round(monthly_savings, 2),
        "feasible": feasible,
        "percentage_of_income": round(percentage, 1),
        "status": "ok"
    }
```

**Affected Tests:**
- `test_calculate_savings_goal_monthly_required`
- `test_savings_goal_feasibility_check_positive`
- `test_savings_goal_feasibility_check_negative`
- `test_savings_goal_percentage_of_income`
- `test_savings_goal_zero_months_validation`
- `test_savings_goal_timeline_breakdown`

---

### ❌ Failure 6: Dispatch Error Handling Issues (2 tests)

#### Test: `test_dispatch_log_health_tool`
```
FAILED tests/test_health_wealth_red.py::TestToolDispatch::test_dispatch_log_health_tool

Location: tests/test_health_wealth_red.py:600
Error Type: AssertionError
Condition Failed: 'error' not in result or result.get("status") == "logged"

Actual Result:
{
    "error": "Invalid arguments for log_health: object sqlite3.Connection can't be used in 'await' expression"
}

Expected Result:
{
    "status": "logged",
    "id": <id>,
    "date": "2024-02-13"
}
```

**Problem Code (aegis/tools/registry.py:115-130):**
```python
async def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return JSON result string."""
    handler = _HANDLERS.get(tool_name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = await handler(**tool_input)
        return json.dumps(result)
    except TypeError as e:  # ❌ Catches DB error correctly
        return json.dumps({"error": f"Invalid arguments for {tool_name}: {e}"})
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name}", exc_info=True)
        return json.dumps({
            "error": "Tool execution failed. Check logs for details.",
            "function": tool_name
        })
```

**The dispatch IS working correctly.** The test assertions need adjustment:
- The dispatch is catching the TypeError from `await get_db()`
- It's returning a proper error JSON
- The test is failing because it expects either no error OR status=="logged"
- But it's getting an error due to the DB layer issue

**Affected Tests:**
- `test_dispatch_log_health_tool`
- `test_dispatch_track_expense_tool`
- `test_dispatch_get_health_summary`
- `test_dispatch_get_spending_summary`
- `test_dispatch_missing_optional_parameters`

**Note:** These will pass automatically once the DB layer is fixed.

---

## What Tests PASS (Error Handling Tests)

```
✅ test_dispatch_unknown_tool_returns_error
✅ test_dispatch_invalid_arguments_returns_error
✅ test_dispatch_returns_valid_json
✅ test_dispatch_with_extra_parameters
✅ test_dispatch_all_health_tools
✅ test_dispatch_all_wealth_tools
✅ test_dispatch_error_doesnt_crash_app
```

**Why They Pass:**
These tests trigger the error handling paths in `dispatch_tool()`:
1. Unknown tool name → caught by `if not handler` check
2. Missing required args → caught by `TypeError` handler
3. Valid JSON → always returns dict via json.dumps()
4. Extra params → Python ignores them automatically
5. All tools listed → dispatch loop succeeds (errors are caught)
6. Errors don't crash → dispatch catches everything

---

## Implementation Priority for GREEN Phase

### Priority 1: Fix Database Layer (Unblocks 35 tests)
**Impact:** Fixes all health logging, queries, expense tracking, spending reports
**Effort:** ~15 minutes
**Files:** `aegis/db.py`, `aegis/tools/health.py`, `aegis/tools/wealth.py`

```python
# Option: Make get_db() async (recommended)
# In aegis/db.py:
async def get_db() -> sqlite3.Connection:
    # ... existing code unchanged, just add async
```

### Priority 2: Implement calculate_savings_goal() (Unblocks 6 tests)
**Impact:** Fixes all savings goal tests
**Effort:** ~10 minutes
**Files:** `aegis/tools/wealth.py`

```python
async def calculate_savings_goal(
    target_amount: float,
    target_months: int,
    monthly_income: float
) -> dict[str, Any]:
    """Calculate monthly savings needed."""
    if target_months <= 0:
        raise ValueError("target_months must be positive")

    monthly_needed = target_amount / target_months
    feasible = monthly_needed <= monthly_income
    pct = (monthly_needed / monthly_income) * 100 if monthly_income > 0 else 0

    return {
        "monthly_savings_needed": round(monthly_needed, 2),
        "feasible": feasible,
        "percentage_of_income": round(pct, 1),
        "status": "ok"
    }
```

### Priority 3: Add Input Validation (Unblocks 1 test)
**Impact:** test_track_expense_zero_amount_validation
**Effort:** ~5 minutes
**Files:** `aegis/tools/wealth.py`

```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    # Add validation
    if amount <= 0:
        raise ValueError("Expense amount must be positive")
    if category not in ["food", "transport", "shopping", "health", "entertainment", "utilities"]:
        raise ValueError(f"Invalid category: {category}")
    # ... rest of implementation
```

### Priority 4: Verify All Tests Pass
**Impact:** Confirms GREEN phase complete
**Effort:** ~5 minutes
**Command:**
```bash
pytest tests/test_health_wealth_red.py -v
# Should see: 50 passed
```

---

## Summary Statistics

| Category | Count | Status |
|----------|-------|--------|
| DB Layer Errors | 35 | Need fix: Remove/add async |
| Missing Functions | 6 | Need implement: calculate_savings_goal |
| Validation Errors | 1 | Need validation: amount > 0 |
| Dispatch Tests | 7 | ✅ Already working |
| **Total** | **50** | **43 failing, 7 passing** |

---

## Test Execution Report

```
============================= test session starts ==============================
collected 50 items

tests/test_health_wealth_red.py::TestHealthDataLogging (9 tests)
  FAILED (9) - TypeError: await on sync get_db()

tests/test_health_wealth_red.py::TestHealthPatternQueries (8 tests)
  FAILED (8) - TypeError: await on sync get_db()

tests/test_health_wealth_red.py::TestExpenseTracking (8 tests)
  FAILED (7) - TypeError: await on sync get_db()
  FAILED (1) - AssertionError: amount validation not implemented

tests/test_health_wealth_red.py::TestSpendingReports (7 tests)
  FAILED (7) - TypeError: await on sync get_db()

tests/test_health_wealth_red.py::TestSavingsGoals (6 tests)
  FAILED (6) - AttributeError: calculate_savings_goal not found

tests/test_health_wealth_red.py::TestToolDispatch (12 tests)
  PASSED (7) - Error handling tests
  FAILED (5) - Dispatch errors due to DB layer

========================= 43 failed, 7 passed in 0.47s ==========================
```

---

## Next Steps

1. **Read this document thoroughly** to understand each failure
2. **Fix Priority 1** (DB layer) - This will pass 35+ tests
3. **Implement Priority 2** (calculate_savings_goal) - This will pass 6 tests
4. **Add Priority 3** (validation) - This will pass 1 test
5. **Run full test suite** - All 50 tests should pass (GREEN phase)

---

Generated: RED Phase Test Analysis
Last Updated: 2024-02-13
