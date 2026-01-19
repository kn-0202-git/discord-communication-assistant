"""Bot初期化モジュール.

Bot起動時の初期化処理をクラスにまとめ、テスト可能な構造を提供する。
"""

import logging

import discord

from src.bot.client import BotClient
from src.bot.commands import setup_commands
from src.bot.handlers import MessageHandler
from src.bot.listeners import MessageListener
from src.bot.notifier import AggregationNotifier
from src.bot.voice_recorder import VoiceRecorder
from src.factory import AppComponents

logger = logging.getLogger(__name__)


class BotInitializer:
    """Bot初期化を管理するクラス.

    AppComponentsを受け取り、Bot起動に必要なコンポーネントを初期化する。

    Example:
        components = create_app_components()
        initializer = BotInitializer(components)
        client = initializer.setup()
        client.run(token)
    """

    def __init__(self, components: AppComponents) -> None:
        """初期化する.

        Args:
            components: アプリケーションコンポーネント
        """
        self.components = components
        self._client: BotClient | None = None
        self._handler: MessageHandler | None = None
        self._listener: MessageListener | None = None
        self._notifier: AggregationNotifier | None = None
        self._voice_recorder: VoiceRecorder | None = None

    @property
    def client(self) -> BotClient:
        """Botクライアントを取得する.

        Raises:
            RuntimeError: setup()が呼ばれていない場合
        """
        if self._client is None:
            raise RuntimeError("Bot not initialized. Call setup() first.")
        return self._client

    @property
    def handler(self) -> MessageHandler:
        """メッセージハンドラーを取得する.

        Raises:
            RuntimeError: setup()が呼ばれていない場合
        """
        if self._handler is None:
            raise RuntimeError("Handler not initialized. Call setup() first.")
        return self._handler

    def setup(self) -> BotClient:
        """Botをセットアップして返す.

        Returns:
            初期化されたBotClientインスタンス
        """
        # メッセージハンドラー
        self._handler = MessageHandler(
            db=self.components.db,
            storage=self.components.storage,
            drive_storage=self.components.drive_storage,
            drive_auto_upload=self.components.drive_auto_upload,
        )

        # Botクライアント
        self._client = BotClient(on_ready_callback=self._on_ready)

        # Voice Recorder
        self._voice_recorder = VoiceRecorder(
            db=self.components.db,
            storage=self.components.storage,
        )

        # 統合Room通知サービス
        self._notifier = AggregationNotifier(
            db=self.components.db,
            bot=self._client,
            router=self.components.router,
        )

        # メッセージリスナー
        self._listener = MessageListener(
            client=self._client,
            on_message_callback=self._handler.handle_message,
        )

        # イベント登録
        self._register_events()

        logger.info("Bot setup completed")
        return self._client

    async def _on_ready(self) -> None:
        """Bot起動時のコールバック."""
        if self._client is None:
            return

        logger.info(f"Bot logged in as {self._client.user}")

        # 既存RoomのDiscordチャンネル名を更新
        await self._migrate_room_names()

        # スラッシュコマンドを登録
        if self.components.router:
            tree = await setup_commands(
                self._client,
                self.components.db,
                self.components.router,
                self._voice_recorder,
                storage=self.components.storage,
                drive_storage=self.components.drive_storage,
            )
            logger.info("Slash commands registered: /summary, /search")

            # コマンドを同期
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")

        logger.info("Bot is ready!")

    async def _migrate_room_names(self) -> None:
        """既存Roomの名前をDiscordチャンネル名に更新する."""
        if self._client is None:
            return

        from sqlalchemy import select

        from src.db.models import Room

        # Room-{ID}形式の名前を持つRoomを取得
        stmt = select(Room).where(Room.name.like("Room-%"))
        rooms = list(self.components.db.session.execute(stmt).scalars().all())

        if not rooms:
            return

        logger.info(f"Migrating {len(rooms)} room names...")
        updated_count = 0
        deleted_count = 0

        for room in rooms:
            try:
                # Discord APIからチャンネル情報を取得
                channel = self._client.get_channel(int(room.discord_channel_id))
                if channel is None:
                    # キャッシュにない場合はAPIで取得
                    try:
                        channel = await self._client.fetch_channel(int(room.discord_channel_id))
                    except discord.NotFound:
                        # チャンネルが削除されている
                        self.components.db.mark_room_deleted(room.id)
                        deleted_count += 1
                        logger.info(f"Room {room.id} marked as deleted (channel not found)")
                        continue
                    except discord.Forbidden:
                        # アクセス権限がない
                        logger.warning(f"No permission to access channel {room.discord_channel_id}")
                        continue

                if channel:
                    channel_name = getattr(channel, "name", None)
                    if channel_name:
                        self.components.db.update_room_name(room.id, channel_name)
                        updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate room {room.id}: {e}")

        if updated_count > 0 or deleted_count > 0:
            logger.info(f"Migrated {updated_count} room names, marked {deleted_count} as deleted")

    def _register_events(self) -> None:
        """イベントハンドラーを登録する."""
        if self._client is None or self._listener is None:
            return

        @self._client.event
        async def on_message(message: discord.Message) -> None:
            """メッセージ受信時のイベントハンドラー."""
            if self._listener is None:
                return
            await self._listener.on_message(message)
            await self._handle_notification(message)

        @self._client.event
        async def on_guild_channel_update(
            before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
        ) -> None:
            """チャンネル更新時にRoom名を更新."""
            if before.name != after.name:
                room = self.components.db.get_room_by_discord_id(str(after.id))
                if room:
                    self.components.db.update_room_name(room.id, after.name)
                    logger.info(f"Room name updated: {before.name} -> {after.name}")

        @self._client.event
        async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
            """チャンネル削除時にRoomをdeleted扱いに."""
            room = self.components.db.get_room_by_discord_id(str(channel.id))
            if room:
                self.components.db.mark_room_deleted(room.id)
                logger.info(f"Room marked as deleted: {channel.name}")

    async def _handle_notification(self, message: discord.Message) -> None:
        """新規メッセージの通知処理."""
        if message.author.bot:
            return

        if self._notifier is None:
            return

        # Roomを取得（存在する場合のみ通知）
        room = self.components.db.get_room_by_discord_id(str(message.channel.id))
        if room:
            saved_message = self.components.db.get_messages_by_room(room.id, limit=1)
            if saved_message:
                await self._notifier.notify_new_message(
                    room=room,
                    message=saved_message[0],
                    find_similar=True,
                )

    async def cleanup(self) -> None:
        """リソースをクリーンアップする."""
        if self._handler:
            await self._handler.close()
        self.components.db.close()
        logger.info("Cleanup completed")
