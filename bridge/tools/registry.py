"""Tool registry — Claude tool definitions + dispatch."""

import json
from bridge.tools import health, wealth

TOOL_DEFINITIONS = [
    {
        "name": "get_health_context",
        "description": "Retrieve user's health metrics with statistical summaries (avg/min/max). Use when user asks 'how did I...', 'what was my...', or mentions health tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back", "default": 7},
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Which metrics: sleep_hours, steps, heart_rate, mood, weight, water, exercise_minutes",
                },
            },
        },
    },
    {
        "name": "log_health",
        "description": "Save a health metric the user reports (e.g., 'I slept 7 hours', 'my mood is 4/5'). Returns weekly average for context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["sleep_hours", "steps", "heart_rate", "mood", "weight", "water", "exercise_minutes"],
                },
                "value": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["metric", "value"],
        },
    },
    {
        "name": "analyze_health_patterns",
        "description": "Get raw daily health data for correlation analysis. Use when user asks 'why', 'analyze', 'pattern', 'trend', 'relationship between' metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What pattern to analyze"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["query"],
        },
    },
    {
        "name": "track_expense",
        "description": "Log a purchase/expense the user reports (e.g., 'I spent $45 on lunch'). Returns weekly total for awareness.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "category": {
                    "type": "string",
                    "enum": ["food", "transport", "housing", "health", "entertainment", "shopping", "utilities", "other"],
                },
                "description": {"type": "string"},
            },
            "required": ["amount", "category"],
        },
    },
    {
        "name": "get_spending_summary",
        "description": "Get spending totals by category over N days. Use when user asks 'how much have I spent', 'where is my money going'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 30},
                "category": {"type": "string", "description": "Optional: filter by category"},
            },
        },
    },
    {
        "name": "calculate_savings_goal",
        "description": "Calculate savings plan to reach target amount in N months. Use when user says 'I want to save', 'help me save', 'savings goal'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_amount": {"type": "number"},
                "target_months": {"type": "integer"},
                "monthly_income": {"type": "number"},
            },
            "required": ["target_amount", "target_months"],
        },
    },
    {
        "name": "save_user_insight",
        "description": "Save a discovered pattern/insight about the user for continuity across sessions. Use when you notice a correlation, habit, or pattern worth remembering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight": {
                    "type": "string",
                    "description": "The insight to remember (e.g., 'User sleeps better on weekends', 'Spending spikes on Fridays')"
                },
            },
            "required": ["insight"],
        },
    },
]

HANDLERS = {
    "get_health_context": health.get_health_context,
    "log_health": health.log_health,
    "analyze_health_patterns": health.analyze_health_patterns,
    "track_expense": wealth.track_expense,
    "get_spending_summary": wealth.get_spending_summary,
    "calculate_savings_goal": wealth.calculate_savings_goal,
    "save_user_insight": health.save_user_insight,
}


async def execute_tool(name: str, arguments: dict) -> str:
    """Route tool call to implementation. Returns JSON string."""
    handler = HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = await handler(**arguments)
    return json.dumps(result)
