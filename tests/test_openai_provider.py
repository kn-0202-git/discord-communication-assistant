"""OpenAI プロバイダー テスト

TEST_PLAN.md で定義されたテストケース:
- OAI-01: test_generate_success - テキスト生成成功
- OAI-02: test_embed_success - 埋め込み生成成功
- OAI-03: test_generate_with_options - オプション付き生成
- OAI-04: test_connection_error - 接続エラー処理
- OAI-05: test_quota_exceeded - レート制限エラー処理
- OAI-06: test_invalid_api_key - 無効なAPIキーエラー
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import (
    AIConnectionError,
    AIProviderError,
    AIQuotaExceededError,
)


class TestOpenAIProvider:
    """OpenAIプロバイダーのテスト"""

    @pytest.fixture
    def mock_openai_client(self) -> MagicMock:
        """OpenAIクライアントのモック"""
        client = MagicMock()
        return client

    @pytest.fixture
    def provider(self, mock_openai_client: MagicMock) -> Any:
        """OpenAIProviderインスタンス"""
        from src.ai.providers.openai import OpenAIProvider

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            return OpenAIProvider(
                api_key="test-api-key",
                model="gpt-4o-mini",
            )

    # OAI-01: テキスト生成成功
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openai_client: MagicMock) -> None:
        """テキスト生成が正常に動作する"""
        from src.ai.providers.openai import OpenAIProvider

        # モックの設定
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated text response"))]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
            result = await provider.generate("Hello, how are you?")

        assert result == "Generated text response"
        mock_openai_client.chat.completions.create.assert_called_once()

    # OAI-02: 埋め込み生成成功
    @pytest.mark.asyncio
    async def test_embed_success(self, mock_openai_client: MagicMock) -> None:
        """埋め込みベクトル生成が正常に動作する"""
        from src.ai.providers.openai import OpenAIProvider

        # 1536次元のダミーベクトル
        expected_embedding = [0.1] * 1536

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=expected_embedding)]
        mock_openai_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(
                api_key="test-key",
                model="gpt-4o-mini",
                embedding_model="text-embedding-3-small",
            )
            result = await provider.embed("Test text")

        assert result == expected_embedding
        assert len(result) == 1536

    # OAI-03: オプション付き生成
    @pytest.mark.asyncio
    async def test_generate_with_options(self, mock_openai_client: MagicMock) -> None:
        """温度やmax_tokensなどのオプション付きで生成できる"""
        from src.ai.providers.openai import OpenAIProvider

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Creative response"))]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
            result = await provider.generate(
                "Write a poem",
                temperature=0.9,
                max_tokens=500,
                system_prompt="You are a creative poet.",
            )

        assert result == "Creative response"

        # 呼び出し引数を確認
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.9
        assert call_args.kwargs["max_tokens"] == 500

    # OAI-04: 接続エラー処理
    @pytest.mark.asyncio
    async def test_connection_error(self, mock_openai_client: MagicMock) -> None:
        """接続エラーが適切に処理される"""
        from openai import APIConnectionError

        from src.ai.providers.openai import OpenAIProvider

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

            with pytest.raises(AIConnectionError) as exc_info:
                await provider.generate("Test prompt")

            assert "openai" in str(exc_info.value).lower()

    # OAI-05: レート制限エラー処理
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, mock_openai_client: MagicMock) -> None:
        """レート制限エラーが適切に処理される"""
        from openai import RateLimitError

        from src.ai.providers.openai import OpenAIProvider

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=mock_response,
                body={"error": {"message": "Rate limit exceeded"}},
            )
        )

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

            with pytest.raises(AIQuotaExceededError) as exc_info:
                await provider.generate("Test prompt")

            assert "rate limit" in str(exc_info.value).lower()

    # OAI-06: 無効なAPIキーエラー
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, mock_openai_client: MagicMock) -> None:
        """無効なAPIキーでエラーが発生する"""
        from openai import AuthenticationError

        from src.ai.providers.openai import OpenAIProvider

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=mock_response,
                body={"error": {"message": "Invalid API key"}},
            )
        )

        with patch(
            "src.ai.providers.openai.AsyncOpenAI", autospec=True, return_value=mock_openai_client
        ):
            provider = OpenAIProvider(api_key="invalid-key", model="gpt-4o-mini")

            with pytest.raises(AIProviderError) as exc_info:
                await provider.generate("Test prompt")

            assert "invalid" in str(exc_info.value).lower() or "auth" in str(exc_info.value).lower()


class TestOpenAIProviderProperties:
    """OpenAIプロバイダーのプロパティテスト"""

    def test_name_property(self) -> None:
        """プロバイダー名が正しく返される"""
        from src.ai.providers.openai import OpenAIProvider

        with patch(
            "src.ai.providers.openai.AsyncOpenAI",
            autospec=True,
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        assert provider.name == "openai"

    def test_model_property(self) -> None:
        """モデル名が正しく返される"""
        from src.ai.providers.openai import OpenAIProvider

        with patch(
            "src.ai.providers.openai.AsyncOpenAI",
            autospec=True,
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o")

        assert provider.model == "gpt-4o"

    def test_repr(self) -> None:
        """__repr__が正しく動作する"""
        from src.ai.providers.openai import OpenAIProvider

        with patch(
            "src.ai.providers.openai.AsyncOpenAI",
            autospec=True,
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        repr_str = repr(provider)
        assert "OpenAIProvider" in repr_str
        assert "openai" in repr_str
        assert "gpt-4o-mini" in repr_str


class TestOpenAIProviderContextGeneration:
    """コンテキスト付きテキスト生成のテスト"""

    @pytest.mark.asyncio
    async def test_generate_with_context(self) -> None:
        """コンテキスト付きで生成できる"""
        from src.ai.providers.openai import OpenAIProvider

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Context-aware response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch(
            "src.ai.providers.openai.AsyncOpenAI",
            autospec=True,
            return_value=mock_client,
        ):
            provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

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
