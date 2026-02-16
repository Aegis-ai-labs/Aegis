"""
Ollama Local LLM Client — Free alternative for testing (Phi-3-mini).

This client connects to a local Ollama instance for cost-free testing.
No API keys required. Perfect for development and iteration.

Usage:
    1. Install Ollama: https://ollama.ai
    2. Pull model: ollama pull phi3
    3. Start Ollama: ollama serve
    4. Set USE_LOCAL_MODEL=true in .env
    5. Server will auto-use OllamaClient instead of Claude
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional

import aiohttp

from bridge.config import settings

logger = logging.getLogger(__name__)\

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OllamaClient:
    """Local LLM client using Ollama (Phi-3-mini or similar)."""

    def __init__(self, base_url: str = "", model_name: str = ""):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama API URL (e.g., http://localhost:11434)
            model_name: Model name (e.g., "phi3", "mistral", "llama2")
        """
        self.base_url = base_url or settings.ollama_url
        self.model = model_name or settings.ollama_model
        self.conversation_history = []
        
        logger.info(
            "OllamaClient initialized: %s (model=%s)",
            self.base_url, self.model
        )

    async def get_response(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Get streaming response from Ollama.
        
        This is a simplified implementation that doesn't use tools
        (tool use requires function calling, which Phi-3 has limited support for).
        
        For testing purposes, responses are direct text without tool invocation.
        Claude will still handle tool use in production mode.
        
        Args:
            user_message: User's input text
            
        Yields:
            Response chunks as they arrive
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        messages_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in self.conversation_history
        ])

        prompt = f"""{messages_text}
ASSISTANT:"""

        start_time = time.monotonic()
        
        try:
            # Use aiohttp for async requests
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": 0.7,
                    "num_predict": 200,  # Keep responses reasonably short
                }

                full_response = ""

                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            "Ollama API error: %d - %s",
                            response.status, error_text[:200]
                        )
                        yield f"[Error: Ollama returned {response.status}]"
                        return

                    async for line in response.content:
                        try:
                            if line:
                                chunk_data = json.loads(line.decode())
                                if "response" in chunk_data:
                                    text_chunk = chunk_data["response"]
                                    full_response += text_chunk
                                    yield text_chunk
                        except json.JSONDecodeError:
                            pass

            # Add response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response,
            })

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Ollama response [%.0fms, %d chars]: %s",
                elapsed_ms, len(full_response),
                full_response[:80]
            )

        except aiohttp.ClientConnectorError as e:
            logger.error(
                "Ollama connection error: %s. "
                "Is Ollama running? Start with: ollama serve",
                str(e)
            )
            yield "[Error: Cannot connect to Ollama. Start with: ollama serve]"
        except Exception as e:
            logger.error("Ollama error: %s", str(e), exc_info=True)
            yield f"[Error: {str(e)[:100]}]"

    def reset_conversation(self):
        """Clear conversation history for fresh start."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def health_check(self) -> bool:
        """Check if Ollama is running and responding.
        
        Returns:
            True if Ollama is healthy, False otherwise
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available; skipping health check")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=2
            )
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.info("Ollama health check passed")
            else:
                logger.warning("Ollama health check failed: %d", response.status_code)
            return is_healthy
        except Exception as e:
            logger.warning("Ollama health check error: %s", str(e))
            return False
