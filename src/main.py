"""Discord Bot エントリーポイント.

このモジュールはDiscord Botの起動を担当します。
環境変数からトークンを読み込み、Botを起動します。

Usage:
    uv run python -m src.main

Features:
    - メッセージ保存・添付ファイル管理
    - AIルーティング（OpenAI, Anthropic, Google, Groq）
    - /summary, /searchスラッシュコマンド
    - 統合Room通知
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.ai.router import AIRouter
from src.bot.client import BotClient
from src.bot.commands import setup_commands
from src.bot.handlers import MessageHandler
from src.bot.listeners import MessageListener
from src.bot.notifier import AggregationNotifier
from src.db.database import Database
from src.storage.local import LocalStorage

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Botを起動する.

    環境変数からDISCORD_BOT_TOKENを読み込み、
    DB/ストレージ/AIルーターを初期化してBotを起動する。
    """
    # 環境変数を読み込み
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not found in environment")
        logger.info("Please set DISCORD_TOKEN in .env file")
        return

    # データディレクトリを作成
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # DB初期化
    db_path = data_dir / "app.db"
    db = Database(f"sqlite:///{db_path}")
    db.create_tables()
    logger.info(f"Database initialized: {db_path}")

    # ストレージ初期化
    storage = LocalStorage(base_path=data_dir / "files")
    logger.info(f"Storage initialized: {storage.base_path}")

    # AIルーター初期化
    config_path = Path("config.yaml")
    if config_path.exists():
        router = AIRouter.from_yaml(str(config_path))
        logger.info("AI Router initialized from config.yaml")
    else:
        logger.warning("config.yaml not found. AI features may not work.")
        router = None

    # メッセージハンドラー初期化
    handler = MessageHandler(db=db, storage=storage)

    # Bot初期化
    async def on_ready() -> None:
        """Bot起動時のコールバック."""
        logger.info(f"Bot logged in as {client.user}")

        # スラッシュコマンドを登録
        if router:
            tree = await setup_commands(client, db, router)
            logger.info("Slash commands registered: /summary, /search")

            # コマンドを同期
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")

        logger.info("Bot is ready!")

    client = BotClient(on_ready_callback=on_ready)

    # 統合Room通知サービス初期化
    notifier = AggregationNotifier(db=db, bot=client, router=router)

    # メッセージリスナー初期化
    listener = MessageListener(
        client=client,
        on_message_callback=handler.handle_message,
    )

    # イベントを登録
    @client.event
    async def on_message(message) -> None:  # type: ignore[no-untyped-def]
        """メッセージ受信時のイベントハンドラー."""
        await listener.on_message(message)

        # メッセージを保存した後、統合Roomに通知
        if message.author.bot:
            return

        # Roomを取得（存在する場合のみ通知）
        room = db.get_room_by_discord_id(str(message.channel.id))
        if room:
            saved_message = db.get_messages_by_room(room.id, limit=1)
            if saved_message:
                await notifier.notify_new_message(
                    room=room,
                    message=saved_message[0],
                    find_similar=True,
                )

    # Bot起動
    logger.info("Starting bot...")
    try:
        client.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        asyncio.run(handler.close())
        db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
