# Implementation Checklist — GREEN Phase

**Status:** Ready for Implementation
**Total Tasks:** 11
**Estimated Time:** ~30 minutes
**Tests to Pass:** 50
**Current Status:** 7 pass, 43 fail (RED phase)

---

## Priority 1: Fix Database Layer (15 min) — UNBLOCKS 35+ TESTS

### Task 1.1: Fix DB Import/Async Issue

**File:** `aegis/tools/health.py`

Find:
```python
async def log_health(
    sleep_hours: float = None,
    steps: int = None,
    heart_rate: int = None,
    mood: str = None,
    notes: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Log health data. Defaults to today if no date provided."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def log_health(
    sleep_hours: float = None,
    steps: int = None,
    heart_rate: int = None,
    mood: str = None,
    notes: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Log health data. Defaults to today if no date provided."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.2: Fix get_health_today

**File:** `aegis/tools/health.py`

Find:
```python
async def get_health_today() -> dict[str, Any]:
    """Get today's health data."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def get_health_today() -> dict[str, Any]:
    """Get today's health data."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.3: Fix get_health_summary

**File:** `aegis/tools/health.py`

Find:
```python
async def get_health_summary(days: int = 7) -> dict[str, Any]:
    """Get health summary for the last N days."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def get_health_summary(days: int = 7) -> dict[str, Any]:
    """Get health summary for the last N days."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.4: Fix track_expense

**File:** `aegis/tools/wealth.py`

Find:
```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.5: Fix get_spending_today

**File:** `aegis/tools/wealth.py`

Find:
```python
async def get_spending_today() -> dict[str, Any]:
    """Get today's expenses."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def get_spending_today() -> dict[str, Any]:
    """Get today's expenses."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.6: Fix get_spending_summary

**File:** `aegis/tools/wealth.py`

Find:
```python
async def get_spending_summary(days: int = 30) -> dict[str, Any]:
    """Get spending summary for the last N days."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def get_spending_summary(days: int = 30) -> dict[str, Any]:
    """Get spending summary for the last N days."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Task 1.7: Fix get_budget_status

**File:** `aegis/tools/wealth.py`

Find:
```python
async def get_budget_status(monthly_budget: float = 3000.0) -> dict[str, Any]:
    """Check spending against a monthly budget."""
    db = await get_db()  # ❌ This line
```

Replace with:
```python
async def get_budget_status(monthly_budget: float = 3000.0) -> dict[str, Any]:
    """Check spending against a monthly budget."""
    db = get_db()  # ✅ Remove await
```

**Status:** [ ] Complete

---

### Verify Priority 1

Run tests:
```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_health_wealth_red.py -v --tb=no | tail -5
```

Expected:
```
35 passed in ~0.5s
```

Or you should see:
- All TestHealthDataLogging tests pass (9)
- All TestHealthPatternQueries tests pass (8)
- All TestExpenseTracking tests pass (7, 1 validation)
- All TestSpendingReports tests pass (7)
- Most TestToolDispatch tests pass

**Status:** [ ] Tests Verified

---

## Priority 2: Implement calculate_savings_goal() (10 min) — UNBLOCKS 6 TESTS

### Task 2.1: Add Function to wealth.py

**File:** `aegis/tools/wealth.py`

Add this function at the end of the file:

```python
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
        ValueError: If inputs are invalid
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

**Status:** [ ] Complete

---

### Task 2.2: Add to Tool Registry

**File:** `aegis/tools/registry.py`

Find the `TOOL_DEFINITIONS` list and add this definition:

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

**Status:** [ ] Complete

---

### Task 2.3: Add to Handlers

**File:** `aegis/tools/registry.py`

Find the `_HANDLERS` dictionary and add:

```python
"calculate_savings_goal": wealth.calculate_savings_goal,
```

So the dict looks like:
```python
_HANDLERS: dict[str, Any] = {
    "log_health": health.log_health,
    "get_health_today": health.get_health_today,
    "get_health_summary": health.get_health_summary,
    "track_expense": wealth.track_expense,
    "get_spending_today": wealth.get_spending_today,
    "get_spending_summary": wealth.get_spending_summary,
    "get_budget_status": wealth.get_budget_status,
    "calculate_savings_goal": wealth.calculate_savings_goal,  # ✅ Add this
}
```

**Status:** [ ] Complete

---

### Verify Priority 2

Run tests:
```bash
python3 -m pytest tests/test_health_wealth_red.py::TestSavingsGoals -v
```

Expected: All 6 tests pass

**Status:** [ ] Tests Verified

---

## Priority 3: Add Input Validation (5 min) — UNBLOCKS 1 TEST

### Task 3.1: Add Validation to track_expense

**File:** `aegis/tools/wealth.py`

Find:
```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    db = get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
```

Replace with:
```python
async def track_expense(
    amount: float,
    category: str,
    description: str = None,
    date: str = None,
) -> dict[str, Any]:
    """Track a new expense. Defaults to today."""
    # Validate inputs
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    
    valid_categories = {"food", "transport", "shopping", "health", "entertainment", "utilities"}
    if category not in valid_categories:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {valid_categories}")
    
    db = get_db()
    date = date or datetime.now().strftime("%Y-%m-%d")
```

**Status:** [ ] Complete

---

### Verify Priority 3

Run tests:
```bash
python3 -m pytest tests/test_health_wealth_red.py::TestExpenseTracking::test_track_expense_zero_amount_validation -v
```

Expected: Test passes

**Status:** [ ] Tests Verified

---

## Priority 4: Final Verification (5 min)

### Task 4.1: Run Full Test Suite

```bash
cd /Users/apple/documents/aegis1
python3 -m pytest tests/test_health_wealth_red.py -v
```

Expected output:
```
========================= 50 passed in ~0.5s ==========================
```

**Status:** [ ] Complete

---

### Task 4.2: Run with Coverage Check

```bash
python3 -m pytest tests/test_health_wealth_red.py --tb=short -v | head -100
```

Verify you see:
```
tests/test_health_wealth_red.py::TestHealthDataLogging (9 tests) PASSED
tests/test_health_wealth_red.py::TestHealthPatternQueries (8 tests) PASSED
tests/test_health_wealth_red.py::TestExpenseTracking (8 tests) PASSED
tests/test_health_wealth_red.py::TestSpendingReports (7 tests) PASSED
tests/test_health_wealth_red.py::TestSavingsGoals (6 tests) PASSED
tests/test_health_wealth_red.py::TestToolDispatch (12 tests) PASSED
```

**Status:** [ ] Complete

---

### Task 4.3: Quick Sanity Check

Run a single integration test manually:

```python
import asyncio
from aegis.tools import health, wealth

async def test():
    # Test health logging
    result = await health.log_health(sleep_hours=7.5)
    print(f"Health logged: {result}")
    
    # Test expense tracking
    result = await wealth.track_expense(amount=25.00, category="food")
    print(f"Expense tracked: {result}")
    
    # Test savings goal
    result = await wealth.calculate_savings_goal(
        target_amount=1200,
        target_months=6,
        monthly_income=4000
    )
    print(f"Savings goal: {result}")

asyncio.run(test())
```

Expected: No errors, all operations succeed

**Status:** [ ] Complete

---

## Summary Checklist

### Priority 1: Database Layer (7 tasks)
- [ ] Task 1.1: Fix health.log_health()
- [ ] Task 1.2: Fix health.get_health_today()
- [ ] Task 1.3: Fix health.get_health_summary()
- [ ] Task 1.4: Fix wealth.track_expense()
- [ ] Task 1.5: Fix wealth.get_spending_today()
- [ ] Task 1.6: Fix wealth.get_spending_summary()
- [ ] Task 1.7: Fix wealth.get_budget_status()
- [ ] Verify: 35+ tests pass

### Priority 2: Savings Goal (3 tasks)
- [ ] Task 2.1: Implement calculate_savings_goal()
- [ ] Task 2.2: Add to TOOL_DEFINITIONS
- [ ] Task 2.3: Add to _HANDLERS
- [ ] Verify: 6 tests pass

### Priority 3: Validation (1 task)
- [ ] Task 3.1: Add input validation to track_expense()
- [ ] Verify: 1 test passes

### Priority 4: Final Verification (3 tasks)
- [ ] Task 4.1: Run full test suite
- [ ] Task 4.2: Check all 50 pass
- [ ] Task 4.3: Manual integration test
- [ ] Verify: All tests green ✅

---

## Time Estimate

| Task | Time | Status |
|------|------|--------|
| Priority 1 (DB Layer) | 15 min | [ ] |
| Priority 2 (Savings) | 10 min | [ ] |
| Priority 3 (Validation) | 5 min | [ ] |
| Priority 4 (Verify) | 5 min | [ ] |
| **Total** | **35 min** | [ ] |

---

## Expected Results

### Before Implementation
```
========================= 43 failed, 7 passed in 0.28s ==========================
```

### After Priority 1
```
========================= 40 passed in 0.30s ==========================
```

### After Priority 2
```
========================= 46 passed in 0.30s ==========================
```

### After Priority 3
```
========================= 47 passed in 0.30s ==========================
```

### After Priority 4 (GREEN Phase Complete)
```
========================= 50 passed in 0.30s ==========================
✅ ALL TESTS GREEN - Ready for REFACTOR phase
```

---

## Notes

- All changes are straightforward copy-paste
- No new functions needed beyond calculate_savings_goal()
- No database migrations needed (schema already exists)
- Tests will guide you if you miss anything
- Run tests after each priority to verify progress

---

**Ready to implement? Let's go! 🚀**

Start with Priority 1 and work through each task systematically.
