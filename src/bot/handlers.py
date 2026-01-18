"""Message handlers - オーケストレーション層.

メッセージ処理のエントリーポイント。
実際のビジネスロジックはMessageServiceに委譲する。
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from src.bot.listeners import MessageData
from src.bot.services.message_service import MessageService
from src.db.database import Database
from src.db.models import Room
from src.storage.base import StorageProvider
from src.storage.google_drive import GoogleDriveStorage

logger = logging.getLogger(__name__)


class MessageHandler:
    """メッセージ処理のオーケストレーター.

    メッセージの受信時に、適切なサービスに処理を委譲する。

    責務:
    - DM判定（フィルタリング）
    - MessageServiceへの委譲

    MessageServiceに委譲する責務:
    - Workspace/Room確保
    - メッセージタイプ判定
    - メッセージ・添付ファイル保存

    Attributes:
        db: Databaseインスタンス
        storage: StorageProviderインスタンス
        max_attachment_size: 添付ファイルの最大サイズ（バイト）
        drive_storage: Google Driveストレージ（オプション）
        drive_auto_upload: 自動アップロードフラグ

    Example:
        >>> db = Database()
        >>> storage = LocalStorage()
        >>> handler = MessageHandler(db=db, storage=storage)
        >>> await handler.handle_message(message_data)
    """

    DEFAULT_MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024

    def __init__(
        self,
        db: Database,
        storage: StorageProvider,
        max_attachment_size: int | None = None,
        config_path: Path | None = None,
        session: Any | None = None,  # 後方互換性のため保持
        drive_storage: GoogleDriveStorage | None = None,
        drive_auto_upload: bool | None = None,
    ) -> None:
        """MessageHandlerを初期化する.

        Args:
            db: Databaseインスタンス
            storage: StorageProviderインスタンス
            max_attachment_size: 添付ファイル最大サイズ（バイト）。指定時は設定値を優先
            config_path: 設定ファイルのパス（既定: config.yaml）
            session: 後方互換性のため保持（未使用）
            drive_storage: Google Driveストレージ（指定時は自動アップロードに利用）
            drive_auto_upload: 自動アップロード設定（指定時は設定値を優先）
        """
        config_path = config_path or Path("config.yaml")

        # 設定読み込み
        resolved_max_size = max_attachment_size or self._load_max_attachment_size(config_path)
        resolved_auto_upload = (
            drive_auto_upload
            if drive_auto_upload is not None
            else self._load_drive_auto_upload(config_path)
        )

        # MessageService初期化
        self._service = MessageService(
            db=db,
            storage=storage,
            drive_storage=drive_storage,
            drive_auto_upload=resolved_auto_upload,
            max_attachment_size=resolved_max_size,
        )

        # 後方互換性のためのプロパティ
        self.db = db
        self.storage = storage
        self.max_attachment_size = resolved_max_size
        self.drive_storage = drive_storage
        self.drive_auto_upload = resolved_auto_upload

    async def handle_message(self, data: MessageData) -> None:
        """メッセージを処理してDB/ストレージに保存する.

        DMはスキップし、サーバーメッセージのみ処理する。

        Args:
            data: MessageData型のメッセージデータ
        """
        # DM判定（オーケストレーターの責務）
        if data["guild_id"] is None:
            logger.debug("Skipping DM message")
            return

        # Workspace/Room確保（サービスに委譲）
        room = self._service.ensure_workspace_and_room(data)
        if room is None:
            logger.warning(f"Could not create/find room for channel {data['channel_id']}")
            return

        # メッセージ保存（サービスに委譲）
        await self._service.save_message_with_attachments(room, data)

    async def close(self) -> None:
        """リソースをクリーンアップする."""
        await self._service.close()

    # ===== 後方互換性のためのメソッド（既存テストで使用） =====

    def _ensure_workspace_and_room(self, data: MessageData) -> Room | None:
        """Workspace/Roomを確保する（後方互換性用）.

        新規コードではMessageService.ensure_workspace_and_roomを使用すること。
        """
        return self._service.ensure_workspace_and_room(data)

    def _determine_message_type(self, data: MessageData) -> str:
        """メッセージタイプを判定する（後方互換性用）.

        新規コードではMessageService.determine_message_typeを使用すること。
        """
        return self._service.determine_message_type(data)

    def _get_file_type(self, content_type: str) -> str:
        """content_typeからファイルタイプを判定する（後方互換性用）.

        新規コードではMessageService._get_file_typeを使用すること。
        """
        return self._service._get_file_type(content_type)

    # ===== 設定読み込みメソッド =====

    @classmethod
    def _load_max_attachment_size(cls, config_path: Path) -> int:
        """設定ファイルから添付ファイル最大サイズを取得する."""
        if not config_path.exists():
            return cls.DEFAULT_MAX_ATTACHMENT_SIZE

        try:
            with open(config_path, encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
        except Exception as exc:  # pragma: no cover - 設定読込失敗時は既定値
            logger.warning(f"Failed to read config.yaml: {exc}")
            return cls.DEFAULT_MAX_ATTACHMENT_SIZE

        attachments = config.get("attachments") or {}
        value = attachments.get("max_size_bytes")
        if isinstance(value, int) and value > 0:
            return value

        return cls.DEFAULT_MAX_ATTACHMENT_SIZE

    @staticmethod
    def _load_drive_auto_upload(config_path: Path) -> bool:
        """設定ファイルからGoogle Drive自動アップロード設定を取得する."""
        if not config_path.exists():
            return False

        try:
            with open(config_path, encoding="utf-8") as file:
                config = yaml.safe_load(file) or {}
        except Exception as exc:  # pragma: no cover - 設定読込失敗時は既定値
            logger.warning(f"Failed to read config.yaml: {exc}")
            return False

        drive_settings = config.get("google_drive") or {}
        return bool(drive_settings.get("auto_upload", False))
