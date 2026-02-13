"""Claude API client — streaming responses with tool use and sentence buffering."""

import json
import logging
import re
import time
from typing import AsyncGenerator

import anthropic

from .config import settings
from .context import build_health_context
from .db import get_db
from .tools.registry import TOOL_DEFINITIONS, dispatch_tool

log = logging.getLogger(__name__)

# Model selection constants
OPUS_TRIGGERS = ["complex", "detailed", "explain", "analyze", "trend", "plan", "why", "correlate"]

def select_model(query: str) -> str:
    """Select Claude model based on query complexity."""
    query_lower = query.lower()
    if any(trigger in query_lower for trigger in OPUS_TRIGGERS):
        return settings.claude_opus_model
    return settings.claude_haiku_model

SYSTEM_PROMPT_BASE = """You are Aegis, a concise voice assistant for health and wealth management.

Rules:
- Keep responses under 2 sentences for simple queries, 3 for complex.
- Speak naturally as if talking to a friend.
- Use tools to log/retrieve data — never guess numbers.
- When logging data, confirm briefly what was saved.
- For health summaries, highlight trends and actionable insights.
- For spending, mention totals and biggest categories.
- If unsure what the user wants, ask one clarifying question.
- Never mention you are an AI or that you are using tools."""

# Export for test compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_BASE

# Regex to split text into sentences for TTS streaming
SENTENCE_RE = re.compile(r"([^.\!?]+[.\!?]+)\s*")


class ClaudeClient:
    """Streaming Claude client with tool use loop."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.conversation_history: list[dict] = []
        self.max_history = 20  # Keep last 20 turns to fit context

    def _trim_history(self):
        """Keep conversation history within bounds."""
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history :]

    async def get_system_prompt(self) -> str:
        """Build dynamic system prompt with current health context."""
        db = get_db()
        health_context = build_health_context(db)
        if health_context:
            return f"{SYSTEM_PROMPT_BASE}\n\n{health_context}"
        return SYSTEM_PROMPT_BASE

    async def chat(self, user_text: str) -> AsyncGenerator[str, None]:
        """Send user text to Claude, handle tool calls, yield sentence chunks.
        Yields complete sentences as they are assembled from the stream,
        enabling TTS to start speaking before the full response is ready.
        """
        self.conversation_history.append({"role": "user", "content": user_text})
        self._trim_history()

        # Tool use loop: Claude may call tools, then we feed results back
        max_tool_rounds = 5
        for _ in range(max_tool_rounds):
            buffer = ""
            tool_use_blocks = []
            current_tool = None

            t0 = time.monotonic()

            async with self.client.messages.stream(
                model=settings.claude_haiku_model,
                max_tokens=settings.claude_max_tokens,
                system=await self.get_system_prompt(),
                tools=TOOL_DEFINITIONS,
                messages=self.conversation_history,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }
                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            buffer += event.delta.text
                            # Yield complete sentences
                            while True:
                                match = SENTENCE_RE.match(buffer)
                                if not match:
                                    break
                                sentence = match.group(1).strip()
                                if sentence:
                                    yield sentence
                                buffer = buffer[match.end() :]
                        elif hasattr(event.delta, "partial_json"):
                            if current_tool:
                                current_tool["input_json"] += event.delta.partial_json
                    elif event.type == "content_block_stop":
                        if current_tool:
                            tool_use_blocks.append(current_tool)
                            current_tool = None

                # Get the final message for history
                final_message = await stream.get_final_message()

            elapsed = time.monotonic() - t0
            log.info(f"Claude stream completed in {elapsed:.2f}s")

            # Yield any remaining text
            remaining = buffer.strip()
            if remaining:
                yield remaining

            # Add assistant message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message.content,
            })

            # If no tool calls, we are done
            if not tool_use_blocks:
                return

            # Execute tool calls and feed results back
            tool_results = []
            for tool in tool_use_blocks:
                try:
                    tool_input = json.loads(tool["input_json"]) if tool["input_json"] else {}
                except json.JSONDecodeError:
                    tool_input = {}

                tool_name = tool["name"]
                log.info(f"Tool call: {tool_name}({tool_input})")
                t1 = time.monotonic()
                result = await dispatch_tool(tool_name, tool_input)
                elapsed = time.monotonic() - t1
                log.info(f"Tool {tool_name} completed in {elapsed:.3f}s")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool["id"],
                    "content": result,
                })

            self.conversation_history.append({"role": "user", "content": tool_results})
            self._trim_history()
            # Loop back to get Claude response incorporating tool results

    async def reset_conversation(self):
        """Clear conversation history (alias for reset)."""
        await self.reset()

    async def get_full_response(self, message: str) -> str:
        """Get complete response as a single string (non-streaming)."""
        chunks = []
        async for chunk in self.chat(message):
            chunks.append(chunk)
        return "".join(chunks)

    async def get_response(self, message: str) -> AsyncGenerator[str, None]:
        """Get streaming response (alias for chat)."""
        async for chunk in self.chat(message):
            yield chunk

    async def reset(self):
        """Clear conversation history."""
        self.conversation_history.clear()
