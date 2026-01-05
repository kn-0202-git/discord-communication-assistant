"""Message handlers.

メッセージ処理とDB/ストレージへの保存を担当するハンドラー。
"""

import logging
from typing import Any

import aiohttp

from src.bot.listeners import MessageData
from src.db.database import Database
from src.db.models import Room
from src.storage.local import LocalStorage

logger = logging.getLogger(__name__)


class MessageHandler:
    """メッセージ処理ハンドラー.

    メッセージの受信時に以下の処理を行う:
    - Workspace/Roomの自動作成
    - メッセージのDB保存
    - 添付ファイルのダウンロード・保存

    Attributes:
        db: Databaseインスタンス
        storage: LocalStorageインスタンス

    Example:
        >>> db = Database()
        >>> storage = LocalStorage()
        >>> handler = MessageHandler(db=db, storage=storage)
        >>> await handler.handle_message(message_data)
    """

    def __init__(
        self,
        db: Database,
        storage: LocalStorage,
    ) -> None:
        """MessageHandlerを初期化する.

        Args:
            db: Databaseインスタンス
            storage: LocalStorageインスタンス
        """
        self.db = db
        self.storage = storage

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
        async with aiohttp.ClientSession() as session:
            for att in attachments:
                try:
                    # ファイルをダウンロード
                    async with session.get(att["url"]) as response:
                        if response.status != 200:
                            logger.error(
                                f"Failed to download {att['filename']}: "
                                f"status {response.status}"
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

                    # ファイルタイプを判定
                    file_type = self._get_file_type(att.get("content_type") or "")

                    # DBに保存
                    self.db.save_attachment(
                        message_id=message_id,
                        file_name=att["filename"],
                        file_path=str(file_path),
                        file_type=file_type,
                        file_size=att["size"],
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
