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

from dotenv import load_dotenv

from src.bot.initializer import BotInitializer
from src.factory import create_app_components

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Botを起動する.

    環境変数からDISCORD_BOT_TOKENを読み込み、
    ファクトリを使用してコンポーネントを初期化し、Botを起動する。
    """
    # 環境変数を読み込み
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not found in environment")
        logger.info("Please set DISCORD_TOKEN in .env file")
        return

    # コンポーネント生成（ファクトリに委譲）
    components = create_app_components()
    logger.info("Components initialized")

    # Bot初期化
    initializer = BotInitializer(components)
    client = initializer.setup()

    # Bot起動
    logger.info("Starting bot...")
    try:
        client.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        asyncio.run(initializer.cleanup())


if __name__ == "__main__":
    main()
