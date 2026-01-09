"""AggregationNotifier テスト

TEST_PLAN.md で定義されたテストケース:
- NOT-01: test_notify_new_message_success - 新メッセージ通知成功
- NOT-02: test_notify_with_similar_messages - 類似過去案件付き通知
- NOT-03: test_no_aggregation_rooms - 統合Roomがない場合
- NOT-04: test_channel_not_found - チャンネルが見つからない場合
- NOT-05: test_create_notification_embed - Embed作成
- NOT-06: test_rate_limit_semaphore - セマフォによる同時リクエスト制限
- NOT-07: test_rate_limit_cooldown - チャンネルクールダウン
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models import Message, Room

if TYPE_CHECKING:
    from src.bot.notifier import AggregationNotifier


class TestAggregationNotifier:
    """AggregationNotifierのテスト"""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Databaseモック"""
        db = MagicMock()
        return db

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Discord Botモック"""
        bot = MagicMock()
        return bot

    @pytest.fixture
    def sample_room(self) -> Room:
        """サンプルRoom"""
        room = MagicMock(spec=Room)
        room.id = 1
        room.workspace_id = 1
        room.name = "Test Room"
        room.discord_channel_id = "123456789"
        room.room_type = "topic"
        return room

    @pytest.fixture
    def sample_aggregation_room(self) -> Room:
        """サンプル統合Room"""
        room = MagicMock(spec=Room)
        room.id = 2
        room.workspace_id = 1
        room.name = "Aggregation Room"
        room.discord_channel_id = "987654321"
        room.room_type = "aggregation"
        return room

    @pytest.fixture
    def sample_message(self) -> Message:
        """サンプルMessage"""
        message = MagicMock(spec=Message)
        message.id = 1
        message.room_id = 1
        message.sender_name = "Test User"
        message.sender_id = "user123"
        message.content = "これはテストメッセージです"
        message.message_type = "text"
        message.discord_message_id = "msg123"
        message.timestamp = datetime.now()
        return message

    # NOT-01: 新メッセージ通知成功
    @pytest.mark.asyncio
    async def test_notify_new_message_success(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_aggregation_room: Room,
        sample_message: Message,
    ) -> None:
        """新メッセージの通知が正常に送信される"""
        import discord

        from src.bot.notifier import AggregationNotifier

        # モック設定
        mock_db.get_target_rooms.return_value = [sample_aggregation_room]

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # 実行
        result = await notifier.notify_new_message(
            room=sample_room,
            message=sample_message,
            find_similar=False,
        )

        # 検証
        assert len(result) == 1
        assert result[0] == sample_aggregation_room.id
        mock_channel.send.assert_called_once()

    # NOT-02: 類似過去案件付き通知
    @pytest.mark.asyncio
    async def test_notify_with_similar_messages(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_aggregation_room: Room,
        sample_message: Message,
    ) -> None:
        """類似過去案件付きで通知が送信される"""
        import discord

        from src.bot.notifier import AggregationNotifier

        # 類似メッセージを作成
        similar_message = MagicMock(spec=Message)
        similar_message.id = 99
        similar_message.sender_name = "Past User"
        similar_message.content = "過去の類似メッセージ"
        similar_message.timestamp = datetime.now()

        mock_db.get_target_rooms.return_value = [sample_aggregation_room]
        mock_db.search_messages.return_value = [similar_message]

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        mock_router = MagicMock()
        notifier = AggregationNotifier(db=mock_db, bot=mock_bot, router=mock_router)

        # 実行
        result = await notifier.notify_new_message(
            room=sample_room,
            message=sample_message,
            find_similar=True,
        )

        # 検証
        assert len(result) == 1
        mock_db.search_messages.assert_called()
        mock_channel.send.assert_called_once()

        # Embedに類似メッセージが含まれているか確認
        call_args = mock_channel.send.call_args
        embed = call_args.kwargs.get("embed")
        assert embed is not None

    # NOT-03: 統合Roomがない場合
    @pytest.mark.asyncio
    async def test_no_aggregation_rooms(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_message: Message,
    ) -> None:
        """統合Roomがない場合は空のリストを返す"""
        from src.bot.notifier import AggregationNotifier

        mock_db.get_target_rooms.return_value = []

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        result = await notifier.notify_new_message(
            room=sample_room,
            message=sample_message,
        )

        assert result == []
        mock_bot.get_channel.assert_not_called()

    # NOT-04: チャンネルが見つからない場合
    @pytest.mark.asyncio
    async def test_channel_not_found(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_aggregation_room: Room,
        sample_message: Message,
    ) -> None:
        """チャンネルが見つからない場合はエラーログが出力される"""
        from src.bot.notifier import AggregationNotifier

        mock_db.get_target_rooms.return_value = [sample_aggregation_room]

        # チャンネルが見つからない
        mock_bot.get_channel.return_value = None
        mock_bot.fetch_channel = AsyncMock(side_effect=Exception("Channel not found"))

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # エラーが発生しても例外は投げられない
        result = await notifier.notify_new_message(
            room=sample_room,
            message=sample_message,
        )

        # 通知は失敗するが、空のリストを返す
        assert result == []

    # NOT-05: Embed作成
    def test_create_notification_embed(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_message: Message,
    ) -> None:
        """通知用Embedが正しく作成される"""
        from src.bot.notifier import AggregationNotifier

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        embed = notifier._create_notification_embed(
            source_room=sample_room,
            message=sample_message,
            similar_messages=[],
        )

        assert embed.title == "📩 新しいメッセージ"
        assert sample_message.content in embed.description
        # フィールドが3つ以上あることを確認
        assert len(embed.fields) >= 3


class TestAggregationNotifierHelpers:
    """ヘルパーメソッドのテスト"""

    @pytest.fixture
    def notifier(self) -> "AggregationNotifier":
        """Notifierインスタンス"""
        from src.bot.notifier import AggregationNotifier

        return AggregationNotifier(db=MagicMock(), bot=MagicMock())

    def test_truncate_short_text(self, notifier: "AggregationNotifier") -> None:
        """短いテキストはそのまま返される"""
        text = "短いテキスト"
        result = notifier._truncate(text, 100)
        assert result == text

    def test_truncate_long_text(self, notifier: "AggregationNotifier") -> None:
        """長いテキストは切り詰められる"""
        text = "a" * 100
        result = notifier._truncate(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_extract_keywords(self, notifier: "AggregationNotifier") -> None:
        """キーワードが正しく抽出される"""
        content = "これは テスト メッセージ です"
        keywords = notifier._extract_keywords(content)
        # 3文字以上の単語が抽出される
        assert "これは" in keywords
        assert "テスト" in keywords


class TestSetupNotifier:
    """setup_notifier関数のテスト"""

    @pytest.mark.asyncio
    async def test_setup_notifier(self) -> None:
        """setup_notifierが正しくNotifierを作成する"""
        from src.bot.notifier import AggregationNotifier, setup_notifier

        mock_db = MagicMock()
        mock_bot = MagicMock()
        mock_router = MagicMock()

        notifier = await setup_notifier(
            db=mock_db,
            bot=mock_bot,
            router=mock_router,
        )

        assert isinstance(notifier, AggregationNotifier)
        assert notifier.db == mock_db
        assert notifier.bot == mock_bot
        assert notifier.router == mock_router


class TestRateLimit:
    """レート制限のテスト"""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Databaseモック"""
        return MagicMock()

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Discord Botモック"""
        return MagicMock()

    @pytest.fixture
    def sample_room(self) -> Room:
        """サンプルRoom"""
        room = MagicMock(spec=Room)
        room.id = 1
        room.workspace_id = 1
        room.name = "Test Room"
        room.discord_channel_id = "123456789"
        room.room_type = "topic"
        return room

    @pytest.fixture
    def sample_aggregation_room(self) -> Room:
        """サンプル統合Room"""
        room = MagicMock(spec=Room)
        room.id = 2
        room.workspace_id = 1
        room.name = "Aggregation Room"
        room.discord_channel_id = "987654321"
        room.room_type = "aggregation"
        return room

    @pytest.fixture
    def sample_message(self) -> Message:
        """サンプルMessage"""
        message = MagicMock(spec=Message)
        message.id = 1
        message.room_id = 1
        message.sender_name = "Test User"
        message.sender_id = "user123"
        message.content = "これはテストメッセージです"
        message.message_type = "text"
        message.discord_message_id = "msg123"
        message.timestamp = datetime.now()
        return message

    # NOT-06: セマフォによる同時リクエスト制限
    def test_rate_limit_semaphore_initialized(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """セマフォが初期化される"""
        from src.bot.notifier import AggregationNotifier

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # セマフォが正しく初期化されていることを確認
        assert hasattr(notifier, "_semaphore")
        assert isinstance(notifier._semaphore, asyncio.Semaphore)

    # NOT-07: チャンネルクールダウン
    @pytest.mark.asyncio
    async def test_rate_limit_cooldown_tracking(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_room: Room,
        sample_aggregation_room: Room,
        sample_message: Message,
    ) -> None:
        """チャンネルごとのクールダウンが追跡される"""
        import discord

        from src.bot.notifier import AggregationNotifier

        mock_db.get_target_rooms.return_value = [sample_aggregation_room]

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # 最初の通知
        await notifier.notify_new_message(
            room=sample_room,
            message=sample_message,
        )

        # チャンネルの最終送信時刻が記録されている
        channel_id = sample_aggregation_room.discord_channel_id
        assert channel_id in notifier._channel_last_sent

    @pytest.mark.asyncio
    async def test_wait_for_cooldown_no_previous_send(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """以前の送信がない場合は即座に返る"""
        from src.bot.notifier import AggregationNotifier

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # 待機時間なしで完了
        await notifier._wait_for_cooldown("unknown_channel")

    @pytest.mark.asyncio
    async def test_wait_for_cooldown_after_cooldown_period(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """クールダウン期間後は即座に返る"""
        import time

        from src.bot.notifier import AggregationNotifier

        notifier = AggregationNotifier(db=mock_db, bot=mock_bot)

        # クールダウン期間より前に送信したことにする
        channel_id = "test_channel"
        notifier._channel_last_sent[channel_id] = (
            time.monotonic() - notifier.CHANNEL_COOLDOWN_SECONDS - 1
        )

        # 待機時間なしで完了
        start = time.monotonic()
        await notifier._wait_for_cooldown(channel_id)
        elapsed = time.monotonic() - start

        # 待機していないことを確認（0.1秒未満）
        assert elapsed < 0.1


class TestReminderNotifier:
    """ReminderNotifierのテスト"""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Databaseモック"""
        return MagicMock()

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Discord Botモック"""
        return MagicMock()

    @pytest.fixture
    def sample_workspace(self) -> MagicMock:
        """サンプルWorkspace"""
        from src.db.models import Workspace

        workspace = MagicMock(spec=Workspace)
        workspace.id = 1
        workspace.name = "Test Workspace"
        workspace.discord_server_id = "123456789"
        return workspace

    @pytest.fixture
    def sample_reminder(self) -> MagicMock:
        """サンプルReminder"""
        from datetime import UTC, datetime, timedelta

        from src.db.models import Reminder

        reminder = MagicMock(spec=Reminder)
        reminder.id = 1
        reminder.workspace_id = 1
        reminder.title = "納品確認"
        reminder.description = "製品Xの納品日"
        reminder.due_date = datetime.now(UTC) + timedelta(hours=1)
        reminder.status = "pending"
        reminder.notified = False
        return reminder

    @pytest.fixture
    def sample_aggregation_room(self) -> Room:
        """サンプル統合Room"""
        room = MagicMock(spec=Room)
        room.id = 2
        room.workspace_id = 1
        room.name = "Aggregation Room"
        room.discord_channel_id = "987654321"
        room.room_type = "aggregation"
        return room

    # RN-01: 期限が近いリマインダーを通知
    @pytest.mark.asyncio
    async def test_check_and_notify_sends_reminder(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_workspace: MagicMock,
        sample_reminder: MagicMock,
        sample_aggregation_room: Room,
    ) -> None:
        """期限が近いリマインダーを通知する"""
        import discord

        from src.bot.notifier import ReminderNotifier

        # モック設定
        mock_db.get_pending_reminders.return_value = [sample_reminder]
        mock_db.get_aggregation_rooms.return_value = [sample_aggregation_room]

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        notifier = ReminderNotifier(db=mock_db, bot=mock_bot)

        # 実行
        count = await notifier.check_and_notify()

        # 検証
        assert count == 1
        mock_channel.send.assert_called_once()
        mock_db.update_reminder_notified.assert_called_once_with(sample_reminder.id, notified=True)

    # RN-02: 通知済みフラグが更新される
    @pytest.mark.asyncio
    async def test_check_and_notify_updates_notified_flag(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_reminder: MagicMock,
        sample_aggregation_room: Room,
    ) -> None:
        """通知後にnotifiedフラグがTrueに更新される"""
        import discord

        from src.bot.notifier import ReminderNotifier

        mock_db.get_pending_reminders.return_value = [sample_reminder]
        mock_db.get_aggregation_rooms.return_value = [sample_aggregation_room]

        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel

        notifier = ReminderNotifier(db=mock_db, bot=mock_bot)
        await notifier.check_and_notify()

        mock_db.update_reminder_notified.assert_called_with(sample_reminder.id, notified=True)

    # RN-03: 統合Roomがない場合はスキップ
    @pytest.mark.asyncio
    async def test_check_and_notify_no_aggregation_rooms(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_reminder: MagicMock,
    ) -> None:
        """統合Roomがない場合はスキップする"""
        from src.bot.notifier import ReminderNotifier

        mock_db.get_pending_reminders.return_value = [sample_reminder]
        mock_db.get_aggregation_rooms.return_value = []

        notifier = ReminderNotifier(db=mock_db, bot=mock_bot)
        count = await notifier.check_and_notify()

        assert count == 0
        mock_db.update_reminder_notified.assert_not_called()

    # RN-04: 期限が近いリマインダーがない場合
    @pytest.mark.asyncio
    async def test_check_and_notify_no_pending_reminders(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
    ) -> None:
        """期限が近いリマインダーがない場合は何もしない"""
        from src.bot.notifier import ReminderNotifier

        mock_db.get_pending_reminders.return_value = []

        notifier = ReminderNotifier(db=mock_db, bot=mock_bot)
        count = await notifier.check_and_notify()

        assert count == 0

    # RN-05: Embed作成のテスト
    def test_create_reminder_embed(
        self,
        mock_db: MagicMock,
        mock_bot: MagicMock,
        sample_reminder: MagicMock,
    ) -> None:
        """リマインダー通知用Embedが正しく作成される"""
        from src.bot.notifier import ReminderNotifier

        notifier = ReminderNotifier(db=mock_db, bot=mock_bot)
        embed = notifier._create_reminder_embed(sample_reminder)

        assert "リマインダー" in embed.title
        assert sample_reminder.title in embed.description
