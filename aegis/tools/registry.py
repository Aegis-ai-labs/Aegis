"""Tool registry — Claude function calling definitions + dispatch."""

import json
from typing import Any

from . import health, wealth

# Claude tool definitions (Anthropic API format)
TOOL_DEFINITIONS = [
    {
        "name": "log_health",
        "description": "Log the user's health data (sleep, steps, heart rate, mood). Use when they report health metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sleep_hours": {"type": "number", "description": "Hours of sleep (e.g. 7.5)"},
                "steps": {"type": "integer", "description": "Step count for the day"},
                "heart_rate": {"type": "integer", "description": "Average resting heart rate"},
                "mood": {
                    "type": "string",
                    "enum": ["great", "good", "okay", "tired", "stressed"],
                    "description": "How the user is feeling",
                },
                "notes": {"type": "string", "description": "Additional health notes"},
                "date": {"type": "string", "description": "Date (YYYY-MM-DD). Defaults to today."},
            },
        },
    },
    {
        "name": "get_health_today",
        "description": "Get today's health data. Use when asked about current health status.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_health_summary",
        "description": "Get health trends over recent days. Use when asked about health patterns or weekly summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to summarize (default 7)",
                    "default": 7,
                },
            },
        },
    },
    {
        "name": "track_expense",
        "description": "Record a new expense. Use when the user mentions spending money.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount spent"},
                "category": {
                    "type": "string",
                    "enum": ["food", "transport", "shopping", "health", "entertainment", "utilities"],
                    "description": "Expense category",
                },
                "description": {"type": "string", "description": "What was purchased"},
                "date": {"type": "string", "description": "Date (YYYY-MM-DD). Defaults to today."},
            },
            "required": ["amount", "category"],
        },
    },
    {
        "name": "get_spending_today",
        "description": "Get today's expenses. Use when asked about today's spending.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending_summary",
        "description": "Get spending breakdown by category over recent days. Use for spending analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default 30)",
                    "default": 30,
                },
            },
        },
    },
    {
        "name": "get_budget_status",
        "description": "Check monthly budget status including remaining allowance. Use when asked about budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_budget": {
                    "type": "number",
                    "description": "Monthly budget amount (default $3000)",
                    "default": 3000.0,
                },
            },
        },
    },
]

# Map tool names to async handler functions
_HANDLERS: dict[str, Any] = {
    "log_health": health.log_health,
    "get_health_today": health.get_health_today,
    "get_health_summary": health.get_health_summary,
    "track_expense": wealth.track_expense,
    "get_spending_today": wealth.get_spending_today,
    "get_spending_summary": wealth.get_spending_summary,
    "get_budget_status": wealth.get_budget_status,
}

async def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return JSON result string."""
    handler = _HANDLERS.get(tool_name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    try:
        result = await handler(**tool_input)
        return json.dumps(result)
    except TypeError as e:
        return json.dumps({"error": f"Invalid arguments for {tool_name}: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {e}"})
