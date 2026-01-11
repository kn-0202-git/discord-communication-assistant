"""音声文字起こしプロバイダーの抽象基底クラス

このモジュールは、複数の文字起こしプロバイダー（OpenAI Whisper, Groq Whisperなど）を
統一的に扱うための抽象化レイヤーを提供します。

既存のAIProviderとは異なり、入力が音声バイナリであるため独立した基底クラスとして定義。

Example:
    >>> class WhisperProvider(TranscriptionProvider):
    ...     async def transcribe(self, audio: bytes, **kwargs) -> str:
    ...         # Whisper APIを呼び出す実装
    ...         pass
"""

from abc import ABC, abstractmethod
from typing import Any


class TranscriptionProvider(ABC):
    """音声文字起こしプロバイダーの抽象基底クラス

    すべての文字起こしプロバイダー（OpenAI Whisper, Groq Whisperなど）は
    このクラスを継承して実装します。

    Attributes:
        name: プロバイダー名（例: "openai", "groq"）
        model: 使用するモデル名（例: "whisper-1"）

    Example:
        >>> class WhisperProvider(TranscriptionProvider):
        ...     def __init__(self, api_key: str, model: str = "whisper-1"):
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
        ...     async def transcribe(self, audio: bytes, **kwargs) -> str:
        ...         # 実装
        ...         pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """プロバイダー名を返す

        Returns:
            プロバイダー名（例: "openai", "groq"）
        """
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """使用するモデル名を返す

        Returns:
            モデル名（例: "whisper-1"）
        """
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        """音声を文字起こしする

        音声バイナリデータを受け取り、文字起こしされたテキストを返します。

        Args:
            audio: 音声データ（WAV, MP3, M4A, WebM等）
            language: 言語コード（例: "ja", "en"）。Noneの場合は自動検出。
            **kwargs: プロバイダー固有のオプション
                - prompt: 文字起こしのヒントとなるプロンプト
                - temperature: 生成の多様性（0.0-1.0）
                - response_format: 出力形式（text, json, srt, vtt）

        Returns:
            文字起こしされたテキスト

        Raises:
            AIProviderError: 文字起こしに失敗した場合
            AIQuotaExceededError: API制限を超過した場合
            AIConnectionError: 接続に失敗した場合
            AIResponseError: 不正な応答の場合
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.model!r})"
