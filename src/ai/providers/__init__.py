"""AIプロバイダー

各AIプロバイダー（OpenAI, Anthropic, Google, Groq）の実装を提供します。

Example:
    >>> from src.ai.providers import OpenAIProvider
    >>> provider = OpenAIProvider(api_key="sk-...", model="gpt-4o-mini")
    >>> result = await provider.generate("Hello!")

    >>> from src.ai.providers import AnthropicProvider
    >>> provider = AnthropicProvider(api_key="sk-ant-...", model="claude-3-5-sonnet-20241022")
    >>> result = await provider.generate("Hello!")

    >>> from src.ai.providers import GoogleProvider
    >>> provider = GoogleProvider(api_key="AIza...", model="gemini-1.5-flash")
    >>> result = await provider.generate("Hello!")

    >>> from src.ai.providers import GroqProvider
    >>> provider = GroqProvider(api_key="gsk_...", model="llama-3.1-70b-versatile")
    >>> result = await provider.generate("Hello!")
"""

from src.ai.providers.anthropic import AnthropicProvider
from src.ai.providers.google import GoogleProvider
from src.ai.providers.groq import GroqProvider
from src.ai.providers.openai import OpenAIProvider

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
]
