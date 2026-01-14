"""コマンドのテスト

TEST_PLAN.md: CMD-01 ~ CMD-10
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.db.database import Database
from src.storage.local import LocalStorage


class TestDateTimeParser:
    """日時パーサーのテスト"""

    def test_parse_relative_days(self) -> None:
        """CMD-01: 相対日時パース（日）"""
        from src.bot.commands import parse_due_date

        now = datetime.now(UTC)
        result = parse_due_date("3d")

        # 3日後であることを確認（1秒の誤差を許容）
        expected = now + timedelta(days=3)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_hours(self) -> None:
        """CMD-02: 相対日時パース（時間）"""
        from src.bot.commands import parse_due_date

        now = datetime.now(UTC)
        result = parse_due_date("2h")

        expected = now + timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_relative_minutes(self) -> None:
        """CMD-03: 相対日時パース（分）"""
        from src.bot.commands import parse_due_date

        now = datetime.now(UTC)
        result = parse_due_date("30m")

        expected = now + timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_absolute_date(self) -> None:
        """CMD-04: 絶対日時パース（日付のみ）"""
        from src.bot.commands import parse_due_date

        result = parse_due_date("2025-01-15")

        # 指定した日付の0時0分であること
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_absolute_datetime(self) -> None:
        """CMD-05: 絶対日時パース（日付と時刻）"""
        from src.bot.commands import parse_due_date

        result = parse_due_date("2025-01-15 14:30")

        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_invalid_format(self) -> None:
        """CMD-06: 無効な日時形式"""
        from src.bot.commands import parse_due_date

        with pytest.raises(ValueError, match="日時の形式が正しくありません"):
            parse_due_date("invalid")

    def test_parse_zero_value(self) -> None:
        """境界値: 0の値"""
        from src.bot.commands import parse_due_date

        with pytest.raises(ValueError, match="0より大きい値"):
            parse_due_date("0d")


class TestRemindCommand:
    """/remind コマンドのテスト"""

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_interaction(self):
        """モックInteraction"""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.id = 123456789
        interaction.channel = MagicMock()
        interaction.channel.id = 987654321
        return interaction

    @pytest.fixture
    def bot_commands(self, db):
        """BotCommandsインスタンス（CommandTreeをモック）"""
        from src.bot.commands import BotCommands

        mock_tree = MagicMock()
        mock_router = MagicMock()
        return BotCommands(mock_tree, db, mock_router)

    @pytest.mark.asyncio
    async def test_remind_command_creates_reminder(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-07: /remind でリマインダー登録"""
        # Workspaceを作成
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # /remind を実行
        await bot_commands._handle_remind(mock_interaction, "納品確認", "1d", "製品Xの納品確認")

        # リマインダーが作成されたことを確認
        reminders = db.get_reminders_by_workspace(workspace.id)
        assert len(reminders) == 1
        assert reminders[0].title == "納品確認"
        assert reminders[0].description == "製品Xの納品確認"

        # 成功メッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_kwargs = mock_interaction.followup.send.call_args.kwargs
        assert "embed" in call_kwargs
        embed = call_kwargs["embed"]
        # Embedの内容を確認
        assert embed.title == "リマインダーを登録しました"

    @pytest.mark.asyncio
    async def test_remind_command_without_description(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-08: /remind でリマインダー登録（説明なし）"""
        # Workspaceを作成
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # /remind を実行（説明なし）
        await bot_commands._handle_remind(mock_interaction, "会議", "2h", None)

        # リマインダーが作成されたことを確認
        reminders = db.get_reminders_by_workspace(workspace.id)
        assert len(reminders) == 1
        assert reminders[0].title == "会議"
        assert reminders[0].description is None

    @pytest.mark.asyncio
    async def test_remind_command_without_workspace(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-09: 未登録サーバーでの /remind"""
        # Workspaceなしで /remind を実行
        await bot_commands._handle_remind(mock_interaction, "タスク", "1d", None)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "登録されていません" in str(call_args)

    @pytest.mark.asyncio
    async def test_remind_command_invalid_date(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-10: 無効な日付形式での /remind"""
        db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # 無効な日付で /remind を実行
        await bot_commands._handle_remind(mock_interaction, "タスク", "invalid", None)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "形式が正しくありません" in str(call_args)


class TestRemindersCommand:
    """/reminders コマンドのテスト"""

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_interaction(self):
        """モックInteraction"""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.id = 123456789
        return interaction

    @pytest.fixture
    def bot_commands(self, db):
        """BotCommandsインスタンス"""
        from src.bot.commands import BotCommands

        mock_tree = MagicMock()
        mock_router = MagicMock()
        return BotCommands(mock_tree, db, mock_router)

    @pytest.mark.asyncio
    async def test_reminders_command_shows_list(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-11: /reminders でリマインダー一覧表示"""
        # Workspaceを作成
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # リマインダーを作成
        db.create_reminder(
            workspace_id=workspace.id,
            title="タスク1",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )
        db.create_reminder(
            workspace_id=workspace.id,
            title="タスク2",
            due_date=datetime.now(UTC) + timedelta(days=2),
        )

        # /reminders を実行
        await bot_commands._handle_reminders(mock_interaction)

        # 成功メッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_kwargs = mock_interaction.followup.send.call_args.kwargs
        assert "embed" in call_kwargs
        embed = call_kwargs["embed"]
        # リストが表示されていること
        assert "2件" in embed.description

    @pytest.mark.asyncio
    async def test_reminders_command_empty_list(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-12: リマインダーがない場合"""
        # Workspaceを作成（リマインダーなし）
        db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # /reminders を実行
        await bot_commands._handle_reminders(mock_interaction)

        # メッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "リマインダーがありません" in str(call_args)

    @pytest.mark.asyncio
    async def test_reminders_command_without_workspace(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-13: 未登録サーバーでの /reminders"""
        # /reminders を実行（Workspaceなし）
        await bot_commands._handle_reminders(mock_interaction)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "登録されていません" in str(call_args)

    @pytest.mark.asyncio
    async def test_reminders_command_pending_only(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-14: 未完了リマインダーのみ表示"""
        # Workspaceを作成
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # リマインダーを作成
        db.create_reminder(
            workspace_id=workspace.id,
            title="未完了タスク",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )
        done_reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="完了タスク",
            due_date=datetime.now(UTC) + timedelta(days=2),
        )
        db.update_reminder_status(done_reminder.id, "done")

        # /reminders を実行
        await bot_commands._handle_reminders(mock_interaction)

        # 未完了のみ表示
        call_kwargs = mock_interaction.followup.send.call_args.kwargs
        embed = call_kwargs["embed"]
        assert "1件" in embed.description


class TestTranscribeCommand:
    """/transcribe コマンドのテスト

    CMD-15 ~ CMD-18
    """

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_interaction(self):
        """モックInteraction"""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.id = 123456789
        return interaction

    @pytest.fixture
    def bot_commands(self, db):
        """BotCommandsインスタンス"""
        from src.bot.commands import BotCommands

        mock_tree = MagicMock()
        mock_router = MagicMock()
        return BotCommands(mock_tree, db, mock_router)

    @pytest.fixture
    def temp_audio_file(self, tmp_path):
        """テスト用音声ファイル"""
        audio_file = tmp_path / "test_audio.wav"
        audio_file.write_bytes(b"fake audio data")
        return audio_file

    @pytest.mark.asyncio
    async def test_transcribe_command_success(
        self, db: Database, mock_interaction, bot_commands, temp_audio_file, monkeypatch
    ) -> None:
        """CMD-15: /transcribe で文字起こし成功"""
        from unittest.mock import patch

        # Workspaceとセッションを作成
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")
        room = db.create_room(
            workspace_id=workspace.id,
            name="ボイスチャンネル",
            discord_channel_id="111222333",
            room_type="voice",
        )
        session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user1"],
        )
        # ファイルパスを設定
        db.update_voice_session_end(
            session.id,
            end_time=datetime.now(UTC),
            file_path=str(temp_audio_file),
        )

        # 環境変数を設定
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # WhisperProviderをモック
        mock_provider = AsyncMock()
        mock_provider.transcribe = AsyncMock(return_value="テスト文字起こし結果")

        with patch("src.bot.commands.WhisperProvider", return_value=mock_provider):
            # /transcribe を実行
            await bot_commands._handle_transcribe(mock_interaction, session.id)

        # 文字起こし結果がDBに保存されたことを確認
        updated_session = db.get_voice_session_by_id(session.id)
        assert updated_session is not None
        assert updated_session.transcription == "テスト文字起こし結果"

        # 成功メッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_kwargs = mock_interaction.followup.send.call_args.kwargs
        assert "embed" in call_kwargs
        embed = call_kwargs["embed"]
        assert "文字起こし" in embed.title

    @pytest.mark.asyncio
    async def test_transcribe_command_session_not_found(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-16: 存在しないセッションIDでの /transcribe"""
        # Workspaceを作成
        db.create_workspace(name="テストサーバー", discord_server_id="123456789")

        # 存在しないセッションIDで /transcribe を実行
        await bot_commands._handle_transcribe(mock_interaction, 99999)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "セッション" in str(call_args) and "見つかりません" in str(call_args)

    @pytest.mark.asyncio
    async def test_transcribe_command_no_audio_file(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-17: 音声ファイルがないセッションでの /transcribe"""
        # Workspaceとセッションを作成（file_pathなし）
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")
        room = db.create_room(
            workspace_id=workspace.id,
            name="ボイスチャンネル",
            discord_channel_id="111222333",
            room_type="voice",
        )
        session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user1"],
        )

        # /transcribe を実行
        await bot_commands._handle_transcribe(mock_interaction, session.id)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "音声ファイル" in str(call_args)

    @pytest.mark.asyncio
    async def test_transcribe_command_outside_guild(
        self, db: Database, mock_interaction, bot_commands
    ) -> None:
        """CMD-18: サーバー外（DM等）での /transcribe"""
        # guildをNoneに設定
        mock_interaction.guild = None

        # /transcribe を実行
        await bot_commands._handle_transcribe(mock_interaction, 1)

        # エラーメッセージが送信されたことを確認
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "サーバー内" in str(call_args)


class TestSaveCommand:
    """/save コマンドのテスト"""

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def storage(self, tmp_path: Path) -> LocalStorage:
        """ローカルストレージ"""
        return LocalStorage(base_path=tmp_path)

    @pytest.fixture
    def mock_interaction(self):
        """モックInteraction"""
        interaction = MagicMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.id = 123456789
        interaction.channel = MagicMock()
        interaction.channel.id = 987654321
        return interaction

    @pytest.fixture
    def bot_commands(self, db, storage):
        """BotCommandsインスタンス"""
        from src.bot.commands import BotCommands

        mock_tree = MagicMock()
        mock_router = MagicMock()
        drive_storage = AsyncMock()
        drive_storage.save_file_with_folder = AsyncMock(return_value=Path("drive-id"))
        return BotCommands(
            mock_tree,
            db,
            mock_router,
            storage=storage,
            drive_storage=drive_storage,
        )

    @pytest.mark.asyncio
    async def test_save_command_uploads_latest_attachment(
        self, db: Database, storage: LocalStorage, mock_interaction, bot_commands
    ) -> None:
        """CMD-19: /save で最新添付をDrive保存"""
        workspace = db.create_workspace(name="テストサーバー", discord_server_id="123456789")
        room = db.create_room(
            workspace_id=workspace.id,
            name="テストチャンネル",
            discord_channel_id="987654321",
            room_type="topic",
        )
        message = db.save_message(
            room_id=room.id,
            sender_name="tester",
            sender_id="123",
            content="file upload",
            message_type="text",
            discord_message_id="message-1",
        )
        file_path = await storage.save_file(
            content=b"dummy",
            workspace_id=workspace.id,
            room_id=room.id,
            filename="report.txt",
        )
        db.save_attachment(
            message_id=message.id,
            file_name="report.txt",
            file_path=str(file_path),
            file_type="document",
            file_size=5,
        )

        await bot_commands._handle_save(mock_interaction, "client-a")

        latest_attachment = db.get_latest_attachment_by_room(room.id)
        assert latest_attachment is not None
        assert latest_attachment.drive_path == "drive-id"

        drive_storage = bot_commands._drive_storage
        assert drive_storage is not None
        drive_storage.save_file_with_folder.assert_awaited_once()

        mock_interaction.followup.send.assert_called_once()
        call_kwargs = mock_interaction.followup.send.call_args.kwargs
        assert "embed" in call_kwargs

    @pytest.mark.asyncio
    async def test_save_command_without_drive_settings(
        self, db: Database, storage: LocalStorage, mock_interaction
    ) -> None:
        """CMD-20: Drive未設定時の /save"""
        from src.bot.commands import BotCommands

        mock_tree = MagicMock()
        mock_router = MagicMock()
        commands = BotCommands(mock_tree, db, mock_router, storage=storage, drive_storage=None)

        await commands._handle_save(mock_interaction, "client-a")

        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        assert "Google Drive" in str(call_args)
