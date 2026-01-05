"""Google AI プロバイダー テスト

TEST_PLAN.md で定義されたテストケース:
- GOO-01: test_generate_success - テキスト生成成功
- GOO-02: test_embed_success - 埋め込み生成成功
- GOO-03: test_generate_with_options - オプション付き生成
- GOO-04: test_connection_error - 接続エラー処理
- GOO-05: test_quota_exceeded - レート制限エラー処理
- GOO-06: test_invalid_api_key - 無効なAPIキーエラー
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
)


class TestGoogleProvider:
    """Googleプロバイダーのテスト"""

    @pytest.fixture
    def mock_genai(self) -> MagicMock:
        """Google genaiモジュールのモック"""
        mock = MagicMock()
        mock.GenerativeModel.return_value = MagicMock()
        mock.GenerationConfig.return_value = MagicMock()
        return mock

    @pytest.fixture
    def provider(self, mock_genai: MagicMock) -> Any:
        """GoogleProviderインスタンス"""
        from src.ai.providers.google import GoogleProvider

        with patch("src.ai.providers.google.genai", mock_genai):
            return GoogleProvider(
                api_key="test-api-key",
                model="gemini-1.5-flash",
            )

    # GOO-01: テキスト生成成功
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_genai: MagicMock) -> None:
        """テキスト生成が正常に動作する"""
        from src.ai.providers.google import GoogleProvider

        # モックの設定
        mock_response = MagicMock()
        mock_response.text = "Generated text response"
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")
            result = await provider.generate("Hello, how are you?")

        assert result == "Generated text response"
        mock_model.generate_content_async.assert_called_once()

    # GOO-02: 埋め込み生成成功
    @pytest.mark.asyncio
    async def test_embed_success(self, mock_genai: MagicMock) -> None:
        """埋め込みベクトル生成が正常に動作する"""
        from src.ai.providers.google import GoogleProvider

        # 768次元のダミーベクトル
        expected_embedding = [0.1] * 768
        mock_genai.embed_content.return_value = {"embedding": expected_embedding}

        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")
            result = await provider.embed("Test text")

        assert result == expected_embedding
        assert len(result) == 768

    # GOO-03: オプション付き生成
    @pytest.mark.asyncio
    async def test_generate_with_options(self, mock_genai: MagicMock) -> None:
        """温度やmax_tokensなどのオプション付きで生成できる"""
        from src.ai.providers.google import GoogleProvider

        mock_response = MagicMock()
        mock_response.text = "Creative response"
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")
            result = await provider.generate(
                "Write a poem",
                temperature=0.9,
                max_tokens=500,
                system_prompt="You are a creative poet.",
            )

        assert result == "Creative response"

        # GenerationConfigが呼び出されていることを確認
        mock_genai.GenerationConfig.assert_called()

    # GOO-04: 接続エラー処理
    @pytest.mark.asyncio
    async def test_connection_error(self, mock_genai: MagicMock) -> None:
        """接続エラーが適切に処理される"""
        from google.api_core import exceptions as google_exceptions

        from src.ai.providers.google import GoogleProvider

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=google_exceptions.ServiceUnavailable("Service unavailable")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.generate("Test prompt")

            assert "google" in str(exc_info.value).lower()

    # GOO-05: レート制限エラー処理
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, mock_genai: MagicMock) -> None:
        """レート制限エラーが適切に処理される"""
        from google.api_core import exceptions as google_exceptions

        from src.ai.providers.google import GoogleProvider

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=google_exceptions.ResourceExhausted("Rate limit exceeded")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")

            with pytest.raises(AIQuotaExceededError) as exc_info:
                await provider.generate("Test prompt")

            assert "rate limit" in str(exc_info.value).lower()

    # GOO-06: 無効なAPIキーエラー
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_genai: MagicMock) -> None:
        """無効なAPIキーでエラーが発生する"""
        from google.api_core import exceptions as google_exceptions

        from src.ai.providers.google import GoogleProvider

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=google_exceptions.PermissionDenied("Permission denied")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="invalid-key", model="gemini-1.5-flash")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate("Test prompt")

            assert "permission" in str(exc_info.value).lower()


class TestGoogleProviderProperties:
    """Googleプロバイダーのプロパティテスト"""

    def test_name_property(self) -> None:
        """プロバイダー名が正しく返される"""
        from src.ai.providers.google import GoogleProvider

        with patch("src.ai.providers.google.genai"):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")

        assert provider.name == "google"

    def test_model_property(self) -> None:
        """モデル名が正しく返される"""
        from src.ai.providers.google import GoogleProvider

        with patch("src.ai.providers.google.genai"):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-pro")

        assert provider.model == "gemini-1.5-pro"


class TestGoogleProviderContextGeneration:
    """コンテキスト付きテキスト生成のテスト"""

    @pytest.mark.asyncio
    async def test_generate_with_context(self) -> None:
        """コンテキスト付きで生成できる"""
        from src.ai.providers.google import GoogleProvider

        mock_genai = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Context-aware response"
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("src.ai.providers.google.genai", mock_genai):
            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")

            context = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
            result = await provider.generate_with_context("How are you?", context)

        assert result == "Context-aware response"
