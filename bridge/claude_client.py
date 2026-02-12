"""
AEGIS1 Claude Client — Streaming LLM with tool use.

The core innovation: Haiku for speed, Opus for depth.
Streaming responses with tool call loop.
"""

import json
import logging
import time
from typing import AsyncGenerator

import anthropic

from bridge.config import settings
from bridge.context import build_health_context
from bridge.tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

# 3-LAYER SYSTEM PROMPT with Prompt Caching
# Layer 1: Static persona (CACHEABLE)
SYSTEM_PROMPT_LAYER1 = """You are Aegis, a voice health and wealth assistant worn as a pendant.

## Voice Constraints
- Speak concisely: 1-2 sentences for simple queries, up to 4 for complex analysis
- Respond as if talking to a friend — warm, supportive, actionable
- Never mention you're an AI or reference using tools

## Core Capabilities
- Health tracking: sleep, exercise, mood, weight, heart rate, steps, water intake
- Expense management: track spending, categorize, analyze patterns
- Proactive insights: notice correlations, suggest improvements"""

# Layer 3: Tool use directives (CACHEABLE)
SYSTEM_PROMPT_LAYER3 = """## Tool Use Behavioral Directives
- ALWAYS use tools to look up user data — never guess or make up numbers
- When logging data, confirm what was saved + provide brief context
- For complex correlations (sleep→mood, spending→categories), use multiple tools
- For patterns over time, call get_health_context or get_spending_summary first
- Save discovered insights with save_user_insight for continuity across sessions"""

# Backward compatibility for tests
SYSTEM_PROMPT = SYSTEM_PROMPT_LAYER1


def build_system_messages() -> list[dict]:
    """Build 3-layer system prompt with dynamic health context and caching."""
    # Layer 2: Dynamic health snapshot (regenerated per request)
    health_context = build_health_context(days=7)
    layer2_content = f"""## Current User Context (last 7 days)
{health_context}"""

    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT_LAYER1,
            "cache_control": {"type": "ephemeral"}  # Cache static persona
        },
        {
            "type": "text",
            "text": layer2_content  # Dynamic health data (not cached)
        },
        {
            "type": "text",
            "text": SYSTEM_PROMPT_LAYER3,
            "cache_control": {"type": "ephemeral"}  # Cache tool directives
        }
    ]

# Keywords that trigger Opus 4.6 for deep analysis
OPUS_TRIGGERS = [
    "analyze", "pattern", "trend", "plan", "correlat", "compare",
    "why am i", "why do i", "what's causing", "relationship between",
    "over time", "savings goal", "financial plan", "budget plan",
]


def select_model(user_text: str) -> str:
    """Route to Opus for complex analysis, Haiku for everything else."""
    text_lower = user_text.lower()
    for trigger in OPUS_TRIGGERS:
        if trigger in text_lower:
            logger.info("Model routing: Opus 4.6 (trigger: %s)", trigger)
            return settings.claude_opus_model
    logger.info("Model routing: Haiku 4.5 (fast path)")
    return settings.claude_haiku_model


class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.conversation_history: list[dict] = []

    def reset_conversation(self):
        self.conversation_history = []

    async def get_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Stream Claude response with tool use. Yields text chunks.

        Handles the full tool use loop:
        1. Send user message
        2. If Claude wants to use a tool → execute it → continue
        3. Yield text chunks as they arrive
        """
        self.conversation_history.append({"role": "user", "content": user_text})

        model = select_model(user_text)
        is_opus = model == settings.claude_opus_model

        start_time = time.monotonic()
        full_response = ""

        # Tool use loop — Claude may call multiple tools
        messages = list(self.conversation_history)
        max_tool_rounds = 5

        for tool_round in range(max_tool_rounds):
            kwargs = {
                "model": model,
                "max_tokens": settings.claude_max_tokens if not is_opus else 1024,
                "system": build_system_messages(),  # 3-layer prompt with health context + caching
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
            }

            # Enable extended thinking for Opus with INTERLEAVED THINKING
            if is_opus:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
                kwargs["betas"] = ["interleaved-thinking-2025-05-14"]

            # TRUE STREAMING: Token-by-token delivery via messages.stream()
            tool_use_blocks = []
            current_tool = None
            current_thinking = None
            assistant_content_blocks = []

            async with self.client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    # Handle streaming events
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }
                        elif event.content_block.type == "thinking":
                            current_thinking = []

                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            # Stream text token-by-token
                            text_chunk = event.delta.text
                            full_response += text_chunk
                            yield text_chunk
                        elif hasattr(event.delta, "thinking"):
                            # Accumulate thinking for logging
                            if current_thinking is not None:
                                current_thinking.append(event.delta.thinking)
                        elif hasattr(event.delta, "partial_json"):
                            # Accumulate tool input JSON
                            if current_tool:
                                current_tool["input_json"] += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool:
                            tool_use_blocks.append(current_tool)
                            current_tool = None
                        elif current_thinking is not None:
                            # Log thinking block for dashboard visibility
                            thinking_text = "".join(current_thinking)
                            logger.info(
                                "Opus thinking [%d chars]: %s...",
                                len(thinking_text),
                                thinking_text[:200]
                            )
                            current_thinking = None

                # Get final message for history
                final_message = await stream.get_final_message()
                assistant_content_blocks = list(final_message.content)

            latency_ms = (time.monotonic() - start_time) * 1000

            # If no tool calls, we're done
            if not tool_use_blocks:
                break

            # Execute tool calls and continue conversation
            messages.append({"role": "assistant", "content": assistant_content_blocks})

            tool_results = []
            for tool in tool_use_blocks:
                try:
                    tool_input = json.loads(tool["input_json"]) if tool["input_json"] else {}
                except json.JSONDecodeError:
                    tool_input = {}

                logger.info(
                    "Tool call: %s(%s)",
                    tool["name"],
                    json.dumps(tool_input)[:100],
                )
                result = await execute_tool(tool["name"], tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool["id"],
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        # Save assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": full_response})

        # Keep conversation history manageable (last 20 turns)
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-20:]

        logger.info(
            "Response complete: model=%s, latency=%.0fms, length=%d chars",
            model, latency_ms, len(full_response),
        )

    async def get_full_response(self, user_text: str) -> str:
        """Get complete response (non-streaming). Useful for testing."""
        chunks = []
        async for chunk in self.get_response(user_text):
            chunks.append(chunk)
        return "".join(chunks)
