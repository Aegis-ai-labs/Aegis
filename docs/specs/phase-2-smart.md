# Phase 2 Specification — Smart (Health Personalization)

**Goal:** Dynamic health-aware system prompts. Claude responses reference user's actual body data. Apple Health import working.  
**Timeline:** Day 4 (Feb 13)  
**Estimated:** 4 hours  
**Depends on:** Phase 1 complete (streaming + tools verified)  
**Status:** Not started

---

## Scope

Phase 2 transforms Claude from **generic health advisor** to **personalized body-aware AI**:

1. **Health context builder** (`aegis/context.py`): Generate dynamic summaries from user_health_logs
2. **3-layer system prompt injection**: Static cached + dynamic health context + static tools
3. **Apple Health XML import** (`aegis/health_import.py`): One-time CLI import of real user data
4. **Tool data enrichment**: Add body-aware insights to tool responses
5. **Demo data curation**: 3 compelling scenarios showcasing personalization

**Key innovation:** Every Claude request includes a dynamically regenerated health context layer, making responses reference actual patterns like "You've been sleeping less than usual this week" instead of generic advice.

**Out of scope for Phase 2:**
- Audio pipeline optimization (Phase 3)
- Conversation memory (Phase 3)
- Testing & demo recording (Phase 4)

---

## Component Specifications

### 1. Health Context Builder — `aegis/context.py`

**Purpose:** Generate natural language summary of user's recent health data for system prompt injection.

**Implementation:**

```python
"""
Health context generation for dynamic system prompt injection.
Converts user_health_logs table into natural language summaries.
"""
from aegis.db import get_db
from datetime import datetime, timedelta
from typing import Optional

async def build_health_context(
    user_id: int = 1,
    days: int = 7,
    include_patterns: bool = True
) -> str:
    """
    Generate dynamic health context for system prompt.
    
    Args:
        user_id: User ID to query
        days: Number of recent days to analyze
        include_patterns: Whether to include pattern analysis
    
    Returns:
        Natural language health summary like:
        
        User's recent health context (last 7 days):
        - Sleep: Avg 6.2 hours/night (target: 7+). Notable: 3 days <6 hours (Mon, Wed, Fri).
        - Steps: Avg 8,500/day (good). Lowest: 4,200 (Sunday). Peak: 12,300 (Wednesday).
        - Heart rate: Avg resting 68 bpm (healthy). Range: 62-75 bpm.
        - Weight: Stable at 165 lbs (±1 lb variance).
        - Exercise: 4 days with 30+ minutes.
        
        Patterns: Sleep deprivation correlates with low step count next day. 
        Weekend exercise lower than weekdays.
    """
    db = await get_db()
    start_date = datetime.now() - timedelta(days=days)
    
    # Query all health metrics for date range
    cursor = await db.execute(
        """
        SELECT metric, value, timestamp
        FROM user_health_logs
        WHERE user_id = ? AND timestamp >= ?
        ORDER BY timestamp DESC
        """,
        (user_id, start_date)
    )
    rows = await cursor.fetchall()
    
    if not rows:
        return "User's recent health context: No health data available yet. Encourage user to start tracking."
    
    # Group by metric
    metrics = {}
    for row in rows:
        metric = row['metric']
        if metric not in metrics:
            metrics[metric] = []
        metrics[metric].append({
            'value': row['value'],
            'timestamp': datetime.fromisoformat(row['timestamp'])
        })
    
    # Build summary for each metric
    summary_lines = [f"User's recent health context (last {days} days):"]
    
    for metric, values in metrics.items():
        if not values:
            continue
        
        vals = [v['value'] for v in values]
        avg = sum(vals) / len(vals)
        min_val = min(vals)
        max_val = max(vals)
        
        # Metric-specific insights
        if metric == "sleep_hours":
            target = 7.0
            below_target = sum(1 for v in vals if v < target)
            line = f"- Sleep: Avg {avg:.1f} hours/night"
            if avg < target:
                line += f" (below {target}h target)"
            if below_target > 0:
                line += f". Notable: {below_target} days <{target}h"
            summary_lines.append(line + ".")
        
        elif metric == "steps":
            goal = 10000
            line = f"- Steps: Avg {int(avg)}/day"
            if avg >= 8000:
                line += " (good)"
            elif avg < 5000:
                line += " (below active level)"
            line += f". Range: {int(min_val)}-{int(max_val)}"
            summary_lines.append(line + ".")
        
        elif metric == "heart_rate":
            line = f"- Heart rate: Avg resting {int(avg)} bpm"
            if 60 <= avg <= 80:
                line += " (healthy)"
            elif avg > 80:
                line += " (elevated - consider stress management)"
            summary_lines.append(line + f". Range: {int(min_val)}-{int(max_val)} bpm.")
        
        elif metric == "weight":
            variance = max_val - min_val
            line = f"- Weight: "
            if variance <= 2:
                line += f"Stable at {avg:.1f} lbs"
            else:
                line += f"Trending from {min_val:.1f} to {max_val:.1f} lbs"
            summary_lines.append(line + ".")
        
        elif metric == "exercise_minutes":
            active_days = sum(1 for v in vals if v >= 30)
            line = f"- Exercise: {active_days} days with 30+ minutes"
            if active_days == 0:
                line += " (consider starting activity)"
            summary_lines.append(line + ".")
    
    # Pattern analysis (if enabled)
    if include_patterns and len(metrics) > 1:
        patterns = []
        
        # Correlate sleep with next-day steps
        if "sleep_hours" in metrics and "steps" in metrics:
            # Simplified: check if low sleep days (< 6h) correlate with low steps next day
            sleep_vals = {v['timestamp'].date(): v['value'] for v in metrics['sleep_hours']}
            steps_vals = {v['timestamp'].date(): v['value'] for v in metrics['steps']}
            
            low_sleep_low_steps = 0
            for date, sleep in sleep_vals.items():
                next_day = date + timedelta(days=1)
                if sleep < 6 and next_day in steps_vals and steps_vals[next_day] < 6000:
                    low_sleep_low_steps += 1
            
            if low_sleep_low_steps >= 2:
                patterns.append("Sleep deprivation correlates with low step count next day")
        
        # Weekend vs weekday exercise
        if "exercise_minutes" in metrics:
            weekday_avg = sum(v['value'] for v in metrics['exercise_minutes'] 
                             if v['timestamp'].weekday() < 5) / max(sum(1 for v in metrics['exercise_minutes'] if v['timestamp'].weekday() < 5), 1)
            weekend_avg = sum(v['value'] for v in metrics['exercise_minutes'] 
                             if v['timestamp'].weekday() >= 5) / max(sum(1 for v in metrics['exercise_minutes'] if v['timestamp'].weekday() >= 5), 1)
            
            if abs(weekday_avg - weekend_avg) > 15:
                if weekend_avg < weekday_avg:
                    patterns.append("Weekend exercise lower than weekdays")
                else:
                    patterns.append("Weekend exercise higher than weekdays")
        
        if patterns:
            summary_lines.append("")
            summary_lines.append("Patterns: " + ". ".join(patterns) + ".")
    
    return "\n".join(summary_lines)
```

**Example output:**

```
User's recent health context (last 7 days):
- Sleep: Avg 6.2 hours/night (below 7h target). Notable: 3 days <7h.
- Steps: Avg 8,500/day (good). Range: 4200-12300.
- Heart rate: Avg resting 68 bpm (healthy). Range: 62-75 bpm.
- Weight: Stable at 165 lbs.
- Exercise: 4 days with 30+ minutes.

Patterns: Sleep deprivation correlates with low step count next day. Weekend exercise lower than weekdays.
```

**Test:**

```python
import asyncio
from aegis.context import build_health_context

async def test():
    context = await build_health_context(user_id=1, days=7)
    print(context)
    assert "Sleep:" in context
    assert "Steps:" in context
    assert "avg" in context.lower() or "Avg" in context

asyncio.run(test())
```

**Acceptance criteria:**
- ✅ Generates natural language summary (not JSON)
- ✅ Includes avg/min/max/notable events per metric
- ✅ Pattern analysis identifies correlations (sleep→steps, weekday vs weekend)
- ✅ Graceful when no data (encourages user to start tracking)
- ✅ Executes in <50ms (indexed query on user_health_logs)

---

### 2. Dynamic System Prompt Injection — `aegis/claude_client.py`

**Current state:** Single static system prompt

**Required change:** 3-layer architecture with mixed caching

**Implementation:**

```python
# In aegis/claude_client.py:

from aegis.context import build_health_context

# Layer 1: Static cached persona & rules
SYSTEM_PROMPT_PERSONA = """You are AEGIS, a voice assistant for a health & wealth tracking pendant worn by the user.

Voice-optimized guidelines:
- Be concise: 1-2 sentences for simple queries, up to 4 sentences for analysis
- Use present tense, warm tone, actionable advice
- Speak naturally (avoid formal language like "Let me assist you")
- Reference the user's actual data when relevant

Example good responses:
- "You slept 6.5 hours last night. That's below your usual 7 hours."
- "You've spent $340 on food this month, averaging $11 per day. Your restaurant spending is up this week."

Example bad responses:
- "I will now proceed to analyze your health metrics." (too formal)
- "Based on the data, it appears..." (robotic, not conversational)
"""

# Layer 3: Static cached tool directives
SYSTEM_PROMPT_TOOLS = """Available tools for querying and writing data:

Health tools:
- get_health_context: Retrieve health summary for last N days
- log_health: Log a health metric (sleep, steps, heart_rate, weight, exercise_minutes)
- analyze_patterns: Get daily records for trend analysis

Wealth tools:
- track_expense: Log an expense (returns week total in category)
- spending_summary: Get spending breakdown for last N days
- savings_goal: Calculate monthly savings needed for a goal

Profile tool:
- save_user_insight: Store user preference, goal, or constraint

Tool usage rules:
- Always use tools to query/write data — never hallucinate numbers
- Max 5 tool call rounds per conversation turn
- If a tool returns an error, explain the error to the user in plain language
"""

async def chat(self, user_text: str) -> AsyncGenerator[str, None]:
    """
    Streaming chat with 3-layer dynamic system prompt.
    
    Layer 1: Static cached persona (ephemeral cache)
    Layer 2: Dynamic health context (fresh every call, no cache)
    Layer 3: Static cached tool directives (ephemeral cache)
    """
    # Generate dynamic health context (Layer 2)
    health_context = await build_health_context(user_id=1, days=7)
    
    # Construct 3-layer system prompt
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT_PERSONA,
            "cache_control": {"type": "ephemeral"}  # Cached after first request
        },
        {
            "type": "text",
            "text": health_context,
            # No cache control — fresh every call
        },
        {
            "type": "text",
            "text": SYSTEM_PROMPT_TOOLS,
            "cache_control": {"type": "ephemeral"}  # Cached after first request
        }
    ]
    
    # Add user message to conversation history
    self.conversation_history.append({
        "role": "user",
        "content": user_text
    })
    
    # Stream from Claude with 3-layer system
    with self.client.messages.stream(
        model=self.select_model(user_text),
        max_tokens=self.max_tokens,
        system=system_blocks,  # 3-layer injection
        messages=self.conversation_history,
        tools=TOOL_DEFINITIONS,
        # ... (rest of streaming logic)
    ) as stream:
        # ... (existing streaming + tool loop code)
```

**Latency benefit:**
- First request: Persona + Tools layers cached (~200ms TTFT)
- Subsequent requests: Only health context regenerated, persona/tools served from cache (~150ms TTFT, 50ms savings)

**Test:**

```python
import asyncio
from aegis.claude_client import ClaudeClient

async def test_personalization():
    client = ClaudeClient()
    
    # Seed user with poor sleep data (simulate 5 days <6h)
    from aegis.tools.health import log_health
    from datetime import datetime, timedelta
    for i in range(5):
        date = (datetime.now() - timedelta(days=i)).isoformat()
        await log_health("sleep_hours", 5.5, "Poor sleep", timestamp=date)
    
    # Query should reference actual data
    response = ""
    async for chunk in client.chat("How am I doing?"):
        response += chunk
    
    print(response)
    assert "sleep" in response.lower()
    assert "5" in response or "six" in response.lower()  # Should mention actual value
    assert "below" in response.lower() or "less" in response.lower()  # Should note it's low

asyncio.run(test_personalization())
```

**Acceptance criteria:**
- ✅ System prompt uses 3-layer structure
- ✅ Health context regenerated every call (not cached)
- ✅ Persona + tools cached (verify via API response metadata)
- ✅ Claude responses reference actual user data ("You've been sleeping 6.2h...")
- ✅ Not generic advice ("Most people need 7-9 hours...")

---

### 3. Apple Health XML Import — `aegis/health_import.py`

**Purpose:** One-time CLI import of real user health data from Apple Health export.

**Apple Health Export Format:**

- XML file: `export.xml`
- Records: `<Record type="HKQuantityTypeIdentifier..." value="..." startDate="..." />`
- Size: 50-500 MB typical
- Contains: 100+ metric types, we extract 5

**Target metrics:**

| Apple Health Type | AEGIS metric | Unit | Notes |
|-------------------|--------------|------|-------|
| `HKQuantityTypeIdentifierStepCount` | `steps` | count | Daily total |
| `HKQuantityTypeIdentifierHeartRate` | `heart_rate` | bpm | Average resting |
| `HKQuantityTypeIdentifierBodyMass` | `weight` | lbs | Convert from kg if needed |
| `HKQuantityTypeIdentifierAppleExerciseTime` | `exercise_minutes` | minutes | Daily total |
| `HKCategoryTypeIdentifierSleepAnalysis` | `sleep_hours` | hours | Compute from sleep duration records |

**Implementation:**

```python
"""
Apple Health XML import for real user data.
Parses export.xml and loads into user_health_logs table.
"""
from lxml import etree
from datetime import datetime
from aegis.db import get_db
from typing import Dict, List, Tuple
import asyncio

# Apple Health type identifiers
HEALTH_TYPE_MAPPING = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierBodyMass": "weight",
    "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_minutes",
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep_hours"
}

async def parse_apple_health_xml(xml_path: str) -> Dict[str, List[Tuple[datetime, float]]]:
    """
    Parse Apple Health export.xml and extract 5 quantitative types.
    
    Args:
        xml_path: Path to export.xml file
    
    Returns:
        Dict mapping metric name to list of (timestamp, value) tuples
        Example: {
            "steps": [(datetime(...), 8500), ...],
            "heart_rate": [(datetime(...), 68), ...],
            ...
        }
    """
    records = {
        "steps": [],
        "heart_rate": [],
        "weight": [],
        "exercise_minutes": [],
        "sleep_hours": []
    }
    
    # Parse XML incrementally (streaming for large files)
    context = etree.iterparse(xml_path, events=('end',), tag='Record')
    
    for event, elem in context:
        record_type = elem.get('type')
        
        if record_type in HEALTH_TYPE_MAPPING:
            metric = HEALTH_TYPE_MAPPING[record_type]
            
            try:
                # Parse value
                value_str = elem.get('value')
                if not value_str:
                    continue
                value = float(value_str)
                
                # Convert units if needed
                if metric == "weight":
                    unit = elem.get('unit', 'lb')
                    if unit == 'kg':
                        value = value * 2.20462  # kg to lbs
                
                elif metric == "sleep_hours":
                    # Sleep is duration in minutes, convert to hours
                    value = value / 60.0
                
                # Parse timestamp
                start_date = elem.get('startDate')
                if not start_date:
                    continue
                timestamp = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                
                records[metric].append((timestamp, value))
            
            except (ValueError, TypeError):
                # Skip malformed records
                pass
        
        # Clear element to free memory (important for large files)
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    
    del context
    
    return records

async def load_to_database(
    user_id: int,
    records: Dict[str, List[Tuple[datetime, float]]],
    deduplicate: bool = True
) -> Dict[str, int]:
    """
    Load parsed health records into user_health_logs table.
    
    Args:
        user_id: User ID to import for
        records: Dict from parse_apple_health_xml
        deduplicate: If True, skip records with duplicate (user_id, metric, timestamp)
    
    Returns:
        Dict with import stats: {"steps": 365, "heart_rate": 1200, ...}
    """
    db = await get_db()
    stats = {}
    
    for metric, entries in records.items():
        if not entries:
            stats[metric] = 0
            continue
        
        # Sort by timestamp
        entries.sort(key=lambda x: x[0])
        
        # Batch insert with conflict handling
        inserted = 0
        for timestamp, value in entries:
            try:
                if deduplicate:
                    # Check if exists
                    cursor = await db.execute(
                        "SELECT 1 FROM user_health_logs WHERE user_id = ? AND metric = ? AND timestamp = ?",
                        (user_id, metric, timestamp.isoformat())
                    )
                    if await cursor.fetchone():
                        continue  # Skip duplicate
                
                # Insert
                await db.execute(
                    "INSERT INTO user_health_logs (user_id, metric, value, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, metric, value, timestamp.isoformat())
                )
                inserted += 1
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to insert {metric} record: {e}")
        
        await db.commit()
        stats[metric] = inserted
    
    return stats

async def import_apple_health(xml_path: str, user_id: int = 1) -> None:
    """
    Full import pipeline: parse XML + load to database.
    
    Args:
        xml_path: Path to Apple Health export.xml
        user_id: User ID to import for
    """
    print(f"Parsing Apple Health export from {xml_path}...")
    records = await parse_apple_health_xml(xml_path)
    
    total_records = sum(len(entries) for entries in records.values())
    print(f"Found {total_records} health records across 5 metrics")
    
    print("Loading to database...")
    stats = await load_to_database(user_id, records, deduplicate=True)
    
    print("\nImport complete:")
    for metric, count in stats.items():
        print(f"  - {metric}: {count} records")
```

**CLI integration** (`aegis/__main__.py`):

```python
@main.command()
@click.argument('xml_path', type=click.Path(exists=True))
@click.option('--user-id', default=1, help='User ID to import for')
def import_health(xml_path: str, user_id: int):
    """Import Apple Health XML export"""
    from aegis.health_import import import_apple_health
    asyncio.run(import_apple_health(xml_path, user_id))
```

**Usage:**

```bash
# Export from iPhone: Settings → Health → Profile → Export All Health Data → export.zip
# Extract: unzip export.zip → export.xml

# Import
python -m aegis import-health ~/Downloads/apple_health_export/export.xml

# Verify
python -c "
import asyncio
from aegis.db import get_db

async def check():
    db = await get_db()
    cursor = await db.execute('SELECT metric, COUNT(*) FROM user_health_logs GROUP BY metric')
    for row in await cursor.fetchall():
        print(f'{row[0]}: {row[1]} records')

asyncio.run(check())
"
```

**Acceptance criteria:**
- ✅ Parses real Apple Health export.xml (50-500 MB)
- ✅ Extracts 5 metrics (steps, heart_rate, weight, exercise_minutes, sleep_hours)
- ✅ Converts units (kg → lbs, minutes → hours)
- ✅ Deduplicates on (user_id, metric, timestamp)
- ✅ Handles large files efficiently (streaming parse, memory-safe)
- ✅ CLI command works: `python -m aegis import-health export.xml`

---

### 4. Tool Data Enrichment

**Goal:** Add body-aware insights to tool responses (not just raw data).

**Example enhancement** (`aegis/tools/health.py`):

```python
async def get_health_context(days: int = 7, metrics: list[str] | None = None) -> dict:
    """Enhanced with insights"""
    data = await _query_health_data(days, metrics)
    
    # Add insights based on actual values
    insights = []
    
    if "sleep_hours" in data:
        avg_sleep = data["sleep_hours"]["avg"]
        if avg_sleep < 7.0:
            days_below = sum(1 for v in data["sleep_hours"]["daily"] if v < 7.0)
            insights.append(f"Sleep below recommended 7+ hours ({days_below} days this week)")
    
    if "steps" in data:
        avg_steps = data["steps"]["avg"]
        if avg_steps < 8000:
            insights.append("Step count below 10k daily goal")
        elif avg_steps >= 12000:
            insights.append("Excellent step count — well above average!")
    
    if "heart_rate" in data:
        avg_hr = data["heart_rate"]["avg"]
        if avg_hr > 80:
            insights.append("Resting heart rate elevated — consider stress management or cardio")
    
    return {
        "data": data,
        "insights": insights,
        "summary": f"{len(data)} metrics tracked over {days} days"
    }
```

**Acceptance criteria:**
- ✅ All tool responses include `insights` array (can be empty)
- ✅ Insights reference user's actual values (not generic)
- ✅ Claude can use insights in responses ("Your tool shows...")

---

### 5. Demo Data Curation

**Goal:** 3 compelling demo scenarios with realistic data showcasing personalization.

**Scenario 1: Sleep Analysis** (`docs/demo-scenarios.md`):

```markdown
## Scenario 1: Sleep Analysis

**Query:** "Why am I always tired on Mondays?"

**Demo data:**
- Last 4 weeks:
  - Mon-Thu: 6.0-6.5h sleep (alarm 6am)
  - Fri-Sat: Late to bed (1am), sleep 7-8h but shifted schedule
  - Sun: Recovery attempt (7h) but still shifted
  - Mon: 6am alarm = sleep debt

**Expected response:**
"Your Monday fatigue stems from weekend sleep schedule shifts. You're going to bed 2 hours later Friday and Saturday, recovering Sunday, but Monday's 6am alarm still cuts into your sleep debt. Try keeping bedtime within 1 hour of your weekday schedule, even on weekends."

**Opus extended thinking:**
- Analyzes 30-day pattern
- Identifies weekend shift pattern
- Correlates with Monday mood (low)
- Recommends circadian rhythm consistency
```

**Scenario 2: Spending Patterns**:

```markdown
## Scenario 2: Spending Patterns

**Query:** "How much did I spend on food this month?"

**Demo data:**
- 30 days:
  - Food category: $450 total
  - Breakdown: Groceries $180, Restaurants $270
  - 3 expensive restaurant visits ($50-$80 each)
  - Weekday lunches: $10-15 consistent
  - Weekend dining: $30-50 per meal

**Expected response:**
"You spent $450 on food this month, averaging $15 per day. Your restaurant spending is $270, with 3 high-ticket meals at $50-80 each. Your weekday lunch budget is consistent at $10-15. Consider meal prepping to reduce your restaurant habit — shifting just 2 restaurant meals per week to home cooking would save $120 per month."

**Tool enrichment:**
- spending_summary returns by-category breakdown
- Insight: "Restaurant spending 60% of food budget (national avg: 40%)"
```

**Scenario 3: Savings Goal**:

```markdown
## Scenario 3: Savings Goal

**Query:** "Help me save $5000 in 6 months."

**Demo data:**
- Current monthly spending: $2400
  - Essentials (housing, transport): $1500
  - Discretionary: $900 (food $450, entertainment $250, shopping $200)
- Monthly income: $4000 (inferred or user-provided)

**Expected response:**
"To save $5000 in 6 months, you need $833 per month. Your current spending is $2400, leaving $1600 available. You're already saving $767 per month, so you need an additional $66. I recommend reducing entertainment from $250 to $184 per month — that's 2 fewer activities or switching to lower-cost options. You're 92% of the way there already!"

**Opus extended thinking:**
- Analyzes spending categories
- Identifies discretionary cuts
- Prioritizes lowest-impact reductions
- Provides encouraging framing ("92% there!")
```

**Implementation:** Seed commands

```bash
# Seed specific scenarios
python -m aegis seed --scenario sleep_analysis
python -m aegis seed --scenario spending_patterns
python -m aegis seed --scenario savings_goal

# Or seed all 3
python -m aegis seed --demo-mode
```

**Acceptance criteria:**
- ✅ 3 scenarios documented in `docs/demo-scenarios.md`
- ✅ Seed data generates realistic patterns for each scenario
- ✅ Terminal test confirms personalized responses (not generic)
- ✅ Opus extended thinking visible in responses (reasoning about patterns)

---

## Verification Plan

### Test 1: Health Context Generation

```bash
python -c "
import asyncio
from aegis.context import build_health_context

async def test():
    context = await build_health_context(user_id=1, days=7)
    print(context)
    assert 'Sleep:' in context
    assert 'Steps:' in context
    assert 'avg' in context.lower()

asyncio.run(test())
"
```

### Test 2: Dynamic System Prompt

```bash
python -m aegis terminal
# Query: "How am I doing?"
# Expected: Mentions actual sleep/steps values, not generic advice
```

### Test 3: Apple Health Import

```bash
# Requires real export.xml
python -m aegis import-health ~/Downloads/export.xml

# Verify
sqlite3 aegis1.db "SELECT metric, COUNT(*) FROM user_health_logs GROUP BY metric;"
```

### Test 4: Enriched Tool Responses

```python
import asyncio
from aegis.tools.health import get_health_context

async def test():
    result = await get_health_context(days=7)
    assert "insights" in result
    print(f"Insights: {result['insights']}")

asyncio.run(test())
```

### Test 5: Demo Scenarios

```bash
# Seed demo data
python -m aegis seed --scenario sleep_analysis

# Terminal test
python -m aegis terminal
# Query: "Why am I always tired on Mondays?"
# Expected: Opus analyzes weekend sleep shift, recommends consistency
```

---

## Acceptance Criteria

### ✅ Phase 2 Complete When:

1. **Health context builder**: Generates natural language summary in <50ms
2. **3-layer prompts**: Persona + dynamic health + tools, with caching
3. **Personalized responses**: Claude references actual user data ("You slept 6.2h...")
4. **Apple Health import**: CLI command parses XML and loads to database
5. **Tool enrichment**: All tools include `insights` array
6. **Demo scenarios**: 3 scenarios seeded, terminal tests pass

### 🚫 Not Required for Phase 2:

- ❌ Audio pipeline optimization → Phase 3
- ❌ Conversation memory (sqlite-vec) → Phase 3
- ❌ Local LLM routing (Phi-3) → Phase 3
- ❌ ADPCM codec → Phase 3
- ❌ Comprehensive tests → Phase 4
- ❌ Demo video → Phase 4

---

## Time Estimate

| Task | Estimated Time |
|------|---------------|
| Health context builder (`context.py`) | 1h |
| 3-layer system prompt injection | 0.5h |
| Apple Health XML import (`health_import.py`) | 1.5h |
| Tool data enrichment | 0.5h |
| Demo data curation + seeding | 0.5h |
| **Total** | **4h** |

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Apple Health XML parsing issues | Medium | Use mock data for demo if real export unavailable |
| Health context generation slow | Low | Indexed queries, cache results if needed |
| Prompt caching not working | Low | Verify via API response metadata, proceed without if broken |
| Demo data unrealistic | Low | Review with health/finance domain expert |

---

## Next Steps → Phase 3

After Phase 2 acceptance criteria met:
1. Add **Silero VAD** for <1ms voice detection
2. Upgrade **STT to Moonshine** (5x faster, native streaming)
3. Verify **Kokoro TTS** (replace Piper)
4. Implement **sqlite-vec memory** for conversation recall
5. Add **Phi-3-mini routing** for simple queries (<200ms)
6. Implement **parallel Opus pattern** (Haiku ack + async Opus deep)
7. Add **ADPCM codec** for 4x audio compression
