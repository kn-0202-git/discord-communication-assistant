"""Bot services package.

メッセージ処理などのビジネスロジックを担当するサービス層。
"""

from src.bot.services.message_service import MessageService

__all__ = ["MessageService"]
