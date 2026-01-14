"""Anthropic プロバイダー

Anthropic APIを使用したテキスト生成を提供します。

Example:
    >>> provider = AnthropicProvider(
    ...     api_key="sk-ant-...",
    ...     model="claude-3-5-sonnet-20241022",
    ... )
    >>> result = await provider.generate("Hello!")
"""

from typing import Any

from anthropic import (
    APIConnectionError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)

from src.ai.base import (
    AIConnectionError,
    AIProvider,
    AIProviderError,
    AIQuotaExceededError,
    AIResponseError,
)
from src.ai.token_counter import get_token_budget, trim_context


class AnthropicProvider(AIProvider):
    """Anthropic APIを使用したAIプロバイダー

    Messages APIをラップして、抽象化されたインターフェースを提供します。

    Attributes:
        _model: 使用するモデル名
        _client: Anthropic非同期クライアント
    """

    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """AnthropicProviderを初期化

        Args:
            api_key: Anthropic APIキー
            model: 使用するモデル名（例: "claude-3-5-sonnet-20241022"）
            base_url: APIのベースURL（オプション）
        """
        self._model = model
        self._client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def name(self) -> str:
        """プロバイダー名を返す"""
        return "anthropic"

    @property
    def model(self) -> str:
        """使用するモデル名を返す"""
        return self._model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """テキスト生成

        Anthropic Messages APIを使用してテキストを生成します。

        Args:
            prompt: 生成のためのプロンプト
            **kwargs: オプション
                - temperature: 生成の多様性（0.0-1.0）
                - max_tokens: 最大トークン数
                - system_prompt: システムプロンプト

        Returns:
            生成されたテキスト

        Raises:
            AIConnectionError: 接続エラーの場合
            AIQuotaExceededError: レート制限超過の場合
            AIProviderError: その他のAPIエラーの場合
        """
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        system_prompt = kwargs.get("system_prompt")
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=[{"role": "user", "content": prompt}],
            )

            if not message.content or len(message.content) == 0:
                raise AIResponseError("Empty response from Anthropic", provider=self.name)

            # テキストブロックを取得
            text_content = message.content[0]
            if hasattr(text_content, "text"):
                return text_content.text  # type: ignore[union-attr]
            raise AIResponseError("Unexpected response format from Anthropic", provider=self.name)

        except APIConnectionError as e:
            raise AIConnectionError(f"Connection error: {e}", provider=self.name) from e
        except RateLimitError as e:
            raise AIQuotaExceededError(f"Rate limit exceeded: {e}", provider=self.name) from e
        except AuthenticationError as e:
            raise AIProviderError(f"Invalid API key: {e}", provider=self.name) from e
        except Exception as e:
            if isinstance(e, AIConnectionError | AIQuotaExceededError | AIProviderError):
                raise
            raise AIProviderError(f"Unexpected error: {e}", provider=self.name) from e

    async def embed(self, text: str) -> list[float]:
        """テキストをベクトル化

        Note:
            AnthropicはEmbedding APIを提供していません。
            代わりにOpenAIのEmbedding APIを使用してください。

        Raises:
            AIProviderError: Anthropicはembeddingをサポートしていない
        """
        raise AIProviderError(
            "Anthropic does not support embeddings. Use OpenAI for embeddings.",
            provider=self.name,
        )

    async def generate_with_context(
        self, prompt: str, context: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """コンテキスト付きテキスト生成

        Args:
            prompt: 生成のためのプロンプト
            context: 会話履歴のリスト
            **kwargs: オプション

        Returns:
            生成されたテキスト
        """
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        system_prompt = kwargs.get("system_prompt")
        token_budget = kwargs.get("token_budget", get_token_budget())
        trimmed_context = trim_context(
            context,
            token_budget,
            prompt_text=prompt,
            system_prompt=system_prompt or "",
        )

        # メッセージを構築
        messages = []
        for msg in trimmed_context:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages,
            )

            if not message.content or len(message.content) == 0:
                raise AIResponseError("Empty response from Anthropic", provider=self.name)

            text_content = message.content[0]
            if hasattr(text_content, "text"):
                return text_content.text  # type: ignore[union-attr]
            raise AIResponseError("Unexpected response format from Anthropic", provider=self.name)

        except APIConnectionError as e:
            raise AIConnectionError(f"Connection error: {e}", provider=self.name) from e
        except RateLimitError as e:
            raise AIQuotaExceededError(f"Rate limit exceeded: {e}", provider=self.name) from e
        except AuthenticationError as e:
            raise AIProviderError(f"Invalid API key: {e}", provider=self.name) from e
        except Exception as e:
            if isinstance(e, AIConnectionError | AIQuotaExceededError | AIProviderError):
                raise
            raise AIProviderError(f"Unexpected error: {e}", provider=self.name) from e
