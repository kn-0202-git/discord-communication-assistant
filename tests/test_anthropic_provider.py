"""Anthropic プロバイダー テスト

TEST_PLAN.md で定義されたテストケース:
- ANT-01: test_generate_success - テキスト生成成功
- ANT-02: test_embed_not_supported - 埋め込みはサポートされていない
- ANT-03: test_generate_with_options - オプション付き生成
- ANT-04: test_connection_error - 接続エラー処理
- ANT-05: test_quota_exceeded - レート制限エラー処理
- ANT-06: test_invalid_api_key - 無効なAPIキーエラー
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
)


class TestAnthropicProvider:
    """Anthropicプロバイダーのテスト"""

    @pytest.fixture
    def mock_anthropic_client(self) -> MagicMock:
        """Anthropicクライアントのモック"""
        client = MagicMock()
        return client

    @pytest.fixture
    def provider(self, mock_anthropic_client: MagicMock) -> Any:
        """AnthropicProviderインスタンス"""
        from src.ai.providers.anthropic import AnthropicProvider

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            return AnthropicProvider(
                api_key="test-api-key",
                model="claude-3-5-sonnet-20241022",
            )

    # ANT-01: テキスト生成成功
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_anthropic_client: MagicMock) -> None:
        """テキスト生成が正常に動作する"""
        from src.ai.providers.anthropic import AnthropicProvider

        # モックの設定
        mock_text_block = MagicMock()
        mock_text_block.text = "Generated text response"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")
            result = await provider.generate("Hello, how are you?")

        assert result == "Generated text response"
        mock_anthropic_client.messages.create.assert_called_once()

    # ANT-02: 埋め込みはサポートされていない
    @pytest.mark.asyncio
    async def test_embed_not_supported(self, mock_anthropic_client: MagicMock) -> None:
        """埋め込みがサポートされていないことを確認"""
        from src.ai.providers.anthropic import AnthropicProvider

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.embed("Test text")

            assert "embeddings" in str(exc_info.value).lower()

    # ANT-03: オプション付き生成
    @pytest.mark.asyncio
    async def test_generate_with_options(self, mock_anthropic_client: MagicMock) -> None:
        """温度やmax_tokensなどのオプション付きで生成できる"""
        from src.ai.providers.anthropic import AnthropicProvider

        mock_text_block = MagicMock()
        mock_text_block.text = "Creative response"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")
            result = await provider.generate(
                "Write a poem",
                temperature=0.9,
                max_tokens=500,
                system_prompt="You are a creative poet.",
            )

        assert result == "Creative response"

        # 呼び出し引数を確認
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0.9
        assert call_args.kwargs["max_tokens"] == 500
        assert call_args.kwargs["system"] == "You are a creative poet."

    # ANT-04: 接続エラー処理
    @pytest.mark.asyncio
    async def test_connection_error(self, mock_anthropic_client: MagicMock) -> None:
        """接続エラーが適切に処理される"""
        from anthropic import APIConnectionError

        from src.ai.providers.anthropic import AnthropicProvider

        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.generate("Test prompt")

            assert "anthropic" in str(exc_info.value).lower()

    # ANT-05: レート制限エラー処理
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, mock_anthropic_client: MagicMock) -> None:
        """レート制限エラーが適切に処理される"""
        from anthropic import RateLimitError

        from src.ai.providers.anthropic import AnthropicProvider

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}},
            )
        )

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

            with pytest.raises(AIQuotaExceededError) as exc_info:
                await provider.generate("Test prompt")

            assert "rate limit" in str(exc_info.value).lower()

    # ANT-06: 無効なAPIキーエラー
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_anthropic_client: MagicMock) -> None:
        """無効なAPIキーでエラーが発生する"""
        from anthropic import AuthenticationError

        from src.ai.providers.anthropic import AnthropicProvider

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_anthropic_client.messages.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}},
            )
        )

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_anthropic_client):
            provider = AnthropicProvider(api_key="invalid-key", model="claude-3-5-sonnet-20241022")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate("Test prompt")

            assert "invalid" in str(exc_info.value).lower() or "auth" in str(exc_info.value).lower()


class TestAnthropicProviderProperties:
    """Anthropicプロバイダーのプロパティテスト"""

    def test_name_property(self) -> None:
        """プロバイダー名が正しく返される"""
        from src.ai.providers.anthropic import AnthropicProvider

        with patch("src.ai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

        assert provider.name == "anthropic"

    def test_model_property(self) -> None:
        """モデル名が正しく返される"""
        from src.ai.providers.anthropic import AnthropicProvider

        with patch("src.ai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-opus-20240229")

        assert provider.model == "claude-3-opus-20240229"


class TestAnthropicProviderContextGeneration:
    """コンテキスト付きテキスト生成のテスト"""

    @pytest.mark.asyncio
    async def test_generate_with_context(self) -> None:
        """コンテキスト付きで生成できる"""
        from src.ai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_text_block = MagicMock()
        mock_text_block.text = "Context-aware response"
        mock_response = MagicMock()
        mock_response.content = [mock_text_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("src.ai.providers.anthropic.AsyncAnthropic", return_value=mock_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-5-sonnet-20241022")

            context = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
            result = await provider.generate_with_context("How are you?", context)

        assert result == "Context-aware response"

        # messagesにコンテキストが含まれていることを確認
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) >= 3  # context + user prompt
