"""VoiceRecorderのテスト

TEST_PLAN.md: VR-01 ~ VR-17
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.database import Database
from src.storage.local import LocalStorage


class TestVoiceRecorderError:
    """VoiceRecorderErrorのテスト"""

    def test_voice_recorder_error(self) -> None:
        """VR-01: VoiceRecorderError例外"""
        from src.bot.voice_recorder import VoiceRecorderError

        error = VoiceRecorderError("テストエラー")
        assert str(error) == "テストエラー"


class TestVoiceRecorder:
    """VoiceRecorderのテスト"""

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        # テスト用のWorkspaceとRoomを作成
        database.create_workspace(
            name="Test Workspace",
            discord_server_id="12345",
        )
        database.create_room(
            workspace_id=1,
            name="Test Room",
            discord_channel_id="67890",
            room_type="voice",
        )
        yield database
        database.close()

    @pytest.fixture
    def storage(self, tmp_path: Path):
        """テスト用ストレージ"""
        return LocalStorage(base_path=tmp_path)

    @pytest.fixture
    def voice_recorder(self, db: Database, storage: LocalStorage):
        """テスト用VoiceRecorder"""
        from src.bot.voice_recorder import VoiceRecorder

        return VoiceRecorder(db, storage)

    def test_voice_recorder_init(self, voice_recorder) -> None:
        """VR-02: VoiceRecorderの初期化"""
        assert voice_recorder._active_recordings == {}

    def test_is_recording_false(self, voice_recorder) -> None:
        """VR-03: 録音していない状態"""
        assert voice_recorder.is_recording(12345) is False

    def test_is_recording_true(self, voice_recorder) -> None:
        """VR-04: 録音中の状態"""
        voice_recorder._active_recordings[12345] = {"test": "data"}
        assert voice_recorder.is_recording(12345) is True

    def test_get_recording_info_none(self, voice_recorder) -> None:
        """VR-05: 録音情報がない場合"""
        assert voice_recorder.get_recording_info(12345) is None

    def test_get_recording_info_exists(self, voice_recorder) -> None:
        """VR-06: 録音情報がある場合"""
        info = {"session_id": 1, "start_time": datetime.now(UTC)}
        voice_recorder._active_recordings[12345] = info
        assert voice_recorder.get_recording_info(12345) == info

    def test_add_participant(self, voice_recorder) -> None:
        """VR-07: 参加者追加"""
        voice_recorder._active_recordings[12345] = {"participants": set()}
        voice_recorder.add_participant(12345, "user1")
        assert "user1" in voice_recorder._active_recordings[12345]["participants"]

    def test_add_participant_no_recording(self, voice_recorder) -> None:
        """VR-08: 録音なしで参加者追加（エラーなし）"""
        # 録音がない場合は何もしない
        voice_recorder.add_participant(12345, "user1")
        # エラーが発生しないことを確認

    def test_remove_participant(self, voice_recorder) -> None:
        """VR-09: 参加者削除"""
        voice_recorder._active_recordings[12345] = {"participants": {"user1", "user2"}}
        voice_recorder.remove_participant(12345, "user1")
        assert "user1" not in voice_recorder._active_recordings[12345]["participants"]
        assert "user2" in voice_recorder._active_recordings[12345]["participants"]

    def test_remove_participant_no_recording(self, voice_recorder) -> None:
        """VR-10: 録音なしで参加者削除（エラーなし）"""
        voice_recorder.remove_participant(12345, "user1")
        # エラーが発生しないことを確認


class TestRecordCommand:
    """/record コマンドのテスト"""

    @pytest.fixture
    def db(self):
        """テスト用データベース"""
        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_tree(self):
        """モックCommandTree"""
        return MagicMock()

    @pytest.fixture
    def mock_router(self):
        """モックAIRouter"""
        return MagicMock()

    @pytest.fixture
    def mock_voice_recorder(self):
        """モックVoiceRecorder"""
        recorder = MagicMock()
        recorder.is_recording.return_value = False
        recorder.start_recording = AsyncMock(return_value=1)
        recorder.stop_recording = AsyncMock(return_value=Path("/test/recording.wav"))
        return recorder

    def test_bot_commands_with_voice_recorder(
        self, mock_tree, db, mock_router, mock_voice_recorder
    ) -> None:
        """VR-11: BotCommandsにVoiceRecorder設定"""
        from src.bot.commands import BotCommands

        commands = BotCommands(mock_tree, db, mock_router, mock_voice_recorder)
        assert commands._voice_recorder is mock_voice_recorder

    def test_bot_commands_without_voice_recorder(self, mock_tree, db, mock_router) -> None:
        """VR-12: VoiceRecorderなしでBotCommands作成"""
        from src.bot.commands import BotCommands

        commands = BotCommands(mock_tree, db, mock_router)
        assert commands._voice_recorder is None

    @pytest.mark.asyncio
    async def test_handle_record_no_voice_recorder(self, mock_tree, db, mock_router) -> None:
        """VR-13: VoiceRecorderなしでの録音コマンド"""
        from src.bot.commands import BotCommands

        commands = BotCommands(mock_tree, db, mock_router, None)

        # モックInteraction
        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.guild = MagicMock()

        await commands._handle_record(interaction, "on")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "利用できません" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_record_no_guild(
        self, mock_tree, db, mock_router, mock_voice_recorder
    ) -> None:
        """VR-14: サーバー外での録音コマンド"""
        from src.bot.commands import BotCommands

        commands = BotCommands(mock_tree, db, mock_router, mock_voice_recorder)

        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.guild = None

        await commands._handle_record(interaction, "on")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "サーバー内" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_record_no_workspace(
        self, mock_tree, db, mock_router, mock_voice_recorder
    ) -> None:
        """VR-15: 未登録サーバーでの録音コマンド"""
        from src.bot.commands import BotCommands

        commands = BotCommands(mock_tree, db, mock_router, mock_voice_recorder)

        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.guild = MagicMock()
        interaction.guild.id = 12345
        interaction.user = MagicMock()

        await commands._handle_record(interaction, "on")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "登録されていません" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_record_off_not_recording(
        self, mock_tree, db, mock_router, mock_voice_recorder
    ) -> None:
        """VR-16: 録音していない状態でのoff"""
        from src.bot.commands import BotCommands

        # Workspaceを登録
        db.create_workspace(name="Test", discord_server_id="12345")

        commands = BotCommands(mock_tree, db, mock_router, mock_voice_recorder)

        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.guild = MagicMock()
        interaction.guild.id = 12345

        await commands._handle_record(interaction, "off")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "録音していません" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_record_on_not_in_voice(
        self, mock_tree, db, mock_router, mock_voice_recorder
    ) -> None:
        """VR-17: ボイスチャンネル未接続での録音開始"""
        from src.bot.commands import BotCommands

        # Workspaceを登録
        db.create_workspace(name="Test", discord_server_id="12345")

        commands = BotCommands(mock_tree, db, mock_router, mock_voice_recorder)

        interaction = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        interaction.guild = MagicMock()
        interaction.guild.id = 12345
        # ユーザーがボイスチャンネルに接続していない
        interaction.user = MagicMock()
        interaction.user.voice = None

        await commands._handle_record(interaction, "on")

        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "ボイスチャンネルに接続" in call_args[0][0]
