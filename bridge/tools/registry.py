"""Tool registry — Claude tool definitions + dispatch."""

import json
from bridge.tools import health, wealth

TOOL_DEFINITIONS = [
    {
        "name": "get_health_context",
        "description": "Get user's recent health data (sleep, steps, heart rate, mood, weight). Call this when user asks about their health.",
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
        "description": "Log a health data point the user reports.",
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
        "description": "Deep analysis of health trends and correlations. Use for complex questions about health patterns over time.",
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
        "description": "Record an expense the user mentions.",
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
        "description": "Get spending summary for a time period.",
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
        "description": "Calculate how to reach a savings target based on current spending patterns.",
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
]

HANDLERS = {
    "get_health_context": health.get_health_context,
    "log_health": health.log_health,
    "analyze_health_patterns": health.analyze_health_patterns,
    "track_expense": wealth.track_expense,
    "get_spending_summary": wealth.get_spending_summary,
    "calculate_savings_goal": wealth.calculate_savings_goal,
}


async def execute_tool(name: str, arguments: dict) -> str:
    """Route tool call to implementation. Returns JSON string."""
    handler = HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    result = await handler(**arguments)
    return json.dumps(result)
