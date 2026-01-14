"""統合テスト

全機能の連携を確認するためのテスト。

TEST_PLAN.md で定義されたテストケース:
- INT-01: test_message_flow - メッセージ保存フロー
- INT-02: test_workspace_room_isolation - Workspace/Room分離
- INT-03: test_ai_router_with_providers - AIルーターとプロバイダー連携
- INT-04: test_summarizer_with_messages - 要約機能の統合テスト
- INT-05: test_notification_flow - 通知フロー
"""

from collections.abc import Generator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from src.db.database import Database


class TestMessageFlow:
    """メッセージ保存フローの統合テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    # INT-01: メッセージ保存フロー
    def test_message_flow(self, db: "Database") -> None:
        """メッセージの保存から検索までの一連のフローを確認"""
        # 1. Workspaceを作成
        workspace = db.create_workspace(
            name="Test Workspace",
            discord_server_id="guild123",
        )
        assert workspace.id is not None

        # 2. Roomを作成
        room = db.create_room(
            workspace_id=workspace.id,
            name="Test Room",
            discord_channel_id="channel123",
            room_type="topic",
        )
        assert room.id is not None

        # 3. メッセージを保存
        message = db.save_message(
            room_id=room.id,
            sender_name="Test User",
            sender_id="user123",
            content="これはテストメッセージです",
            message_type="text",
            discord_message_id="msg123",
        )
        assert message.id is not None

        # 4. メッセージを検索
        results = db.search_messages(
            workspace_id=workspace.id,
            keyword="テスト",
        )
        assert len(results) == 1
        assert results[0].id == message.id

        # 5. Roomからメッセージを取得
        room_messages = db.get_messages_by_room(room.id)
        assert len(room_messages) == 1

    # INT-02: Workspace/Room分離
    def test_workspace_room_isolation(self, db: "Database") -> None:
        """異なるWorkspace間でデータが分離されていることを確認"""
        # Workspace Aを作成
        workspace_a = db.create_workspace(
            name="Workspace A",
            discord_server_id="guild_a",
        )
        room_a = db.create_room(
            workspace_id=workspace_a.id,
            name="Room A",
            discord_channel_id="channel_a",
            room_type="topic",
        )
        db.save_message(
            room_id=room_a.id,
            sender_name="User A",
            sender_id="user_a",
            content="Workspace Aのメッセージ",
            message_type="text",
            discord_message_id="msg_a",
        )

        # Workspace Bを作成
        workspace_b = db.create_workspace(
            name="Workspace B",
            discord_server_id="guild_b",
        )
        room_b = db.create_room(
            workspace_id=workspace_b.id,
            name="Room B",
            discord_channel_id="channel_b",
            room_type="topic",
        )
        db.save_message(
            room_id=room_b.id,
            sender_name="User B",
            sender_id="user_b",
            content="Workspace Bのメッセージ",
            message_type="text",
            discord_message_id="msg_b",
        )

        # Workspace Aからの検索ではAのメッセージのみ
        results_a = db.search_messages(workspace_id=workspace_a.id, keyword="メッセージ")
        assert len(results_a) == 1
        assert "Workspace A" in results_a[0].content

        # Workspace Bからの検索ではBのメッセージのみ
        results_b = db.search_messages(workspace_id=workspace_b.id, keyword="メッセージ")
        assert len(results_b) == 1
        assert "Workspace B" in results_b[0].content

        # Workspace AからWorkspace Bのメッセージは検索できない
        results_cross = db.search_messages(workspace_id=workspace_a.id, keyword="Workspace B")
        assert len(results_cross) == 0


class TestAIIntegration:
    """AI機能の統合テスト"""

    # INT-03: AIルーターとプロバイダー連携
    @pytest.mark.asyncio
    async def test_ai_router_with_providers(self) -> None:
        """AIルーターが正しくプロバイダー情報を返すことを確認"""
        from unittest.mock import patch

        from src.ai.router import AIRouter

        # グローバル設定でOpenAIを使用
        config = {
            "ai_providers": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-4o-mini",
                }
            },
            "ai_routing": {
                "summary": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        }

        router = AIRouter(config)

        # プロバイダー情報を取得
        provider_info = router.get_provider_info("summary")

        # 正しいプロバイダー情報が返される
        assert provider_info is not None
        assert provider_info["provider"] == "openai"
        assert provider_info["model"] == "gpt-4o-mini"

        # プロバイダー設定を取得
        provider_config = router.get_provider_config("openai")
        assert provider_config["api_key"] == "test-key"

        # プロバイダー情報を使って実際にプロバイダーを作成できることを確認
        with patch("src.ai.providers.openai.AsyncOpenAI", autospec=True) as mock_async_openai:
            mock_client = MagicMock()
            mock_async_openai.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                return_value=MagicMock(
                    choices=[MagicMock(message=MagicMock(content="Test response"))]
                )
            )

            from src.ai.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                api_key=provider_config["api_key"],
                model=provider_info["model"],
            )
            result = await provider.generate("Test prompt")
            assert result == "Test response"

    # INT-04: 要約機能の統合テスト
    @pytest.mark.asyncio
    async def test_summarizer_with_messages(self) -> None:
        """要約機能がメッセージを正しく処理することを確認"""
        from datetime import UTC
        from unittest.mock import patch

        from src.ai.summarizer import Summarizer

        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value="これは要約です")

        mock_router = MagicMock()
        mock_router.get_provider.return_value = mock_provider
        mock_router.get_provider_info.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
        }
        mock_router.get_provider_config.return_value = {
            "api_key": "test-key",
        }

        summarizer = Summarizer(mock_router)
        with patch.object(summarizer, "_get_provider", return_value=mock_provider):
            # サンプルメッセージ（UTC aware datetime を使用）
            now = datetime.now(UTC)
            messages = [
                {
                    "sender_name": "User A",
                    "content": "今日の進捗を報告します",
                    "timestamp": now - timedelta(hours=2),
                },
                {
                    "sender_name": "User B",
                    "content": "了解です",
                    "timestamp": now - timedelta(hours=1),
                },
            ]

            result = await summarizer.summarize(messages)

            assert result == "これは要約です"
            mock_provider.generate.assert_called_once()


class TestNotificationFlow:
    """通知機能の統合テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    # INT-05: 通知フロー
    @pytest.mark.asyncio
    async def test_notification_flow(self, db: "Database") -> None:
        """メッセージ受信から通知送信までのフローを確認"""
        import discord

        from src.bot.notifier import AggregationNotifier

        # Workspaceを作成
        workspace = db.create_workspace(
            name="Test Workspace",
            discord_server_id="guild123",
        )

        # 通常Roomを作成
        source_room = db.create_room(
            workspace_id=workspace.id,
            name="Source Room",
            discord_channel_id="123456789",
            room_type="topic",
        )

        # 統合Roomを作成
        aggregation_room = db.create_room(
            workspace_id=workspace.id,
            name="Aggregation Room",
            discord_channel_id="987654321",
            room_type="aggregation",
        )

        # RoomLinkを作成
        db.create_room_link(
            source_room_id=source_room.id,
            target_room_id=aggregation_room.id,
            link_type="one_way",
        )

        # メッセージを保存
        message = db.save_message(
            room_id=source_room.id,
            sender_name="Test User",
            sender_id="user123",
            content="これは通知テストです",
            message_type="text",
            discord_message_id="msg123",
        )

        # Botモック
        mock_bot = MagicMock()
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        # 通知サービス
        notifier = AggregationNotifier(db=db, bot=mock_bot)

        # 通知を送信
        notified = await notifier.notify_new_message(
            room=source_room,
            message=message,
        )

        # 統合Roomに通知が送信された
        assert len(notified) == 1
        assert notified[0] == aggregation_room.id
        mock_channel.send.assert_called_once()


class TestRoomLinkIntegration:
    """RoomLink機能の統合テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    def test_room_link_target_rooms(self, db: "Database") -> None:
        """RoomLinkでリンク先を取得できることを確認"""
        # Workspaceを作成
        workspace = db.create_workspace(
            name="Test Workspace",
            discord_server_id="guild123",
        )

        # 複数のRoomを作成
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="Room 1",
            discord_channel_id="channel1",
            room_type="topic",
        )
        room2 = db.create_room(
            workspace_id=workspace.id,
            name="Room 2",
            discord_channel_id="channel2",
            room_type="topic",
        )
        aggregation = db.create_room(
            workspace_id=workspace.id,
            name="Aggregation",
            discord_channel_id="channel_agg",
            room_type="aggregation",
        )

        # リンクを作成
        db.create_room_link(room1.id, aggregation.id, "one_way")
        db.create_room_link(room2.id, aggregation.id, "one_way")

        # Room1からのリンク先を取得
        targets = db.get_target_rooms(room1.id)
        assert len(targets) == 1
        assert targets[0].id == aggregation.id

        # aggregation roomへのリンク元を取得
        sources = db.get_linked_rooms(aggregation.id)
        assert len(sources) == 2

    def test_get_aggregation_rooms(self, db: "Database") -> None:
        """Workspace内の統合Roomを取得できることを確認"""
        workspace = db.create_workspace(
            name="Test Workspace",
            discord_server_id="guild123",
        )

        # 複数のRoomを作成（統合Roomを含む）
        db.create_room(
            workspace_id=workspace.id,
            name="Room 1",
            discord_channel_id="channel1",
            room_type="topic",
        )
        db.create_room(
            workspace_id=workspace.id,
            name="Aggregation 1",
            discord_channel_id="channel_agg1",
            room_type="aggregation",
        )
        db.create_room(
            workspace_id=workspace.id,
            name="Aggregation 2",
            discord_channel_id="channel_agg2",
            room_type="aggregation",
        )

        # 統合Roomのみを取得
        aggregation_rooms = db.get_aggregation_rooms(workspace.id)
        assert len(aggregation_rooms) == 2
        for room in aggregation_rooms:
            assert room.room_type == "aggregation"
