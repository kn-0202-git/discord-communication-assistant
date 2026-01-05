"""AIプロバイダーの抽象基底クラスとエラー定義

このモジュールは、複数のAIプロバイダー（OpenAI, Anthropic, Google, Groq, Local）を
統一的に扱うための抽象化レイヤーを提供します。

Example:
    >>> class OpenAIProvider(AIProvider):
    ...     async def generate(self, prompt: str, **kwargs) -> str:
    ...         # OpenAI APIを呼び出す実装
    ...         pass
    ...
    ...     async def embed(self, text: str) -> list[float]:
    ...         # Embedding APIを呼び出す実装
    ...         pass
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """AIプロバイダーの基底エラークラス

    すべてのAI関連エラーはこのクラスを継承します。

    Attributes:
        message: エラーメッセージ
        provider: エラーが発生したプロバイダー名（オプション）
    """

    def __init__(self, message: str, provider: str | None = None) -> None:
        self.message = message
        self.provider = provider
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.provider:
            return f"[{self.provider}] {self.message}"
        return self.message


class AIProviderNotConfiguredError(AIProviderError):
    """プロバイダーが設定されていない場合のエラー

    指定されたpurposeまたはプロバイダーが設定ファイルに存在しない場合に発生します。

    Example:
        >>> raise AIProviderNotConfiguredError("summary", provider="groq")
        AIProviderNotConfiguredError: [groq] Provider not configured for purpose: summary
    """

    def __init__(self, purpose: str, provider: str | None = None) -> None:
        self.purpose = purpose
        message = f"Provider not configured for purpose: {purpose}"
        super().__init__(message, provider)


class AIQuotaExceededError(AIProviderError):
    """API制限超過エラー

    レート制限やトークン制限を超過した場合に発生します。

    Attributes:
        retry_after: 再試行までの待機時間（秒）。不明な場合はNone。
    """

    def __init__(
        self, message: str, provider: str | None = None, retry_after: float | None = None
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider)


class AIConnectionError(AIProviderError):
    """API接続エラー

    ネットワークエラーやタイムアウトなど、接続に関する問題が発生した場合に発生します。
    """

    pass


class AIResponseError(AIProviderError):
    """API応答エラー

    APIからの応答が不正または予期しない形式の場合に発生します。
    """

    pass


class AIProvider(ABC):
    """AIプロバイダーの抽象基底クラス

    すべてのAIプロバイダー（OpenAI, Anthropic, Google, Groq, Local）は
    このクラスを継承して実装します。

    Attributes:
        name: プロバイダー名（例: "openai", "anthropic"）
        model: 使用するモデル名（例: "gpt-4o-mini"）

    Example:
        >>> class OpenAIProvider(AIProvider):
        ...     def __init__(self, api_key: str, model: str):
        ...         self._api_key = api_key
        ...         self._model = model
        ...
        ...     @property
        ...     def name(self) -> str:
        ...         return "openai"
        ...
        ...     @property
        ...     def model(self) -> str:
        ...         return self._model
        ...
        ...     async def generate(self, prompt: str, **kwargs) -> str:
        ...         # 実装
        ...         pass
        ...
        ...     async def embed(self, text: str) -> list[float]:
        ...         # 実装
        ...         pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """プロバイダー名を返す

        Returns:
            プロバイダー名（例: "openai", "anthropic", "google", "groq", "local"）
        """
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """使用するモデル名を返す

        Returns:
            モデル名（例: "gpt-4o-mini", "claude-3-5-sonnet-20241022"）
        """
        pass

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """テキスト生成

        プロンプトを受け取り、AIが生成したテキストを返します。

        Args:
            prompt: 生成のためのプロンプト
            **kwargs: プロバイダー固有のオプション
                - temperature: 生成の多様性（0.0-2.0）
                - max_tokens: 最大トークン数
                - system_prompt: システムプロンプト

        Returns:
            生成されたテキスト

        Raises:
            AIProviderError: 生成に失敗した場合
            AIQuotaExceededError: API制限を超過した場合
            AIConnectionError: 接続に失敗した場合
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """テキストをベクトル化

        テキストを埋め込みベクトル（embedding）に変換します。
        類似検索やRAGで使用されます。

        Args:
            text: ベクトル化するテキスト

        Returns:
            埋め込みベクトル（通常1536次元のfloatリスト）

        Raises:
            AIProviderError: ベクトル化に失敗した場合
            AIQuotaExceededError: API制限を超過した場合
            AIConnectionError: 接続に失敗した場合
        """
        pass

    async def generate_with_context(
        self, prompt: str, context: list[dict[str, str]], **kwargs: Any
    ) -> str:
        """コンテキスト付きテキスト生成

        会話履歴などのコンテキストを含めて生成を行います。
        デフォルト実装では、コンテキストをプロンプトに結合して generate() を呼び出します。

        Args:
            prompt: 生成のためのプロンプト
            context: 会話履歴のリスト。各要素は {"role": "user"|"assistant", "content": str}
            **kwargs: プロバイダー固有のオプション

        Returns:
            生成されたテキスト
        """
        # デフォルト実装: コンテキストをプロンプトに結合
        context_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in context)
        full_prompt = f"{context_text}\n\nuser: {prompt}" if context else prompt
        return await self.generate(full_prompt, **kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r})"
