"""Message handlers.

メッセージ処理とDB/ストレージへの保存を担当するハンドラー。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import yaml

from src.bot.listeners import MessageData
from src.db.database import Database
from src.db.models import Room
from src.storage.base import StorageProvider
from src.storage.google_drive import GoogleDriveStorage

logger = logging.getLogger(__name__)


class MessageHandler:
    """メッセージ処理ハンドラー.

    メッセージの受信時に以下の処理を行う:
    - Workspace/Roomの自動作成
    - メッセージのDB保存
    - 添付ファイルのダウンロード・保存

    Attributes:
        db: Databaseインスタンス
        storage: StorageProviderインスタンス
        max_attachment_size: 添付ファイルの最大サイズ（バイト）
        session: 共有aiohttpセッション
        drive_storage: Google Driveストレージ（オプション）

    Example:
        >>> db = Database()
        >>> storage = LocalStorage()
        >>> handler = MessageHandler(db=db, storage=storage)
        >>> await handler.handle_message(message_data)
    """

    # 添付ファイルの最大サイズ（25MB = Discord無料プランの上限）
    DEFAULT_MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024

    def __init__(
        self,
        db: Database,
        storage: StorageProvider,
        max_attachment_size: int | None = None,
        config_path: Path | None = None,
        session: aiohttp.ClientSession | None = None,
        drive_storage: GoogleDriveStorage | None = None,
        drive_auto_upload: bool | None = None,
    ) -> None:
        """MessageHandlerを初期化する.

        Args:
            db: Databaseインスタンス
            storage: StorageProviderインスタンス
            max_attachment_size: 添付ファイル最大サイズ（バイト）。指定時は設定値を優先
            config_path: 設定ファイルのパス（既定: config.yaml）
            session: 共有aiohttpセッション（指定時はそれを利用）
            drive_storage: Google Driveストレージ（指定時は自動アップロードに利用）
            drive_auto_upload: 自動アップロード設定（指定時は設定値を優先）
        """
        self.db = db
        self.storage = storage
        config_path = config_path or Path("config.yaml")
        self.max_attachment_size = max_attachment_size or self._load_max_attachment_size(
            config_path
        )
        self._session = session
        self.drive_storage = drive_storage
        self.drive_auto_upload = (
            drive_auto_upload
            if drive_auto_upload is not None
            else self._load_drive_auto_upload(config_path)
        )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """共有セッションを確保する."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """保持しているセッションを閉じる."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self.drive_storage:
            await self.drive_storage.close()

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

    async def handle_message(self, data: MessageData) -> None:
        """メッセージを処理してDB/ストレージに保存する.

        DMはスキップし、サーバーメッセージのみ処理する。
        Workspace/Roomが存在しない場合は自動作成する。

        Args:
            data: MessageData型のメッセージデータ
        """
        # DMはスキップ（guild_idがNone）
        if data["guild_id"] is None:
            logger.debug("Skipping DM message")
            return

        # Workspace/Roomを確保（なければ作成）
        room = self._ensure_workspace_and_room(data)
        if room is None:
            logger.warning(f"Could not create/find room for channel {data['channel_id']}")
            return

        # メッセージタイプを判定
        message_type = self._determine_message_type(data)

        # メッセージをDBに保存
        message = self.db.save_message(
            room_id=room.id,
            sender_name=data["author_name"],
            sender_id=str(data["author_id"]),
            content=data["content"],
            message_type=message_type,
            discord_message_id=str(data["message_id"]),
        )

        # 添付ファイルがあれば保存
        if data["attachments"]:
            await self._save_attachments(
                message_id=message.id,
                attachments=data["attachments"],
                workspace_id=room.workspace_id,
                room_id=room.id,
            )

        logger.info(f"Saved message {message.id} from {data['author_name']}")

    def _ensure_workspace_and_room(self, data: MessageData) -> Room | None:
        """Workspace/Roomを確保する.

        存在しない場合は自動作成する。

        Args:
            data: MessageData型のメッセージデータ

        Returns:
            Roomオブジェクト、作成に失敗した場合はNone
        """
        guild_id = str(data["guild_id"])
        channel_id = str(data["channel_id"])

        # Workspaceを取得または作成
        workspace = self.db.get_workspace_by_discord_id(guild_id)
        if workspace is None:
            workspace = self.db.create_workspace(
                name=f"Workspace-{guild_id}",
                discord_server_id=guild_id,
            )
            logger.info(f"Created new workspace for guild {guild_id}")

        # Roomを取得または作成
        room = self.db.get_room_by_discord_id(channel_id)
        if room is None:
            room = self.db.create_room(
                workspace_id=workspace.id,
                name=f"Room-{channel_id}",
                discord_channel_id=channel_id,
                room_type="topic",
            )
            logger.info(f"Created new room for channel {channel_id}")

        return room

    def _determine_message_type(self, data: MessageData) -> str:
        """メッセージタイプを判定する.

        添付ファイルのcontent_typeに基づいて判定する。

        Args:
            data: MessageData型のメッセージデータ

        Returns:
            メッセージタイプ（text/image/video/voice）
        """
        if not data["attachments"]:
            return "text"

        # 最初の添付ファイルのcontent_typeで判定
        content_type = data["attachments"][0].get("content_type") or ""
        if content_type.startswith("image/"):
            return "image"
        elif content_type.startswith("video/"):
            return "video"
        elif content_type.startswith("audio/"):
            return "voice"
        return "text"

    async def _save_attachments(
        self,
        message_id: int,
        attachments: list[dict[str, Any]],
        workspace_id: int,
        room_id: int,
    ) -> None:
        """添付ファイルをダウンロードして保存する.

        Args:
            message_id: メッセージID
            attachments: 添付ファイル情報のリスト
            workspace_id: Workspace ID
            room_id: Room ID
        """
        session = await self._ensure_session()
        for att in attachments:
            try:
                # サイズチェック（DoS対策）
                file_size = att.get("size", 0)
                if file_size > self.max_attachment_size:
                    logger.warning(
                        f"Skipping {att['filename']}: size {file_size} exceeds "
                        f"limit {self.max_attachment_size}"
                    )
                    continue

                # ファイルをダウンロード
                async with session.get(att["url"]) as response:
                    if response.status != 200:
                        logger.error(
                            f"Failed to download {att['filename']}: " f"status {response.status}"
                        )
                        continue

                    # Content-Lengthでも再チェック
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > self.max_attachment_size:
                        logger.warning(
                            f"Skipping {att['filename']}: Content-Length "
                            f"{content_length} exceeds limit"
                        )
                        continue

                    content = await response.read()

                # ローカルストレージに保存
                file_path = await self.storage.save_file(
                    content=content,
                    workspace_id=workspace_id,
                    room_id=room_id,
                    filename=att["filename"],
                )

                drive_path = None
                if self.drive_storage and self.drive_auto_upload:
                    try:
                        drive_folder_parts = self._build_drive_folder_parts(workspace_id)
                        drive_file_path = await self.drive_storage.save_file_with_folder(
                            content=content,
                            filename=att["filename"],
                            folder_parts=drive_folder_parts,
                        )
                        drive_path = str(drive_file_path)
                    except Exception as exc:
                        logger.warning(f"Failed to upload {att['filename']} to Google Drive: {exc}")

                # ファイルタイプを判定
                file_type = self._get_file_type(att.get("content_type") or "")

                # DBに保存
                self.db.save_attachment(
                    message_id=message_id,
                    file_name=att["filename"],
                    file_path=str(file_path),
                    file_type=file_type,
                    file_size=att["size"],
                    drive_path=drive_path,
                )

                logger.info(f"Saved attachment: {att['filename']}")

            except Exception as e:
                logger.error(f"Error saving attachment {att['filename']}: {e}")

    def _get_file_type(self, content_type: str) -> str:
        """content_typeからファイルタイプを判定する.

        Args:
            content_type: MIMEタイプ

        Returns:
            ファイルタイプ（image/video/voice/document）
        """
        if content_type.startswith("image/"):
            return "image"
        elif content_type.startswith("video/"):
            return "video"
        elif content_type.startswith("audio/"):
            return "voice"
        return "document"

    def _build_drive_folder_parts(self, workspace_id: int) -> list[str]:
        """Google Driveの保存フォルダ構成を生成する."""
        workspace = self.db.get_workspace_by_id(workspace_id)
        workspace_name = workspace.name if workspace else f"workspace-{workspace_id}"
        date_str = datetime.now().strftime("%Y-%m-%d")
        return [workspace_name, date_str]
