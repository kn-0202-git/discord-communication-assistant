"""メッセージ処理サービス.

メッセージの保存、Workspace/Room管理などの責務を担当する。
"""

import logging
from datetime import datetime
from typing import Any

import aiohttp

from src.bot.listeners import MessageData
from src.db.database import Database
from src.db.models import Message, Room
from src.storage.base import StorageProvider
from src.storage.google_drive import GoogleDriveStorage

logger = logging.getLogger(__name__)


class MessageService:
    """メッセージ処理サービス.

    メッセージの保存に関するビジネスロジックを担当する。

    責務:
    - Workspace/Roomの確保（自動作成）
    - メッセージタイプの判定
    - メッセージと添付ファイルの保存

    Attributes:
        db: Databaseインスタンス
        storage: StorageProviderインスタンス
        drive_storage: Google Driveストレージ（オプション）
        drive_auto_upload: 自動アップロードフラグ
        max_attachment_size: 添付ファイルの最大サイズ（バイト）

    Example:
        >>> service = MessageService(db, storage)
        >>> room = service.ensure_workspace_and_room(data)
        >>> await service.save_message_with_attachments(room, data)
    """

    DEFAULT_MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024

    def __init__(
        self,
        db: Database,
        storage: StorageProvider,
        drive_storage: GoogleDriveStorage | None = None,
        drive_auto_upload: bool = False,
        max_attachment_size: int | None = None,
    ) -> None:
        """MessageServiceを初期化する.

        Args:
            db: Databaseインスタンス
            storage: StorageProviderインスタンス
            drive_storage: Google Driveストレージ（オプション）
            drive_auto_upload: 自動アップロードフラグ
            max_attachment_size: 添付ファイル最大サイズ（バイト）
        """
        self.db = db
        self.storage = storage
        self.drive_storage = drive_storage
        self.drive_auto_upload = drive_auto_upload
        self.max_attachment_size = max_attachment_size or self.DEFAULT_MAX_ATTACHMENT_SIZE
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """共有セッションを確保する."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """リソースをクリーンアップする."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self.drive_storage:
            await self.drive_storage.close()

    def ensure_workspace_and_room(self, data: MessageData) -> Room | None:
        """Workspace/Roomを確保する（なければ作成）.

        Args:
            data: メッセージデータ

        Returns:
            Roomオブジェクト、guild_idがNoneの場合はNone
        """
        if data["guild_id"] is None:
            return None

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

    def determine_message_type(self, data: MessageData) -> str:
        """メッセージタイプを判定する.

        添付ファイルのcontent_typeに基づいて判定する。

        Args:
            data: メッセージデータ

        Returns:
            メッセージタイプ（text/image/video/voice）
        """
        if not data["attachments"]:
            return "text"

        content_type = data["attachments"][0].get("content_type") or ""
        if content_type.startswith("image/"):
            return "image"
        elif content_type.startswith("video/"):
            return "video"
        elif content_type.startswith("audio/"):
            return "voice"
        return "text"

    async def save_message_with_attachments(
        self,
        room: Room,
        data: MessageData,
    ) -> Message:
        """メッセージと添付ファイルを保存する.

        Args:
            room: Roomオブジェクト
            data: メッセージデータ

        Returns:
            保存されたMessageオブジェクト
        """
        message_type = self.determine_message_type(data)

        # メッセージ保存
        message = self.db.save_message(
            room_id=room.id,
            sender_name=data["author_name"],
            sender_id=str(data["author_id"]),
            content=data["content"],
            message_type=message_type,
            discord_message_id=str(data["message_id"]),
        )

        # 添付ファイル保存
        if data["attachments"]:
            await self._save_attachments(
                message_id=message.id,
                attachments=data["attachments"],
                workspace_id=room.workspace_id,
                room_id=room.id,
            )

        logger.info(f"Saved message {message.id} from {data['author_name']}")
        return message

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

                # Google Driveにアップロード（オプション）
                drive_path = await self._upload_to_drive(content, att["filename"], workspace_id)

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

    async def _upload_to_drive(
        self,
        content: bytes,
        filename: str,
        workspace_id: int,
    ) -> str | None:
        """Google Driveにアップロードする.

        Args:
            content: ファイルコンテンツ
            filename: ファイル名
            workspace_id: Workspace ID

        Returns:
            Driveのパス、アップロードしない場合はNone
        """
        if not self.drive_storage or not self.drive_auto_upload:
            return None

        try:
            folder_parts = self._build_drive_folder_parts(workspace_id)
            drive_file_path = await self.drive_storage.save_file_with_folder(
                content=content,
                filename=filename,
                folder_parts=folder_parts,
            )
            return str(drive_file_path)
        except Exception as exc:
            logger.warning(f"Failed to upload {filename} to Google Drive: {exc}")
            return None

    def _build_drive_folder_parts(self, workspace_id: int) -> list[str]:
        """Google Driveの保存フォルダ構成を生成する.

        Args:
            workspace_id: Workspace ID

        Returns:
            フォルダパーツのリスト
        """
        workspace = self.db.get_workspace_by_id(workspace_id)
        workspace_name = workspace.name if workspace else f"workspace-{workspace_id}"
        date_str = datetime.now().strftime("%Y-%m-%d")
        return [workspace_name, date_str]

    @staticmethod
    def _get_file_type(content_type: str) -> str:
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
