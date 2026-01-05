"""Discord Bot モジュール

このモジュールはDiscord Botの基盤機能を提供します。

Classes:
    BotClient: Discord Botのメインクライアント
    MessageListener: メッセージイベントのリスナー
    GuildListener: サーバーイベントのリスナー
    MessageHandler: メッセージ処理ハンドラー
    BotCommands: Botコマンド（/summary, /search）
    AggregationNotifier: 統合Room通知サービス

Types:
    MessageData: メッセージデータの型定義
"""

from src.bot.client import BotClient
from src.bot.commands import BotCommands, SummaryCommands, setup_commands
from src.bot.handlers import MessageHandler
from src.bot.listeners import GuildListener, MessageData, MessageListener
from src.bot.notifier import AggregationNotifier, NotificationError, setup_notifier

__all__ = [
    "BotClient",
    "MessageListener",
    "GuildListener",
    "MessageHandler",
    "MessageData",
    "BotCommands",
    "SummaryCommands",  # 後方互換性
    "setup_commands",
    "AggregationNotifier",
    "NotificationError",
    "setup_notifier",
]
