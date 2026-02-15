"""
AEGIS1 LLM Router — Multi-LLM orchestration.

Factory pattern to route between Claude, Gemini, and Ollama based on configuration.

Routing Priority:
1. USE_LOCAL_MODEL=true → OllamaClient (free, local, no API key needed)
2. USE_GEMINI_FOR_TESTING=true → GeminiClient (cheaper Anthropic alternative)
3. Default → ClaudeClient (production quality, best for demos)
"""

import logging
from typing import TYPE_CHECKING, Union

from bridge.config import settings
from bridge.claude_client import ClaudeClient

if TYPE_CHECKING:
    from bridge.gemini_client import GeminiClient
    from bridge.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


def get_llm_client() -> Union["OllamaClient", ClaudeClient, "GeminiClient"]:
    """
    Factory: Return appropriate LLM client based on configuration.

    Routing Logic:
    1. If USE_LOCAL_MODEL=true: Return OllamaClient (free, perfect for testing)
       - No API key required
       - ~200ms response time
       - Uses Phi-3-mini (7B, 4GB model)
       - Requires Ollama running locally
    
    2. Else if USE_GEMINI_FOR_TESTING=true: Return GeminiClient (budget testing)
       - Cheaper than Claude
       - Preserves Anthropic API credits for final demo
    
    3. Else: Return ClaudeClient (production)
       - Best quality responses
       - Full tool integration
       - For final demo and real usage

    This allows seamless switching for different phases:
    - Development: USE_LOCAL_MODEL=true (free iteration)
    - Budget demo: USE_GEMINI_FOR_TESTING=true
    - Final demo: Default Claude (highest quality)

    Returns:
        LLM client instance (OllamaClient, ClaudeClient, or GeminiClient)

    Raises:
        ValueError: If configuration is invalid
    """
    if settings.use_local_model:
        from bridge.ollama_client import OllamaClient
        logger.info(
            "LLM Router: Using OllamaClient (local testing mode) - %s:%s",
            settings.ollama_url, settings.ollama_model
        )
        client = OllamaClient(
            base_url=settings.ollama_url,
            model_name=settings.ollama_model
        )
        
        # Warn if Ollama isn't healthy (but don't fail - it might start later)
        if not client.health_check():
            logger.warning(
                "Ollama not responding at %s. "
                "Start Ollama with: ollama serve",
                settings.ollama_url
            )
        
        return client

    elif settings.use_gemini_for_testing:
        logger.info("LLM Router: Using GeminiClient (budget testing mode)")

        if not settings.gemini_api_key:
            raise ValueError(
                "USE_GEMINI_FOR_TESTING=true but GEMINI_API_KEY is not set. "
                "Either set GEMINI_API_KEY or set USE_GEMINI_FOR_TESTING=false"
            )

        from bridge.gemini_client import GeminiClient
        return GeminiClient()

    else:
        logger.info("LLM Router: Using ClaudeClient (production mode)")
        return ClaudeClient()
