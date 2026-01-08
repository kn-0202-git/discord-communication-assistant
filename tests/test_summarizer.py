"""Summarizer サービス テスト

TEST_PLAN.md で定義されたテストケース:
- SUM-01: test_summarize_messages_success - メッセージ要約成功
- SUM-02: test_summarize_empty_messages - 空のメッセージリストで適切な応答
- SUM-03: test_summarize_with_date_filter - 日付フィルタリング
- SUM-04: test_summarize_uses_correct_provider - 正しいプロバイダーを使用
- SUM-05: test_summarize_ai_error_handling - AIエラーハンドリング
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.base import AIProviderError


class TestSummarizer:
    """Summarizerのテスト"""

    @pytest.fixture
    def mock_ai_provider(self) -> MagicMock:
        """AIプロバイダーのモック"""
        provider = MagicMock()
        provider.generate = AsyncMock(
            return_value="""【決定事項】
・製品Xの仕様変更を承認
・納期を1週間延長

【未決事項】
・価格改定について要検討"""
        )
        return provider

    @pytest.fixture
    def mock_router(self, mock_ai_provider: MagicMock) -> MagicMock:
        """AIRouterのモック"""
        router = MagicMock()
        router.get_provider_info.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        router.get_provider_config.return_value = {
            "api_key": "test-key",
        }
        return router

    @pytest.fixture
    def sample_messages(self) -> list[dict[str, Any]]:
        """サンプルメッセージ（UTC aware datetime を使用）"""
        now = datetime.now(UTC)
        return [
            {
                "sender_name": "田中",
                "content": "製品Xの仕様変更について相談があります",
                "timestamp": now - timedelta(hours=2),
            },
            {
                "sender_name": "佐藤",
                "content": "はい、どのような変更ですか？",
                "timestamp": now - timedelta(hours=1),
            },
            {
                "sender_name": "田中",
                "content": "サイズを10%大きくしたいです。それに伴い納期を1週間延長できますか？",
                "timestamp": now - timedelta(minutes=30),
            },
            {
                "sender_name": "佐藤",
                "content": "承知しました。仕様変更と納期延長、承認します。",
                "timestamp": now - timedelta(minutes=10),
            },
        ]

    # SUM-01: メッセージ要約成功
    @pytest.mark.asyncio
    async def test_summarize_messages_success(
        self,
        mock_ai_provider: MagicMock,
        mock_router: MagicMock,
        sample_messages: list[dict[str, Any]],
    ) -> None:
        """メッセージ要約が正常に動作する"""
        from src.ai.summarizer import Summarizer

        summarizer = Summarizer(mock_router)
        with patch.object(summarizer, "_get_provider", return_value=mock_ai_provider):
            result = await summarizer.summarize(sample_messages)

        assert "決定事項" in result
        assert "製品X" in result
        mock_ai_provider.generate.assert_called_once()

    # SUM-02: 空のメッセージリストで適切な応答
    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self, mock_router: MagicMock) -> None:
        """空のメッセージリストで適切なメッセージを返す"""
        from src.ai.summarizer import Summarizer

        summarizer = Summarizer(mock_router)
        result = await summarizer.summarize([])

        assert "メッセージがありません" in result or "要約する" in result.lower()

    # SUM-03: 日付フィルタリング
    @pytest.mark.asyncio
    async def test_filter_messages_by_days(
        self, mock_ai_provider: MagicMock, mock_router: MagicMock
    ) -> None:
        """指定した日数でメッセージをフィルタリングできる"""
        from src.ai.summarizer import Summarizer

        now = datetime.now(UTC)
        messages = [
            {
                "sender_name": "A",
                "content": "古いメッセージ",
                "timestamp": now - timedelta(days=10),
            },
            {
                "sender_name": "B",
                "content": "最近のメッセージ",
                "timestamp": now - timedelta(days=2),
            },
            {
                "sender_name": "C",
                "content": "今日のメッセージ",
                "timestamp": now - timedelta(hours=1),
            },
        ]

        summarizer = Summarizer(mock_router)
        with patch.object(summarizer, "_get_provider", return_value=mock_ai_provider):
            # 7日以内のメッセージのみを要約
            await summarizer.summarize(messages, days=7)

            # generate が呼び出されていることを確認
            mock_ai_provider.generate.assert_called_once()

            # 呼び出し引数のプロンプトを確認
            call_args = mock_ai_provider.generate.call_args
            prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")

            # 古いメッセージは含まれていないはず
            assert "古いメッセージ" not in prompt
            # 新しいメッセージは含まれているはず
            assert "最近のメッセージ" in prompt
            assert "今日のメッセージ" in prompt

    # SUM-04: 正しいプロバイダーを使用
    @pytest.mark.asyncio
    async def test_summarize_uses_correct_provider(
        self, mock_ai_provider: MagicMock, sample_messages: list[dict[str, Any]]
    ) -> None:
        """Workspace/Room設定に基づいた正しいプロバイダーを使用する"""
        from src.ai.summarizer import Summarizer

        mock_router = MagicMock()
        mock_router.get_provider_info.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        mock_router.get_provider_config.return_value = {
            "api_key": "test-key",
        }

        summarizer = Summarizer(mock_router)
        mock_get_provider = MagicMock(return_value=mock_ai_provider)
        with patch.object(summarizer, "_get_provider", mock_get_provider):
            await summarizer.summarize(
                sample_messages,
                workspace_id="workspace_a",
                room_id="room_123",
            )

        # _get_provider が正しい引数で呼ばれたことを確認
        mock_get_provider.assert_called_once_with("workspace_a", "room_123")

    # SUM-05: AIエラーハンドリング
    @pytest.mark.asyncio
    async def test_summarize_ai_error_handling(
        self, mock_router: MagicMock, sample_messages: list[dict[str, Any]]
    ) -> None:
        """AIエラーが適切に処理される"""
        from src.ai.summarizer import Summarizer, SummaryError

        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=AIProviderError("API error"))

        summarizer = Summarizer(mock_router)
        with patch.object(summarizer, "_get_provider", return_value=mock_provider):
            with pytest.raises(SummaryError) as exc_info:
                await summarizer.summarize(sample_messages)

            assert "要約" in str(exc_info.value) or "エラー" in str(exc_info.value)


class TestSummarizerPrompt:
    """Summarizerのプロンプト生成テスト"""

    @pytest.fixture
    def mock_router(self) -> MagicMock:
        """AIRouterのモック"""
        router = MagicMock()
        router.get_provider_info.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        router.get_provider_config.return_value = {"api_key": "test-key"}
        return router

    def test_build_prompt_includes_messages(self, mock_router: MagicMock) -> None:
        """プロンプトにメッセージが含まれる"""
        from src.ai.summarizer import Summarizer

        summarizer = Summarizer(mock_router)
        now = datetime.now(UTC)
        messages = [
            {"sender_name": "田中", "content": "テストメッセージ1", "timestamp": now},
            {"sender_name": "佐藤", "content": "テストメッセージ2", "timestamp": now},
        ]

        prompt = summarizer._build_prompt(messages)

        assert "田中" in prompt
        assert "佐藤" in prompt
        assert "テストメッセージ1" in prompt
        assert "テストメッセージ2" in prompt

    def test_build_prompt_has_summary_instructions(self, mock_router: MagicMock) -> None:
        """プロンプトに要約指示が含まれる"""
        from src.ai.summarizer import Summarizer

        summarizer = Summarizer(mock_router)
        messages = [
            {"sender_name": "A", "content": "Test", "timestamp": datetime.now(UTC)},
        ]

        prompt = summarizer._build_prompt(messages)

        # 要約指示が含まれていることを確認
        assert "要約" in prompt or "summary" in prompt.lower()
