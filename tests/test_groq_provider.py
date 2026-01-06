"""Groq プロバイダー テスト

TEST_PLAN.md で定義されたテストケース:
- GRQ-01: test_generate_success - テキスト生成成功
- GRQ-02: test_embed_not_supported - 埋め込みはサポートされていない
- GRQ-03: test_generate_with_options - オプション付き生成
- GRQ-04: test_connection_error - 接続エラー処理
- GRQ-05: test_quota_exceeded - レート制限エラー処理
- GRQ-06: test_invalid_api_key - 無効なAPIキーエラー
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
)


class TestGroqProvider:
    """Groqプロバイダーのテスト"""

    @pytest.fixture
    def mock_groq_client(self) -> MagicMock:
        """Groqクライアントのモック"""
        client = MagicMock()
        return client

    @pytest.fixture
    def provider(self, mock_groq_client: MagicMock) -> Any:
        """GroqProviderインスタンス"""
        from src.ai.providers.groq import GroqProvider

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            return GroqProvider(
                api_key="test-api-key",
                model="llama-3.1-70b-versatile",
            )

    # GRQ-01: テキスト生成成功
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_groq_client: MagicMock) -> None:
        """テキスト生成が正常に動作する"""
        from src.ai.providers.groq import GroqProvider

        # モックの設定
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated text response"))]
        mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")
            result = await provider.generate("Hello, how are you?")

        assert result == "Generated text response"
        mock_groq_client.chat.completions.create.assert_called_once()

    # GRQ-02: 埋め込みはサポートされていない
    @pytest.mark.asyncio
    async def test_embed_not_supported(self, mock_groq_client: MagicMock) -> None:
        """埋め込みがサポートされていないことを確認"""
        from src.ai.providers.groq import GroqProvider

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.embed("Test text")

            assert "embeddings" in str(exc_info.value).lower()

    # GRQ-03: オプション付き生成
    @pytest.mark.asyncio
    async def test_generate_with_options(self, mock_groq_client: MagicMock) -> None:
        """温度やmax_tokensなどのオプション付きで生成できる"""
        from src.ai.providers.groq import GroqProvider

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Creative response"))]
        mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")
            result = await provider.generate(
                "Write a poem",
                temperature=0.9,
                max_tokens=500,
                system_prompt="You are a creative poet.",
            )

        assert result == "Creative response"

        # 呼び出し引数を確認
        call_args = mock_groq_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.9
        assert call_args.kwargs["max_tokens"] == 500

    # GRQ-04: 接続エラー処理
    @pytest.mark.asyncio
    async def test_connection_error(self, mock_groq_client: MagicMock) -> None:
        """接続エラーが適切に処理される"""
        from groq import APIConnectionError

        from src.ai.providers.groq import GroqProvider

        mock_groq_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.generate("Test prompt")

            assert "groq" in str(exc_info.value).lower()

    # GRQ-05: レート制限エラー処理
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, mock_groq_client: MagicMock) -> None:
        """レート制限エラーが適切に処理される"""
        from groq import RateLimitError

        from src.ai.providers.groq import GroqProvider

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_groq_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}},
            )
        )

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")

            with pytest.raises(AIQuotaExceededError) as exc_info:
                await provider.generate("Test prompt")

            assert "rate limit" in str(exc_info.value).lower()

    # GRQ-06: 無効なAPIキーエラー
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_groq_client: MagicMock) -> None:
        """無効なAPIキーでエラーが発生する"""
        from groq import AuthenticationError

        from src.ai.providers.groq import GroqProvider

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_groq_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}},
            )
        )

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_groq_client):
            provider = GroqProvider(api_key="invalid-key", model="llama-3.1-70b-versatile")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate("Test prompt")

            assert "invalid" in str(exc_info.value).lower() or "auth" in str(exc_info.value).lower()


class TestGroqProviderProperties:
    """Groqプロバイダーのプロパティテスト"""

    def test_name_property(self) -> None:
        """プロバイダー名が正しく返される"""
        from src.ai.providers.groq import GroqProvider

        with patch("src.ai.providers.groq.AsyncGroq"):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")

        assert provider.name == "groq"

    def test_model_property(self) -> None:
        """モデル名が正しく返される"""
        from src.ai.providers.groq import GroqProvider

        with patch("src.ai.providers.groq.AsyncGroq"):
            provider = GroqProvider(api_key="test-key", model="mixtral-8x7b-32768")

        assert provider.model == "mixtral-8x7b-32768"


class TestGroqProviderContextGeneration:
    """コンテキスト付きテキスト生成のテスト"""

    @pytest.mark.asyncio
    async def test_generate_with_context(self) -> None:
        """コンテキスト付きで生成できる"""
        from src.ai.providers.groq import GroqProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Context-aware response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.groq.AsyncGroq", return_value=mock_client):
            provider = GroqProvider(api_key="test-key", model="llama-3.1-70b-versatile")

            context = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
            result = await provider.generate_with_context("How are you?", context)

        assert result == "Context-aware response"

        # messagesにコンテキストが含まれていることを確認
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) >= 3  # context + user prompt
