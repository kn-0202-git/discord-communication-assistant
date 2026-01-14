"""Google AI プロバイダー

Google Generative AI（Gemini）APIを使用したテキスト生成を提供します。

Example:
    >>> provider = GoogleProvider(
    ...     api_key="AIza...",
    ...     model="gemini-1.5-flash",
    ... )
    >>> result = await provider.generate("Hello!")
"""

from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.ai.base import (
    AIConnectionError,
    AIProvider,
    AIProviderError,
    AIQuotaExceededError,
    AIResponseError,
)
from src.ai.token_counter import get_token_budget, trim_context


class GoogleProvider(AIProvider):
    """Google AI (Gemini) APIを使用したAIプロバイダー

    Attributes:
        _model: 使用するモデル名
        _client: GenerativeModelインスタンス
    """

    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        """GoogleProviderを初期化

        Args:
            api_key: Google AI APIキー
            model: 使用するモデル名（例: "gemini-1.5-flash"）
        """
        self._model_name = model
        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        self._client = genai.GenerativeModel(model)  # type: ignore[attr-defined]

    @property
    def name(self) -> str:
        """プロバイダー名を返す"""
        return "google"

    @property
    def model(self) -> str:
        """使用するモデル名を返す"""
        return self._model_name

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """テキスト生成

        Gemini APIを使用してテキストを生成します。

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

        # システムプロンプトがあればプロンプトに含める
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = genai.GenerationConfig(  # type: ignore[attr-defined]
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            response = await self._client.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            )

            if not response.text:
                raise AIResponseError("Empty response from Google AI", provider=self.name)

            return response.text

        except google_exceptions.ServiceUnavailable as e:
            raise AIConnectionError(f"Service unavailable: {e}", provider=self.name) from e
        except google_exceptions.ResourceExhausted as e:
            raise AIQuotaExceededError(f"Rate limit exceeded: {e}", provider=self.name) from e
        except google_exceptions.InvalidArgument as e:
            raise AIProviderError(f"Invalid argument: {e}", provider=self.name) from e
        except google_exceptions.PermissionDenied as e:
            raise AIProviderError(
                f"Permission denied (invalid API key?): {e}", provider=self.name
            ) from e
        except Exception as e:
            if isinstance(e, AIConnectionError | AIQuotaExceededError | AIProviderError):
                raise
            raise AIProviderError(f"Unexpected error: {e}", provider=self.name) from e

    async def embed(self, text: str) -> list[float]:
        """テキストをベクトル化

        Google AI Embedding APIを使用してテキストを埋め込みベクトルに変換します。

        Args:
            text: ベクトル化するテキスト

        Returns:
            埋め込みベクトル

        Raises:
            AIProviderError: ベクトル化に失敗した場合
        """
        try:
            result = genai.embed_content(  # type: ignore[attr-defined]
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document",
            )

            if not result.get("embedding"):
                raise AIResponseError("Empty embedding from Google AI", provider=self.name)

            return result["embedding"]

        except google_exceptions.ServiceUnavailable as e:
            raise AIConnectionError(f"Service unavailable: {e}", provider=self.name) from e
        except google_exceptions.ResourceExhausted as e:
            raise AIQuotaExceededError(f"Rate limit exceeded: {e}", provider=self.name) from e
        except Exception as e:
            if isinstance(e, AIConnectionError | AIQuotaExceededError | AIProviderError):
                raise
            raise AIProviderError(f"Unexpected error: {e}", provider=self.name) from e

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
        trimmed_context = trim_context(context, token_budget, prompt_text=prompt)

        # コンテキストをプロンプトに結合
        context_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in trimmed_context)
        full_prompt = f"{context_text}\n\nuser: {prompt}" if trimmed_context else prompt

        return await self.generate(full_prompt, **kwargs)
