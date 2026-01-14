"""Whisper プロバイダー テスト

TEST_PLAN.md で定義されたテストケース:
- WHP-01: test_transcribe_success - 正常な文字起こし
- WHP-02: test_transcribe_with_language - 言語指定付き
- WHP-03: test_connection_error - 接続エラー処理
- WHP-04: test_quota_exceeded - レート制限エラー
- WHP-05: test_invalid_api_key - 認証エラー
- WHP-06: test_empty_audio - 空の音声データ
- WHP-07: test_name_property - プロバイダー名
- WHP-08: test_model_property - モデル名
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
    AIResponseError,
)


class TestWhisperProvider:
    """WhisperProviderのテスト"""

    @pytest.fixture
    def mock_openai_client(self) -> MagicMock:
        """OpenAIクライアントのモック"""
        client = MagicMock()
        return client

    @pytest.fixture
    def provider(self, mock_openai_client: MagicMock) -> Any:
        """WhisperProviderインスタンス"""
        from src.ai.transcription.whisper import WhisperProvider

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            return WhisperProvider(
                api_key="test-api-key",
                model="whisper-1",
            )

    # WHP-01: 正常な文字起こし
    @pytest.mark.asyncio
    async def test_transcribe_success(self, mock_openai_client: MagicMock) -> None:
        """文字起こしが正常に動作する"""
        from src.ai.transcription.whisper import WhisperProvider

        # モックの設定（response_format=textの場合、文字列が返る）
        mock_openai_client.audio.transcriptions.create = AsyncMock(
            return_value="これはテストの文字起こしです。"
        )

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")
            audio_data = b"fake audio data"
            result = await provider.transcribe(audio_data)

        assert result == "これはテストの文字起こしです。"
        mock_openai_client.audio.transcriptions.create.assert_called_once()

    # WHP-02: 言語指定付き
    @pytest.mark.asyncio
    async def test_transcribe_with_language(self, mock_openai_client: MagicMock) -> None:
        """言語指定付きで文字起こしできる"""
        from src.ai.transcription.whisper import WhisperProvider

        mock_openai_client.audio.transcriptions.create = AsyncMock(
            return_value="Hello, this is a test."
        )

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")
            audio_data = b"fake audio data"
            result = await provider.transcribe(audio_data, language="en")

        assert result == "Hello, this is a test."

        # 呼び出し引数を確認
        call_args = mock_openai_client.audio.transcriptions.create.call_args
        assert call_args.kwargs["language"] == "en"

    # WHP-03: 接続エラー処理
    @pytest.mark.asyncio
    async def test_connection_error(self, mock_openai_client: MagicMock) -> None:
        """接続エラーが適切に処理される"""
        from openai import APIConnectionError

        from src.ai.transcription.whisper import WhisperProvider

        mock_openai_client.audio.transcriptions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.transcribe(b"fake audio data")

            assert "openai" in str(exc_info.value).lower()

    # WHP-04: レート制限エラー
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, mock_openai_client: MagicMock) -> None:
        """レート制限エラーが適切に処理される"""
        from openai import RateLimitError

        from src.ai.transcription.whisper import WhisperProvider

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_openai_client.audio.transcriptions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}},
            )
        )

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

            with pytest.raises(AIQuotaExceededError) as exc_info:
                await provider.transcribe(b"fake audio data")

            assert "rate limit" in str(exc_info.value).lower()

    # WHP-05: 認証エラー
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_openai_client: MagicMock) -> None:
        """無効なAPIキーでエラーが発生する"""
        from openai import AuthenticationError

        from src.ai.transcription.whisper import WhisperProvider

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_openai_client.audio.transcriptions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}},
            )
        )

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="invalid-key", model="whisper-1")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.transcribe(b"fake audio data")

            assert "invalid" in str(exc_info.value).lower() or "auth" in str(exc_info.value).lower()

    # WHP-06: 空の音声データ
    @pytest.mark.asyncio
    async def test_empty_audio(self, mock_openai_client: MagicMock) -> None:
        """空の音声データでエラーが発生する"""
        from src.ai.transcription.whisper import WhisperProvider

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
            return_value=mock_openai_client,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

            with pytest.raises(AIResponseError) as exc_info:
                await provider.transcribe(b"")

            assert "empty" in str(exc_info.value).lower()


class TestWhisperProviderProperties:
    """WhisperProviderのプロパティテスト"""

    # WHP-07: プロバイダー名
    def test_name_property(self) -> None:
        """プロバイダー名が正しく返される"""
        from src.ai.transcription.whisper import WhisperProvider

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

        assert provider.name == "openai"

    # WHP-08: モデル名
    def test_model_property(self) -> None:
        """モデル名が正しく返される"""
        from src.ai.transcription.whisper import WhisperProvider

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

        assert provider.model == "whisper-1"

    def test_repr(self) -> None:
        """__repr__が正しく動作する"""
        from src.ai.transcription.whisper import WhisperProvider

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI",
            autospec=True,
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")

        repr_str = repr(provider)
        assert "WhisperProvider" in repr_str
        assert "openai" in repr_str
        assert "whisper-1" in repr_str


class TestWhisperProviderOptions:
    """WhisperProviderのオプションテスト"""

    @pytest.mark.asyncio
    async def test_transcribe_with_options(self) -> None:
        """各種オプション付きで文字起こしできる"""
        from src.ai.transcription.whisper import WhisperProvider

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create = AsyncMock(return_value="Transcribed with options")

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI", autospec=True, return_value=mock_client
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")
            result = await provider.transcribe(
                b"fake audio data",
                language="ja",
                prompt="会議の議事録",
                temperature=0.5,
            )

        assert result == "Transcribed with options"

        # 呼び出し引数を確認
        call_args = mock_client.audio.transcriptions.create.call_args
        assert call_args.kwargs["language"] == "ja"
        assert call_args.kwargs["prompt"] == "会議の議事録"
        assert call_args.kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_transcribe_json_format(self) -> None:
        """JSON形式で文字起こしできる"""
        from src.ai.transcription.whisper import WhisperProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Transcribed text from JSON"
        mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        with patch(
            "src.ai.transcription.whisper.AsyncOpenAI", autospec=True, return_value=mock_client
        ):
            provider = WhisperProvider(api_key="test-key", model="whisper-1")
            result = await provider.transcribe(
                b"fake audio data",
                response_format="json",
            )

        assert result == "Transcribed text from JSON"

        # 呼び出し引数を確認
        call_args = mock_client.audio.transcriptions.create.call_args
        assert call_args.kwargs["response_format"] == "json"
