"""Aggregation Room Notifier.

統合Roomへの通知機能を提供します。

Example:
    >>> notifier = AggregationNotifier(db=db, bot=bot, router=router)
    >>> await notifier.notify_new_message(room_id=1, message=message)
"""

import asyncio
import contextlib
import logging
import time
from datetime import datetime

import discord

from src.ai.router import AIRouter
from src.db.database import Database
from src.db.models import Message, Reminder, Room

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """通知エラー"""

    pass


class AggregationNotifier:
    """統合Roomへの通知を管理するクラス.

    新しいメッセージが投稿された際に、リンクされた統合Roomへ通知を送信します。
    オプションで類似過去案件の検索も行います。
    レート制限対策として、同時リクエスト数の制限とクールダウンを実装しています。

    Attributes:
        db: Databaseインスタンス
        bot: Discord Botインスタンス
        router: AIRouterインスタンス（類似検索に使用）
    """

    # 類似検索で取得する最大メッセージ数
    MAX_SIMILAR_MESSAGES = 3

    # レート制限設定
    MAX_CONCURRENT_REQUESTS = 5  # 同時リクエスト数の上限
    CHANNEL_COOLDOWN_SECONDS = 1.0  # チャンネルごとのクールダウン（秒）

    def __init__(
        self,
        db: Database,
        bot: discord.Client,
        router: AIRouter | None = None,
    ) -> None:
        """AggregationNotifierを初期化.

        Args:
            db: Databaseインスタンス
            bot: Discord Botインスタンス
            router: AIRouterインスタンス（類似検索に使用、オプション）
        """
        self.db = db
        self.bot = bot
        self.router = router

        # レート制限用のセマフォ（同時リクエスト数を制限）
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        # チャンネルごとの最終送信時刻
        self._channel_last_sent: dict[str, float] = {}

    async def notify_new_message(
        self,
        room: Room,
        message: Message,
        find_similar: bool = False,
    ) -> list[int]:
        """新しいメッセージを統合Roomに通知.

        Args:
            room: メッセージが投稿されたRoom
            message: 保存されたMessageオブジェクト
            find_similar: 類似過去案件を検索するかどうか

        Returns:
            通知を送信したRoom IDのリスト
        """
        notified_rooms: list[int] = []

        # リンクされた統合Roomを取得
        target_rooms = self.db.get_target_rooms(room.id)
        aggregation_rooms = [r for r in target_rooms if r.room_type == "aggregation"]

        if not aggregation_rooms:
            logger.debug(f"No aggregation rooms linked to room {room.id}")
            return notified_rooms

        # 類似メッセージを検索（オプション）
        similar_messages: list[Message] = []
        if find_similar and self.router:
            similar_messages = await self._find_similar_messages(
                workspace_id=room.workspace_id,
                content=message.content,
                exclude_message_id=message.id,
            )

        # 各統合Roomに通知
        for agg_room in aggregation_rooms:
            try:
                await self._send_notification(
                    aggregation_room=agg_room,
                    source_room=room,
                    message=message,
                    similar_messages=similar_messages,
                )
                notified_rooms.append(agg_room.id)
                logger.info(f"Notified aggregation room {agg_room.id}")
            except Exception as e:
                logger.error(f"Failed to notify aggregation room {agg_room.id}: {e}")

        return notified_rooms

    async def _send_notification(
        self,
        aggregation_room: Room,
        source_room: Room,
        message: Message,
        similar_messages: list[Message],
    ) -> None:
        """統合Roomに通知を送信.

        レート制限対策:
        - セマフォで同時リクエスト数を制限
        - チャンネルごとにクールダウンを適用

        Args:
            aggregation_room: 通知先の統合Room
            source_room: メッセージの送信元Room
            message: 新しいメッセージ
            similar_messages: 類似過去案件のリスト
        """
        channel_id = aggregation_room.discord_channel_id

        # セマフォで同時リクエスト数を制限
        async with self._semaphore:
            # チャンネルごとのクールダウンを確認
            await self._wait_for_cooldown(channel_id)

            # Discordチャンネルを取得
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(channel_id))

            if not isinstance(channel, discord.TextChannel):
                raise NotificationError(f"Channel {channel_id} is not a text channel")

            # Embedを作成
            embed = self._create_notification_embed(
                source_room=source_room,
                message=message,
                similar_messages=similar_messages,
            )

            await channel.send(embed=embed)

            # 最終送信時刻を更新
            self._channel_last_sent[channel_id] = time.monotonic()

    async def _wait_for_cooldown(self, channel_id: str) -> None:
        """チャンネルのクールダウンを待機.

        Args:
            channel_id: Discord チャンネルID
        """
        if channel_id in self._channel_last_sent:
            elapsed = time.monotonic() - self._channel_last_sent[channel_id]
            remaining = self.CHANNEL_COOLDOWN_SECONDS - elapsed
            if remaining > 0:
                logger.debug(f"Rate limit: waiting {remaining:.2f}s for channel {channel_id}")
                await asyncio.sleep(remaining)

    def _create_notification_embed(
        self,
        source_room: Room,
        message: Message,
        similar_messages: list[Message],
    ) -> discord.Embed:
        """通知用のEmbedを作成.

        Args:
            source_room: メッセージの送信元Room
            message: 新しいメッセージ
            similar_messages: 類似過去案件のリスト

        Returns:
            Discord Embed
        """
        embed = discord.Embed(
            title="📩 新しいメッセージ",
            description=self._truncate(message.content, 500),
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        embed.add_field(
            name="送信者",
            value=message.sender_name,
            inline=True,
        )
        embed.add_field(
            name="送信元Room",
            value=source_room.name,
            inline=True,
        )
        embed.add_field(
            name="メッセージタイプ",
            value=message.message_type,
            inline=True,
        )

        # 類似過去案件があれば追加
        if similar_messages:
            similar_text = self._format_similar_messages(similar_messages)
            embed.add_field(
                name="📚 類似過去案件",
                value=similar_text,
                inline=False,
            )

        embed.set_footer(text=f"Message ID: {message.discord_message_id}")

        return embed

    def _format_similar_messages(self, messages: list[Message]) -> str:
        """類似メッセージをフォーマット.

        Args:
            messages: 類似メッセージのリスト

        Returns:
            フォーマットされた文字列
        """
        lines = []
        for i, msg in enumerate(messages, 1):
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            content = self._truncate(msg.content, 100)
            lines.append(f"{i}. [{timestamp}] {msg.sender_name}: {content}")
        return "\n".join(lines)

    def _truncate(self, text: str, max_length: int) -> str:
        """テキストを指定長で切り詰め.

        Args:
            text: 元のテキスト
            max_length: 最大長

        Returns:
            切り詰められたテキスト
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    async def _find_similar_messages(
        self,
        workspace_id: int,
        content: str,
        exclude_message_id: int,
    ) -> list[Message]:
        """類似メッセージを検索.

        簡易実装：キーワードベースの検索を行う。
        将来的にはベクトル検索に置き換え可能。

        Args:
            workspace_id: Workspace ID
            content: 検索するコンテンツ
            exclude_message_id: 除外するメッセージID

        Returns:
            類似メッセージのリスト
        """
        # 簡易実装：コンテンツから重要なキーワードを抽出
        keywords = self._extract_keywords(content)
        if not keywords:
            return []

        # 各キーワードで検索
        results: list[Message] = []
        for keyword in keywords[:3]:  # 最大3キーワード
            messages = self.db.search_messages(
                workspace_id=workspace_id,
                keyword=keyword,
                limit=self.MAX_SIMILAR_MESSAGES * 2,
            )
            for msg in messages:
                if msg.id != exclude_message_id and msg not in results:
                    results.append(msg)

        return results[: self.MAX_SIMILAR_MESSAGES]

    def _extract_keywords(self, content: str) -> list[str]:
        """コンテンツからキーワードを抽出.

        簡易実装：長い単語を抽出。
        将来的にはAIによるキーワード抽出に置き換え可能。

        Args:
            content: 検索するコンテンツ

        Returns:
            キーワードのリスト
        """
        # 簡易的なキーワード抽出
        # スペースで分割し、3文字以上の単語を抽出
        words = content.split()
        keywords = [w for w in words if len(w) >= 3]
        return keywords[:5]  # 最大5キーワード


class ReminderNotifier:
    """リマインダー通知を管理するクラス.

    期限が近いリマインダーを統合Roomに自動通知します。

    Attributes:
        db: Databaseインスタンス
        bot: Discord Botインスタンス
        check_interval: チェック間隔（秒）
    """

    # デフォルトのチェック間隔（5分）
    DEFAULT_CHECK_INTERVAL = 300

    # 期限通知の先読み時間（24時間）
    DEFAULT_HOURS_AHEAD = 24

    def __init__(
        self,
        db: Database,
        bot: discord.Client,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        hours_ahead: int = DEFAULT_HOURS_AHEAD,
    ) -> None:
        """ReminderNotifierを初期化.

        Args:
            db: Databaseインスタンス
            bot: Discord Botインスタンス
            check_interval: チェック間隔（秒）
            hours_ahead: 期限通知の先読み時間（時間）
        """
        self.db = db
        self.bot = bot
        self.check_interval = check_interval
        self.hours_ahead = hours_ahead
        self._task: asyncio.Task | None = None

    async def check_and_notify(self) -> int:
        """期限が近いリマインダーをチェックして通知.

        Returns:
            通知したリマインダーの数
        """
        notified_count = 0

        # 期限が近いリマインダーを取得
        pending_reminders = self.db.get_pending_reminders(hours_ahead=self.hours_ahead)

        if not pending_reminders:
            logger.debug("No pending reminders to notify")
            return notified_count

        for reminder in pending_reminders:
            try:
                # Workspace内の統合Roomを取得
                aggregation_rooms = self.db.get_aggregation_rooms(reminder.workspace_id)

                if not aggregation_rooms:
                    logger.debug(f"No aggregation rooms for workspace {reminder.workspace_id}")
                    continue

                # 各統合Roomに通知
                for agg_room in aggregation_rooms:
                    await self._send_reminder_notification(agg_room, reminder)

                # 通知済みフラグを更新
                self.db.update_reminder_notified(reminder.id, notified=True)
                notified_count += 1
                logger.info(f"Sent reminder notification for reminder {reminder.id}")

            except Exception as e:
                logger.error(f"Failed to notify reminder {reminder.id}: {e}")

        return notified_count

    async def _send_reminder_notification(
        self,
        aggregation_room: Room,
        reminder: Reminder,
    ) -> None:
        """リマインダー通知を送信.

        Args:
            aggregation_room: 通知先の統合Room
            reminder: 通知するリマインダー
        """
        channel_id = aggregation_room.discord_channel_id

        # Discordチャンネルを取得
        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            channel = await self.bot.fetch_channel(int(channel_id))

        if not isinstance(channel, discord.TextChannel):
            raise NotificationError(f"Channel {channel_id} is not a text channel")

        # Embedを作成
        embed = self._create_reminder_embed(reminder)

        await channel.send(embed=embed)

    def _create_reminder_embed(self, reminder: Reminder) -> discord.Embed:
        """リマインダー通知用Embedを作成.

        Args:
            reminder: 通知するリマインダー

        Returns:
            Discord Embed
        """
        embed = discord.Embed(
            title="⏰ リマインダー通知",
            description=f"**{reminder.title}**",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )

        due_str = reminder.due_date.strftime("%Y-%m-%d %H:%M")
        embed.add_field(name="期限", value=due_str, inline=True)
        embed.add_field(name="ステータス", value=reminder.status, inline=True)

        if reminder.description:
            embed.add_field(name="詳細", value=reminder.description, inline=False)

        embed.set_footer(text=f"リマインダーID: {reminder.id}")

        return embed

    async def start(self) -> None:
        """バックグラウンドタスクを開始."""
        if self._task is not None:
            logger.warning("ReminderNotifier is already running")
            return

        self._task = asyncio.create_task(self._background_loop())
        logger.info("ReminderNotifier started")

    async def stop(self) -> None:
        """バックグラウンドタスクを停止."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
            logger.info("ReminderNotifier stopped")

    async def _background_loop(self) -> None:
        """バックグラウンドループ."""
        while True:
            try:
                await self.check_and_notify()
            except Exception as e:
                logger.error(f"Error in reminder notification loop: {e}")

            await asyncio.sleep(self.check_interval)


async def setup_notifier(
    db: Database,
    bot: discord.Client,
    router: AIRouter | None = None,
) -> AggregationNotifier:
    """AggregationNotifierをセットアップ.

    Args:
        db: Databaseインスタンス
        bot: Discord Botインスタンス
        router: AIRouterインスタンス（オプション）

    Returns:
        セットアップされたAggregationNotifier
    """
    return AggregationNotifier(db=db, bot=bot, router=router)


async def setup_reminder_notifier(
    db: Database,
    bot: discord.Client,
    check_interval: int = ReminderNotifier.DEFAULT_CHECK_INTERVAL,
    hours_ahead: int = ReminderNotifier.DEFAULT_HOURS_AHEAD,
) -> ReminderNotifier:
    """ReminderNotifierをセットアップ.

    Args:
        db: Databaseインスタンス
        bot: Discord Botインスタンス
        check_interval: チェック間隔（秒）
        hours_ahead: 期限通知の先読み時間（時間）

    Returns:
        セットアップされたReminderNotifier
    """
    return ReminderNotifier(
        db=db,
        bot=bot,
        check_interval=check_interval,
        hours_ahead=hours_ahead,
    )
