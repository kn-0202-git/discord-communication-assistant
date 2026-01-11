"""OpenAI Whisper プロバイダー

OpenAI Whisper APIを使用した音声文字起こしを提供します。

Example:
    >>> provider = WhisperProvider(
    ...     api_key="sk-...",
    ...     model="whisper-1",
    ... )
    >>> text = await provider.transcribe(audio_bytes, language="ja")
    >>> print(text)
    "こんにちは、お元気ですか？"
"""

import io
from typing import Any

from openai import (
    APIConnectionError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
    AIResponseError,
)
from src.ai.transcription.base import TranscriptionProvider


class WhisperProvider(TranscriptionProvider):
    """OpenAI Whisper APIを使用した文字起こしプロバイダー

    Audio Transcriptions APIをラップして、
    抽象化されたインターフェースを提供します。

    Attributes:
        _model: 使用するモデル名
        _client: OpenAI非同期クライアント

    Example:
        >>> provider = WhisperProvider(
        ...     api_key="sk-...",
        ...     model="whisper-1",
        ... )
        >>> text = await provider.transcribe(audio_bytes)
    """

    DEFAULT_RESPONSE_FORMAT = "text"

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        base_url: str | None = None,
    ) -> None:
        """WhisperProviderを初期化

        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル名（デフォルト: "whisper-1"）
            base_url: APIのベースURL（OpenAI互換APIを使用する場合）
        """
        self._model = model
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

    async def transcribe(
        self,
        audio: bytes,
        language: str | None = None,
        **kwargs: Any,
    ) -> str:
        """音声を文字起こしする

        OpenAI Audio Transcriptions APIを使用して音声を文字起こしします。

        Args:
            audio: 音声データ（WAV, MP3, M4A, WebM等）
            language: 言語コード（例: "ja", "en"）。Noneの場合は自動検出。
            **kwargs: オプション
                - prompt: 文字起こしのヒントとなるプロンプト
                - temperature: 生成の多様性（0.0-1.0）
                - response_format: 出力形式（text, json, srt, vtt）

        Returns:
            文字起こしされたテキスト

        Raises:
            AIConnectionError: 接続エラーの場合
            AIQuotaExceededError: レート制限超過の場合
            AIProviderError: その他のAPIエラーの場合
            AIResponseError: 空の応答の場合
        """
        if not audio:
            raise AIResponseError("Empty audio data provided", provider=self.name)

        response_format = kwargs.get("response_format", self.DEFAULT_RESPONSE_FORMAT)
        prompt = kwargs.get("prompt")
        temperature = kwargs.get("temperature")

        # BytesIOでファイルライクオブジェクトを作成
        audio_file = io.BytesIO(audio)
        audio_file.name = "audio.wav"

        try:
            # APIパラメータを構築
            api_params: dict[str, Any] = {
                "model": self._model,
                "file": audio_file,
                "response_format": response_format,
            }

            if language is not None:
                api_params["language"] = language

            if prompt is not None:
                api_params["prompt"] = prompt

            if temperature is not None:
                api_params["temperature"] = temperature

            response = await self._client.audio.transcriptions.create(**api_params)

            # response_format=textの場合、responseは文字列
            # response_format=jsonの場合、responseはオブジェクト
            if response_format == "text":
                if not response:
                    raise AIResponseError(
                        "Empty transcription response from OpenAI", provider=self.name
                    )
                return str(response)
            else:
                # json, srt, vtt形式の場合
                if hasattr(response, "text"):
                    return str(response.text)
                return str(response)

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
