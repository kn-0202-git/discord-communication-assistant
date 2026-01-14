"""Handler tests.

メッセージハンドラーのテスト。
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.bot.handlers import MessageHandler
from src.bot.listeners import MessageData
from src.db.database import Database
from src.storage.local import LocalStorage


class TestMessageHandler:
    """MessageHandlerのテスト."""

    @pytest.fixture
    def db(self) -> Database:
        """インメモリデータベースを作成."""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def storage(self, tmp_path: Path) -> LocalStorage:
        """一時ディレクトリを使用したストレージを作成."""
        return LocalStorage(base_path=tmp_path)

    @pytest.fixture
    def handler(self, db: Database, storage: LocalStorage) -> MessageHandler:
        """MessageHandlerを作成."""
        return MessageHandler(db=db, storage=storage)

    def test_loads_max_attachment_size_from_config(
        self, db: Database, storage: LocalStorage, tmp_path: Path
    ) -> None:
        """正常系: config.yamlから添付サイズ上限を読み込む."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("attachments:\n  max_size_bytes: 123\n", encoding="utf-8")

        handler = MessageHandler(db=db, storage=storage, config_path=config_path)

        assert handler.max_attachment_size == 123

    def _create_message_data(
        self,
        content: str = "テストメッセージ",
        author_name: str = "テストユーザー",
        author_id: int = 123,
        guild_id: int | None = 456,
        channel_id: int = 789,
        message_id: int = 111,
        attachments: list | None = None,
    ) -> MessageData:
        """テスト用のMessageDataを作成."""
        return MessageData(
            content=content,
            author_name=author_name,
            author_id=author_id,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            attachments=attachments or [],
        )

    @pytest.mark.asyncio
    async def test_handle_message_creates_workspace_and_room(
        self, handler: MessageHandler, db: Database
    ) -> None:
        """正常系: メッセージ受信でWorkspaceとRoom自動作成."""
        data = self._create_message_data()

        await handler.handle_message(data)

        # Workspaceが作成されている
        workspace = db.get_workspace_by_discord_id("456")
        assert workspace is not None
        assert workspace.discord_server_id == "456"

        # Roomが作成されている
        room = db.get_room_by_discord_id("789")
        assert room is not None
        assert room.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_handle_message_saves_to_db(self, handler: MessageHandler, db: Database) -> None:
        """正常系: メッセージがDBに保存される."""
        data = self._create_message_data(
            content="保存テスト",
            author_name="田中",
        )

        await handler.handle_message(data)

        room = db.get_room_by_discord_id("789")
        messages = db.get_messages_by_room(room.id)

        assert len(messages) == 1
        assert messages[0].content == "保存テスト"
        assert messages[0].sender_name == "田中"

    @pytest.mark.asyncio
    async def test_handle_message_skips_dm(self, handler: MessageHandler, db: Database) -> None:
        """正常系: DMはスキップ."""
        data = self._create_message_data(
            content="DMメッセージ",
            guild_id=None,  # DM
        )

        await handler.handle_message(data)

        # Workspaceは作成されない
        workspace = db.get_workspace_by_discord_id("None")
        assert workspace is None

    @pytest.mark.asyncio
    async def test_room_isolation(self, handler: MessageHandler, db: Database) -> None:
        """正常系: Room1とRoom2のデータ分離."""
        # Room1にメッセージ
        data1 = self._create_message_data(
            content="Room1のメッセージ",
            author_name="ユーザー1",
            channel_id=201,
            message_id=1001,  # 異なるメッセージID
        )
        await handler.handle_message(data1)

        # Room2にメッセージ
        data2 = self._create_message_data(
            content="Room2のメッセージ",
            author_name="ユーザー2",
            channel_id=202,
            message_id=1002,  # 異なるメッセージID
        )
        await handler.handle_message(data2)

        room1 = db.get_room_by_discord_id("201")
        room2 = db.get_room_by_discord_id("202")

        messages1 = db.get_messages_by_room(room1.id)
        messages2 = db.get_messages_by_room(room2.id)

        # 各Roomに自分のメッセージのみ
        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content == "Room1のメッセージ"
        assert messages2[0].content == "Room2のメッセージ"

    @pytest.mark.asyncio
    async def test_handle_message_with_image_attachment(
        self, handler: MessageHandler, db: Database, tmp_path: Path
    ) -> None:
        """正常系: 画像添付ファイルがダウンロード・保存される."""
        # モックでHTTPリクエストをシミュレート
        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        data = self._create_message_data(
            content="画像付きメッセージ",
            attachments=[
                {
                    "id": 1,
                    "filename": "photo.png",
                    "url": "https://example.com/photo.png",
                    "size": 108,
                    "content_type": "image/png",
                }
            ],
        )

        # aiohttpのモック
        with patch("src.bot.handlers.aiohttp.ClientSession", autospec=True) as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=fake_image)

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None

            mock_session.return_value = mock_session_instance

            await handler.handle_message(data)

        room = db.get_room_by_discord_id("789")
        messages = db.get_messages_by_room(room.id)

        # メッセージが保存されている
        assert len(messages) == 1
        assert messages[0].message_type == "image"

    @pytest.mark.asyncio
    async def test_handle_message_auto_uploads_to_drive(
        self, db: Database, storage: LocalStorage
    ) -> None:
        """正常系: Drive自動アップロード時にdrive_pathが保存される."""
        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
        data = self._create_message_data(
            attachments=[
                {
                    "id": 1,
                    "filename": "photo.png",
                    "url": "https://example.com/photo.png",
                    "size": 18,
                    "content_type": "image/png",
                }
            ],
        )

        drive_storage = AsyncMock()
        drive_storage.save_file_with_folder = AsyncMock(return_value=Path("drive-id"))
        drive_storage.close = AsyncMock()
        handler = MessageHandler(
            db=db,
            storage=storage,
            drive_storage=drive_storage,
            drive_auto_upload=True,
        )

        with patch("src.bot.handlers.aiohttp.ClientSession", autospec=True) as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=fake_image)

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = AsyncMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None

            mock_session.return_value = mock_session_instance

            await handler.handle_message(data)

        room = db.get_room_by_discord_id("789")
        attachment = db.get_latest_attachment_by_room(room.id)
        assert attachment is not None
        assert attachment.drive_path == "drive-id"
        drive_storage.save_file_with_folder.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_message_skips_oversized_attachment(
        self, db: Database, storage: LocalStorage
    ) -> None:
        """正常系: 上限超過の添付は保存しない."""
        handler = MessageHandler(db=db, storage=storage, max_attachment_size=1)

        data = self._create_message_data(
            attachments=[
                {
                    "id": 1,
                    "filename": "too_large.bin",
                    "url": "https://example.com/too_large.bin",
                    "size": 2,
                    "content_type": "application/octet-stream",
                }
            ],
        )

        storage.save_file = AsyncMock()  # type: ignore[assignment]

        with patch("src.bot.handlers.aiohttp.ClientSession", autospec=True) as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.__aenter__.return_value = mock_session_instance
            mock_session_instance.__aexit__.return_value = None
            mock_session.return_value = mock_session_instance

            await handler.handle_message(data)

        storage.save_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_determine_message_type_text(self, handler: MessageHandler) -> None:
        """正常系: 添付なしはtext."""
        data = self._create_message_data(attachments=[])
        assert handler._determine_message_type(data) == "text"

    @pytest.mark.asyncio
    async def test_determine_message_type_image(self, handler: MessageHandler) -> None:
        """正常系: 画像添付はimage."""
        data = self._create_message_data(attachments=[{"content_type": "image/png"}])
        assert handler._determine_message_type(data) == "image"

    @pytest.mark.asyncio
    async def test_determine_message_type_video(self, handler: MessageHandler) -> None:
        """正常系: 動画添付はvideo."""
        data = self._create_message_data(attachments=[{"content_type": "video/mp4"}])
        assert handler._determine_message_type(data) == "video"

    @pytest.mark.asyncio
    async def test_determine_message_type_voice(self, handler: MessageHandler) -> None:
        """正常系: 音声添付はvoice."""
        data = self._create_message_data(attachments=[{"content_type": "audio/ogg"}])
        assert handler._determine_message_type(data) == "voice"

    @pytest.mark.asyncio
    async def test_get_file_type(self, handler: MessageHandler) -> None:
        """正常系: content_typeからファイルタイプを判定."""
        assert handler._get_file_type("image/png") == "image"
        assert handler._get_file_type("video/mp4") == "video"
        assert handler._get_file_type("audio/ogg") == "voice"
        assert handler._get_file_type("application/pdf") == "document"
        assert handler._get_file_type("") == "document"

    @pytest.mark.asyncio
    async def test_reuses_existing_workspace_and_room(
        self, handler: MessageHandler, db: Database
    ) -> None:
        """正常系: 既存のWorkspace/Roomを再利用."""
        # 1回目
        data1 = self._create_message_data(content="1回目")
        await handler.handle_message(data1)

        # 2回目（同じチャンネル）
        data2 = self._create_message_data(content="2回目", message_id=222)
        await handler.handle_message(data2)

        # Workspaceは1つのみ
        workspace = db.get_workspace_by_discord_id("456")
        assert workspace is not None

        # Roomは1つのみ
        room = db.get_room_by_discord_id("789")
        assert room is not None

        # メッセージは2つ
        messages = db.get_messages_by_room(room.id)
        assert len(messages) == 2


class TestRoomAggregation:
    """Room集約（Room3）のテスト."""

    @pytest.fixture
    def db(self) -> Database:
        """インメモリデータベースを作成."""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    def test_room3_can_see_room1_via_link(self, db: Database) -> None:
        """正常系: Room3からRoom1のデータが見える（RoomLink経由）."""
        # Workspace作成
        workspace = db.create_workspace(name="Test", discord_server_id="100")

        # Room作成
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="Room1",
            discord_channel_id="201",
            room_type="topic",
        )
        room3 = db.create_room(
            workspace_id=workspace.id,
            name="Room3-Aggregation",
            discord_channel_id="203",
            room_type="aggregation",
        )

        # RoomLink作成: Room1 -> Room3
        db.create_room_link(
            source_room_id=room1.id,
            target_room_id=room3.id,
            link_type="one_way",
        )

        # Room1にメッセージ保存
        db.save_message(
            room_id=room1.id,
            sender_name="User",
            sender_id="1",
            content="Room1のデータ",
            message_type="text",
            discord_message_id="msg1",
        )

        # Room3からリンク先のRoomを取得
        linked_rooms = db.get_linked_rooms(room3.id)

        assert len(linked_rooms) == 1
        assert linked_rooms[0].id == room1.id

        # リンク先のメッセージを取得
        messages = db.get_messages_by_room(linked_rooms[0].id)
        assert len(messages) == 1
        assert messages[0].content == "Room1のデータ"

    def test_room2_cannot_see_room1_without_link(self, db: Database) -> None:
        """正常系: Room2からRoom1のデータが見えない（リンクなし）."""
        # Workspace作成
        workspace = db.create_workspace(name="Test", discord_server_id="100")

        # Room作成
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="Room1",
            discord_channel_id="201",
            room_type="topic",
        )
        room2 = db.create_room(
            workspace_id=workspace.id,
            name="Room2",
            discord_channel_id="202",
            room_type="topic",
        )

        # Room1にメッセージ保存
        db.save_message(
            room_id=room1.id,
            sender_name="User",
            sender_id="1",
            content="Room1のデータ",
            message_type="text",
            discord_message_id="msg1",
        )

        # Room2からリンク先を取得（リンクなし）
        linked_rooms = db.get_linked_rooms(room2.id)
        assert len(linked_rooms) == 0

        # Room2のメッセージを取得（空）
        messages = db.get_messages_by_room(room2.id)
        assert len(messages) == 0
