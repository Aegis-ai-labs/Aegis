"""
AEGIS1 Gemini Client — Streaming LLM with tool use.

Alternative LLM client using Google Gemini for testing phase
to preserve Anthropic API credits for final demo.
"""

import json
import logging
import time
from typing import AsyncGenerator

import google.generativeai as genai

from bridge.config import settings
from bridge.context import build_health_context
from bridge.tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

# Import for dashboard broadcasting
_broadcast_callback = None

def set_dashboard_broadcast(callback):
    """Set the broadcast callback from main.py to avoid circular imports."""
    global _broadcast_callback
    _broadcast_callback = callback

async def _broadcast_if_available(event: dict):
    """Broadcast to dashboard if callback is set."""
    if _broadcast_callback:
        try:
            await _broadcast_callback(event)
        except Exception:
            pass  # Don't let dashboard errors break pipeline

# System prompt for Gemini (similar to Claude but adapted)
SYSTEM_PROMPT = """You are Aegis, a voice health and wealth assistant worn as a pendant.

## Voice Constraints
- Speak concisely: 1-2 sentences for simple queries, up to 4 for complex analysis
- Respond as if talking to a friend — warm, supportive, actionable
- Never mention you're an AI or reference using tools

## Core Capabilities
- Health tracking: sleep, exercise, mood, weight, heart rate, steps, water intake
- Expense management: track spending, categorize, analyze patterns
- Proactive insights: notice correlations, suggest improvements

## Tool Use Behavioral Directives
- ALWAYS use tools to look up user data — never guess or make up numbers
- When logging data, confirm what was saved + provide brief context
- For complex correlations (sleep→mood, spending→categories), use multiple tools
- For patterns over time, call get_health_context or get_spending_summary first
- Save discovered insights with save_user_insight for continuity across sessions"""


def convert_tools_to_gemini_format(claude_tools: list[dict]) -> list[dict]:
    """
    Convert Claude tool format to Gemini function calling format.

    Claude format:
    {
        "name": "log_health",
        "description": "Log health data...",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }

    Gemini format (simplified - no type field):
    {
        "name": "log_health",
        "description": "Log health data...",
        "parameters": {
            "properties": {...},
            "required": [...]
        }
    }
    """
    gemini_tools = []
    for tool in claude_tools:
        # Copy schema but remove top-level "type": "object"
        # Gemini doesn't use this field
        schema = dict(tool["input_schema"])
        schema.pop("type", None)  # Remove "type" field

        gemini_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": schema
        })
    return gemini_tools


class GeminiClient:
    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required when USE_GEMINI_FOR_TESTING=true"
            )

        genai.configure(api_key=settings.gemini_api_key)

        # Convert tools to Gemini format
        gemini_tools = convert_tools_to_gemini_format(TOOL_DEFINITIONS)
        self.tools = [genai.protos.Tool(function_declarations=[
            genai.protos.FunctionDeclaration(**tool) for tool in gemini_tools
        ])]

        # Build system instruction with health context
        health_context = build_health_context(days=7)
        system_instruction = f"""{SYSTEM_PROMPT}

## Current User Context (last 7 days)
{health_context}"""

        # Initialize model with tools and system instruction
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            tools=self.tools,
            system_instruction=system_instruction,
        )

        self.conversation_history: list[dict] = []
        self.chat = None

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.chat = None
        logger.info("Gemini conversation reset")

    async def get_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Stream Gemini response with tool use. Yields text chunks.

        Handles the full tool use loop:
        1. Send user message
        2. If Gemini wants to use a tool → execute it → continue
        3. Yield text chunks as they arrive
        """
        start_time = time.monotonic()
        full_response = ""

        # Initialize chat if first message
        if self.chat is None:
            self.chat = self.model.start_chat(history=[])

        # Tool use loop — Gemini may call multiple tools
        max_tool_rounds = 5
        current_user_message = user_text

        for tool_round in range(max_tool_rounds):
            try:
                # Send message with streaming
                response = await self.chat.send_message_async(
                    current_user_message,
                    stream=True
                )

                # Collect response parts
                tool_calls = []
                text_parts = []

                async for chunk in response:
                    # Check for function calls
                    if chunk.candidates and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                # Store tool call
                                tool_calls.append({
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args)
                                })
                            elif hasattr(part, 'text') and part.text:
                                # Stream text
                                text_chunk = part.text
                                text_parts.append(text_chunk)
                                full_response += text_chunk
                                yield text_chunk

                # If no tool calls, we're done
                if not tool_calls:
                    break

                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    logger.info(
                        "Tool call: %s(%s)",
                        tool_name,
                        json.dumps(tool_args)[:100],
                    )

                    # Broadcast tool call to dashboard
                    await _broadcast_if_available({
                        "type": "tool_call",
                        "name": tool_name,
                        "input": tool_args
                    })

                    # Execute tool
                    result = await execute_tool(tool_name, tool_args)

                    # Broadcast tool result to dashboard
                    try:
                        result_obj = json.loads(result) if isinstance(result, str) else result
                    except (json.JSONDecodeError, TypeError, ValueError) as e:
                        logger.warning("Failed to parse tool result as JSON: %s", e)
                        result_obj = {"raw": str(result)}

                    await _broadcast_if_available({
                        "type": "tool_result",
                        "name": tool_name,
                        "result": result_obj
                    })

                    tool_results.append({
                        "name": tool_name,
                        "response": result
                    })

                # Send tool results back to model
                # Build function response parts
                function_response_parts = [
                    genai.protos.Part(function_response=genai.protos.FunctionResponse(
                        name=tr["name"],
                        response={"result": tr["response"]}
                    ))
                    for tr in tool_results
                ]

                # Continue conversation with tool results
                current_user_message = function_response_parts

            except Exception as e:
                logger.error("Gemini API error: %s", str(e), exc_info=True)
                raise

        # Save to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_text
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })

        # Keep conversation history manageable (last 10 turns = 20 messages)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        latency_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Response complete: model=%s, latency=%.0fms, length=%d chars",
            settings.gemini_model, latency_ms, len(full_response),
        )

    async def get_full_response(self, user_text: str) -> str:
        """Get complete response (non-streaming). Useful for testing."""
        chunks = []
        async for chunk in self.get_response(user_text):
            chunks.append(chunk)
        return "".join(chunks)
