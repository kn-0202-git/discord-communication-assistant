"""OpenAI プロバイダー

OpenAI APIを使用したテキスト生成・埋め込み生成を提供します。

Example:
    >>> provider = OpenAIProvider(
    ...     api_key="sk-...",
    ...     model="gpt-4o-mini",
    ...     embedding_model="text-embedding-3-small",
    ... )
    >>> result = await provider.generate("Hello, how are you?")
    >>> print(result)
    "I'm doing well, thank you for asking!"

    >>> embedding = await provider.embed("Test text")
    >>> print(len(embedding))
    1536
"""

from typing import Any

from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessageParam

from src.ai.base import (
    AIConnectionError,
    AIProvider,
    AIProviderError,
    AIQuotaExceededError,
    AIResponseError,
)


class OpenAIProvider(AIProvider):
    """OpenAI APIを使用したAIプロバイダー

    Chat Completions APIとEmbeddings APIをラップして、
    抽象化されたインターフェースを提供します。

    Attributes:
        _model: 生成に使用するモデル名
        _embedding_model: 埋め込みに使用するモデル名
        _client: OpenAI非同期クライアント

    Example:
        >>> provider = OpenAIProvider(
        ...     api_key="sk-...",
        ...     model="gpt-4o-mini",
        ... )
        >>> text = await provider.generate("Summarize this text: ...")
    """

    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        api_key: str,
        model: str,
        embedding_model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """OpenAIProviderを初期化

        Args:
            api_key: OpenAI APIキー
            model: 生成に使用するモデル名（例: "gpt-4o-mini", "gpt-4o"）
            embedding_model: 埋め込みに使用するモデル名（デフォルト: "text-embedding-3-small"）
            base_url: APIのベースURL（OpenAI互換APIを使用する場合）
        """
        self._model = model
        self._embedding_model = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    @property
    def name(self) -> str:
        """プロバイダー名を返す"""
        return "openai"

    @property
    def model(self) -> str:
        """使用するモデル名を返す"""
        return self._model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """テキスト生成

        OpenAI Chat Completions APIを使用してテキストを生成します。

        Args:
            prompt: 生成のためのプロンプト
            **kwargs: オプション
                - temperature: 生成の多様性（0.0-2.0、デフォルト: 0.7）
                - max_tokens: 最大トークン数（デフォルト: 1024）
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
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                raise AIResponseError("Empty response from OpenAI", provider=self.name)

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

        OpenAI Embeddings APIを使用してテキストを埋め込みベクトルに変換します。

        Args:
            text: ベクトル化するテキスト

        Returns:
            埋め込みベクトル（通常1536次元のfloatリスト）

        Raises:
            AIConnectionError: 接続エラーの場合
            AIQuotaExceededError: レート制限超過の場合
            AIProviderError: その他のAPIエラーの場合
        """
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=text,
            )

            if not response.data or not response.data[0].embedding:
                raise AIResponseError("Empty embedding response from OpenAI", provider=self.name)

            return response.data[0].embedding

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

    async def generate_with_context(
        self, prompt: str, context: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """コンテキスト付きテキスト生成

        会話履歴などのコンテキストを含めて生成を行います。
        OpenAIのnativeなmessages形式を使用するため、基底クラスの実装をオーバーライドします。

        Args:
            prompt: 生成のためのプロンプト
            context: 会話履歴のリスト。各要素は {"role": "user"|"assistant", "content": str}
            **kwargs: オプション（generateと同じ）

        Returns:
            生成されたテキスト
        """
        messages: list[ChatCompletionMessageParam] = []

        # システムプロンプトがあれば追加
        if "system_prompt" in kwargs:
            messages.append({"role": "system", "content": kwargs["system_prompt"]})

        # コンテキストを追加（contextの各要素をChatCompletionMessageParamとして追加）
        for msg in context:
            messages.append({"role": msg["role"], "content": msg["content"]})  # type: ignore[typeddict-item]

        # 現在のユーザープロンプトを追加
        messages.append({"role": "user", "content": prompt})

        temperature = kwargs.get("temperature", self.DEFAULT_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", self.DEFAULT_MAX_TOKENS)

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                raise AIResponseError("Empty response from OpenAI", provider=self.name)

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
    ) -> list[ChatCompletionMessageParam]:
        """APIに送信するメッセージリストを構築

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）

        Returns:
            メッセージのリスト
        """
        messages: list[ChatCompletionMessageParam] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return messages
