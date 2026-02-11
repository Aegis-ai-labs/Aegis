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
from bridge.tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Aegis, a voice health and wealth assistant worn as a pendant.
You speak concisely — 1-2 sentences for simple queries, up to 4 for analysis.
You have tools for health tracking and expense management.
Use tools when the user asks about their data. Don't guess — look it up.
For complex health correlations or financial planning, think step by step.
Always be warm, supportive, and actionable in your advice.
When logging data, confirm what you logged and provide brief context if relevant."""

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
                "system": SYSTEM_PROMPT,
                "messages": messages,
                "tools": TOOL_DEFINITIONS,
            }

            # Enable extended thinking for Opus on complex queries
            if is_opus:
                kwargs["thinking"] = {"type": "adaptive"}
                kwargs["output_config"] = {"effort": "medium"}

            response = self.client.messages.create(**kwargs)
            latency_ms = (time.monotonic() - start_time) * 1000

            # Process response content blocks
            tool_use_blocks = []
            text_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_blocks.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)
                # thinking blocks are internal, we skip them

            # Yield any text we got
            for text in text_blocks:
                full_response += text
                yield text

            # If no tool calls, we're done
            if not tool_use_blocks:
                break

            # Execute tool calls and continue conversation
            assistant_content = list(response.content)
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for tool_block in tool_use_blocks:
                logger.info(
                    "Tool call: %s(%s)",
                    tool_block.name,
                    json.dumps(tool_block.input)[:100],
                )
                result = await execute_tool(tool_block.name, tool_block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
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
