"""
AEGIS1 LLM Router — Multi-LLM orchestration.

Factory pattern to route between Claude and Gemini based on configuration.
"""

import logging
from typing import Union

from bridge.config import settings
from bridge.claude_client import ClaudeClient
from bridge.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def get_llm_client() -> Union[ClaudeClient, GeminiClient]:
    """
    Factory: Return appropriate LLM client based on configuration.

    Routing Logic:
    - If USE_GEMINI_FOR_TESTING=true: Return GeminiClient (save Anthropic credits)
    - Else: Return ClaudeClient (default, routes Opus vs Haiku internally)

    This allows seamless switching between LLMs for testing vs production:
    - Testing phase: Use Gemini (cheaper) to preserve $100 Anthropic budget
    - Demo phase: Use Claude (higher quality) for final presentation

    Returns:
        LLM client instance (ClaudeClient or GeminiClient)

    Raises:
        ValueError: If Gemini is requested but API key is missing
    """
    if settings.use_gemini_for_testing:
        logger.info("LLM Router: Using GeminiClient (testing mode)")

        if not settings.gemini_api_key:
            raise ValueError(
                "USE_GEMINI_FOR_TESTING=true but GEMINI_API_KEY is not set. "
                "Either set GEMINI_API_KEY or set USE_GEMINI_FOR_TESTING=false"
            )

        return GeminiClient()
    else:
        logger.info("LLM Router: Using ClaudeClient (production mode)")
        return ClaudeClient()
