"""AIプロバイダー

各AIプロバイダー（OpenAI, Anthropic, Google, Groq, Local）の実装を提供します。

Example:
    >>> from src.ai.providers import OpenAIProvider
    >>> provider = OpenAIProvider(api_key="sk-...", model="gpt-4o-mini")
    >>> result = await provider.generate("Hello!")
"""

from src.ai.providers.openai import OpenAIProvider

__all__ = ["OpenAIProvider"]
