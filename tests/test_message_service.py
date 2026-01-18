"""MessageService テスト."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.listeners import MessageData
from src.bot.services.message_service import MessageService
from src.db.database import Database
from src.storage.local import LocalStorage


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """テスト用のDBインスタンス."""
    db = Database(":memory:")
    db.create_tables()
    return db


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    """テスト用のストレージインスタンス."""
    return LocalStorage(base_path=tmp_path / "files")


@pytest.fixture
def service(db: Database, storage: LocalStorage) -> MessageService:
    """テスト用のMessageServiceインスタンス."""
    return MessageService(db=db, storage=storage)


@pytest.fixture
def sample_message_data() -> MessageData:
    """テスト用のメッセージデータ."""
    return MessageData(
        message_id=123456789,
        guild_id=111111111,
        channel_id=222222222,
        author_id=333333333,
        author_name="TestUser",
        content="Hello, world!",
        attachments=[],
    )


class TestEnsureWorkspaceAndRoom:
    """ensure_workspace_and_roomのテスト."""

    def test_creates_workspace_and_room(
        self, service: MessageService, db: Database, sample_message_data: MessageData
    ) -> None:
        """Workspace/Roomが存在しない場合、新規作成する."""
        room = service.ensure_workspace_and_room(sample_message_data)

        assert room is not None
        assert room.discord_channel_id == str(sample_message_data["channel_id"])

        # Workspaceも作成されている
        workspace = db.get_workspace_by_discord_id(str(sample_message_data["guild_id"]))
        assert workspace is not None

    def test_reuses_existing_workspace_and_room(
        self, service: MessageService, db: Database, sample_message_data: MessageData
    ) -> None:
        """Workspace/Roomが存在する場合、既存のものを再利用する."""
        # 最初の呼び出しで作成
        room1 = service.ensure_workspace_and_room(sample_message_data)

        # 2回目の呼び出し
        room2 = service.ensure_workspace_and_room(sample_message_data)

        assert room1 is not None
        assert room2 is not None
        assert room1.id == room2.id

    def test_returns_none_for_dm(self, service: MessageService) -> None:
        """DMの場合、Noneを返す."""
        dm_data = MessageData(
            message_id=123456789,
            guild_id=None,  # DM
            channel_id=222222222,
            author_id=333333333,
            author_name="TestUser",
            content="Hello!",
            attachments=[],
        )

        room = service.ensure_workspace_and_room(dm_data)

        assert room is None


class TestDetermineMessageType:
    """determine_message_typeのテスト."""

    def test_text_message(self, service: MessageService) -> None:
        """テキストメッセージの判定."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="Hello",
            attachments=[],
        )

        assert service.determine_message_type(data) == "text"

    def test_image_message(self, service: MessageService) -> None:
        """画像メッセージの判定."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="",
            attachments=[{"content_type": "image/png", "filename": "test.png"}],
        )

        assert service.determine_message_type(data) == "image"

    def test_video_message(self, service: MessageService) -> None:
        """動画メッセージの判定."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="",
            attachments=[{"content_type": "video/mp4", "filename": "test.mp4"}],
        )

        assert service.determine_message_type(data) == "video"

    def test_voice_message(self, service: MessageService) -> None:
        """音声メッセージの判定."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="",
            attachments=[{"content_type": "audio/ogg", "filename": "voice.ogg"}],
        )

        assert service.determine_message_type(data) == "voice"

    def test_unknown_content_type(self, service: MessageService) -> None:
        """不明なcontent_typeはtextになる."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="",
            attachments=[{"content_type": "application/pdf", "filename": "doc.pdf"}],
        )

        assert service.determine_message_type(data) == "text"


class TestGetFileType:
    """_get_file_typeのテスト."""

    def test_image_type(self, service: MessageService) -> None:
        """画像タイプの判定."""
        assert service._get_file_type("image/png") == "image"
        assert service._get_file_type("image/jpeg") == "image"

    def test_video_type(self, service: MessageService) -> None:
        """動画タイプの判定."""
        assert service._get_file_type("video/mp4") == "video"

    def test_audio_type(self, service: MessageService) -> None:
        """音声タイプの判定."""
        assert service._get_file_type("audio/mpeg") == "voice"

    def test_document_type(self, service: MessageService) -> None:
        """ドキュメントタイプの判定."""
        assert service._get_file_type("application/pdf") == "document"
        assert service._get_file_type("text/plain") == "document"


class TestSaveMessageWithAttachments:
    """save_message_with_attachmentsのテスト."""

    @pytest.mark.asyncio
    async def test_saves_message_without_attachments(
        self, service: MessageService, db: Database, sample_message_data: MessageData
    ) -> None:
        """添付ファイルなしのメッセージを保存."""
        room = service.ensure_workspace_and_room(sample_message_data)
        assert room is not None

        message = await service.save_message_with_attachments(room, sample_message_data)

        assert message is not None
        assert message.content == "Hello, world!"
        assert message.sender_name == "TestUser"
        assert message.message_type == "text"

    @pytest.mark.asyncio
    async def test_saves_message_type_from_attachment(
        self, service: MessageService, db: Database
    ) -> None:
        """添付ファイルに基づいてメッセージタイプを設定."""
        data = MessageData(
            message_id=1,
            guild_id=1,
            channel_id=1,
            author_id=1,
            author_name="User",
            content="Image attached",
            attachments=[
                {
                    "content_type": "image/png",
                    "filename": "test.png",
                    "url": "https://example.com/test.png",
                    "size": 1000,
                }
            ],
        )

        room = service.ensure_workspace_and_room(data)
        assert room is not None

        # 添付ファイルのダウンロードをモック
        service._session = MagicMock()
        service._session.closed = False

        message = await service.save_message_with_attachments(room, data)

        assert message.message_type == "image"


class TestClose:
    """closeのテスト."""

    @pytest.mark.asyncio
    async def test_close_session(self, service: MessageService) -> None:
        """セッションを閉じる."""
        service._session = AsyncMock()
        service._session.closed = False

        await service.close()

        service._session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_drive_storage(self, service: MessageService) -> None:
        """Google Driveストレージを閉じる."""
        service.drive_storage = AsyncMock()

        await service.close()

        service.drive_storage.close.assert_called_once()
