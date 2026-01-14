"""Groq プロバイダー

Groq APIを使用した高速テキスト生成を提供します。

Example:
    >>> provider = GroqProvider(
    ...     api_key="gsk_...",
    ...     model="llama-3.1-70b-versatile",
    ... )
    >>> result = await provider.generate("Hello!")
"""

from typing import Any

from groq import (
    APIConnectionError,
    AsyncGroq,
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


class GroqProvider(AIProvider):
    """Groq APIを使用したAIプロバイダー

    高速なLLM推論を提供します。

    Attributes:
        _model: 使用するモデル名
        _client: Groq非同期クライアント
    """

    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """GroqProviderを初期化

        Args:
            api_key: Groq APIキー
            model: 使用するモデル名（例: "llama-3.1-70b-versatile"）
            base_url: APIのベースURL（オプション）
        """
        self._model = model
        self._client = AsyncGroq(
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def name(self) -> str:
        """プロバイダー名を返す"""
        return "groq"

    @property
    def model(self) -> str:
        """使用するモデル名を返す"""
        return self._model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """テキスト生成

        Groq Chat Completions APIを使用してテキストを生成します。

        Args:
            prompt: 生成のためのプロンプト
            **kwargs: オプション
                - temperature: 生成の多様性（0.0-2.0）
                - max_tokens: 最大トークン数
                - system_prompt: システムプロンプト

        Returns:
            生成されたテキスト

        Raises:
            AIConnectionError: 接続エラーの場合
            AIQuotaExceededError: レート制限超過の場合
            AIProviderError: その他のAPIエラーの場合
        """
        messages = self._build_messages(prompt, kwargs.get("system_prompt"))
        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                raise AIResponseError("Empty response from Groq", provider=self.name)

            return response.choices[0].message.content

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
            GroqはEmbedding APIを提供していません。
            代わりにOpenAIのEmbedding APIを使用してください。

        Raises:
            AIProviderError: Groqはembeddingをサポートしていない
        """
        raise AIProviderError(
            "Groq does not support embeddings. Use OpenAI for embeddings.",
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
        token_budget = kwargs.get("token_budget", get_token_budget())
        system_prompt = kwargs.get("system_prompt")
        trimmed_context = trim_context(
            context,
            token_budget,
            prompt_text=prompt,
            system_prompt=system_prompt or "",
        )

        messages: list[dict[str, str]] = []

        # システムプロンプトがあれば追加
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # コンテキストを追加
        for msg in trimmed_context:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 現在のユーザープロンプトを追加
        messages.append({"role": "user", "content": prompt})

        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                raise AIResponseError("Empty response from Groq", provider=self.name)

            return response.choices[0].message.content

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

    def _build_messages(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict[str, str]]:
        """APIに送信するメッセージリストを構築

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）

        Returns:
            メッセージのリスト
        """
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return messages
