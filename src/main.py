"""Discord Bot エントリーポイント.

このモジュールはDiscord Botの起動を担当します。
環境変数からトークンを読み込み、Botを起動します。

Usage:
    uv run python -m src.main
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from src.bot.client import BotClient
from src.bot.handlers import MessageHandler
from src.bot.listeners import MessageListener
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
    DB/ストレージを初期化してBotを起動する。
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

    # メッセージハンドラー初期化
    handler = MessageHandler(db=db, storage=storage)

    # Bot初期化
    async def on_ready() -> None:
        logger.info("Bot is ready!")

    client = BotClient(on_ready_callback=on_ready)

    # メッセージリスナー初期化
    listener = MessageListener(
        client=client,
        on_message_callback=handler.handle_message,
    )

    # イベントを登録
    @client.event
    async def on_message(message) -> None:  # type: ignore[no-untyped-def]
        await listener.on_message(message)

    # Bot起動
    logger.info("Starting bot...")
    try:
        client.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
