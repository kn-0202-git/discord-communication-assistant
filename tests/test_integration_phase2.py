"""Phase 2 統合テスト（正常系）

Phase 2で実装した機能の統合テスト:
- リマインダー機能 (Issue #18-21)
- 通話録音・文字起こし機能 (Issue #30-33)
- 技術課題対応 (Issue #15-17)

TEST_PLAN.md で定義されたテストケース:
- P2-INT-01: test_reminder_creation_and_notification - リマインダー作成→通知フロー
- P2-INT-02: test_reminder_notification_filtering - 期限内/期限外フィルタリング
- P2-INT-03: test_reminder_notifier_integration - ReminderNotifier統合
- P2-INT-04: test_voice_recording_lifecycle - 録音ライフサイクル
- P2-INT-05: test_voice_session_transcription_flow - 録音→文字起こしフロー
- P2-INT-06: test_transcription_with_whisper - WhisperProvider統合
- P2-INT-07: test_reminder_and_voice_coexistence - 両機能の同時動作
- P2-INT-08: test_reminder_status_transitions - ステータス遷移
- P2-INT-09: test_voice_session_multiple_rooms - 複数Room録音管理
- P2-INT-10: test_reminder_notification_to_correct_room - 正しいRoomへの通知
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

if TYPE_CHECKING:
    from src.db.database import Database
    from src.storage.local import LocalStorage


class TestReminderIntegration:
    """リマインダー機能の統合テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_bot(self) -> MagicMock:
        """Discord Botモック"""
        bot = MagicMock(spec=discord.Client)
        channel = MagicMock(spec=discord.TextChannel)
        channel.send = AsyncMock()
        bot.get_channel.return_value = channel
        return bot

    @pytest.fixture
    def workspace_with_aggregation(self, db: "Database") -> tuple:
        """統合Room付きWorkspaceセットアップ"""
        ws = db.create_workspace(name="Test Workspace", discord_server_id="guild123")
        topic_room = db.create_room(
            workspace_id=ws.id,
            name="Topic Room",
            discord_channel_id="123456789",
            room_type="topic",
        )
        agg_room = db.create_room(
            workspace_id=ws.id,
            name="Aggregation",
            discord_channel_id="987654321",
            room_type="aggregation",
        )
        db.create_room_link(
            source_room_id=topic_room.id,
            target_room_id=agg_room.id,
            link_type="one_way",
        )
        return ws, topic_room, agg_room

    # P2-INT-01: リマインダー作成→通知フロー
    @pytest.mark.asyncio
    async def test_reminder_creation_and_notification(
        self,
        db: "Database",
        mock_bot: MagicMock,
        workspace_with_aggregation: tuple,
    ) -> None:
        """リマインダー作成→DB保存→期限通知→統合Roomへ送信の一連のフロー"""
        from src.bot.notifier import ReminderNotifier

        ws, topic_room, agg_room = workspace_with_aggregation

        # 1. リマインダーを作成（1時間後の期限）
        due_date = datetime.now(UTC) + timedelta(hours=1)
        reminder = db.create_reminder(
            workspace_id=ws.id,
            title="テストリマインダー",
            due_date=due_date,
            description="テスト用の説明",
        )

        # 2. DBに保存されていることを確認
        assert reminder.id is not None
        assert reminder.status == "pending"
        assert reminder.notified is False

        # 3. ReminderNotifierで通知をチェック（24時間以内なので通知される）
        notifier = ReminderNotifier(
            db=db,
            bot=mock_bot,
            hours_ahead=24,  # 24時間以内のリマインダーを通知
        )
        notified_count = await notifier.check_and_notify()

        # 4. 通知が送信されたことを確認
        assert notified_count == 1
        mock_bot.get_channel.assert_called_with(int(agg_room.discord_channel_id))
        channel = mock_bot.get_channel.return_value
        channel.send.assert_called_once()

        # 5. notifiedフラグが更新されていることを確認
        updated_reminder = db.get_reminder_by_id(reminder.id)
        assert updated_reminder is not None
        assert updated_reminder.notified is True

    # P2-INT-02: 期限内/期限外フィルタリング
    @pytest.mark.asyncio
    async def test_reminder_notification_filtering(
        self,
        db: "Database",
        mock_bot: MagicMock,
        workspace_with_aggregation: tuple,
    ) -> None:
        """複数リマインダーで期限内/期限外のフィルタリングが正しく動作"""
        from src.bot.notifier import ReminderNotifier

        ws, topic_room, agg_room = workspace_with_aggregation

        # 期限内のリマインダー（12時間後）
        due_soon = datetime.now(UTC) + timedelta(hours=12)
        reminder_soon = db.create_reminder(
            workspace_id=ws.id,
            title="期限近いリマインダー",
            due_date=due_soon,
        )

        # 期限外のリマインダー（48時間後）
        due_later = datetime.now(UTC) + timedelta(hours=48)
        reminder_later = db.create_reminder(
            workspace_id=ws.id,
            title="期限遠いリマインダー",
            due_date=due_later,
        )

        # 24時間以内のリマインダーのみ通知
        notifier = ReminderNotifier(db=db, bot=mock_bot, hours_ahead=24)
        notified_count = await notifier.check_and_notify()

        # 期限内のリマインダーのみ通知される
        assert notified_count == 1

        # 期限内のリマインダーは通知済み
        updated_soon = db.get_reminder_by_id(reminder_soon.id)
        assert updated_soon is not None
        assert updated_soon.notified is True

        # 期限外のリマインダーは未通知
        updated_later = db.get_reminder_by_id(reminder_later.id)
        assert updated_later is not None
        assert updated_later.notified is False

    # P2-INT-03: ReminderNotifier統合
    @pytest.mark.asyncio
    async def test_reminder_notifier_integration(
        self,
        db: "Database",
        mock_bot: MagicMock,
        workspace_with_aggregation: tuple,
    ) -> None:
        """ReminderNotifierがBot・Databaseと正しく連携して通知"""
        from src.bot.notifier import ReminderNotifier

        ws, topic_room, agg_room = workspace_with_aggregation

        # 複数のリマインダーを作成
        for i in range(3):
            due_date = datetime.now(UTC) + timedelta(hours=i + 1)
            db.create_reminder(
                workspace_id=ws.id,
                title=f"リマインダー{i + 1}",
                due_date=due_date,
            )

        notifier = ReminderNotifier(db=db, bot=mock_bot, hours_ahead=24)
        notified_count = await notifier.check_and_notify()

        # 3つ全て通知される
        assert notified_count == 3

        # 統合Roomに3回送信された
        channel = mock_bot.get_channel.return_value
        assert channel.send.call_count == 3

    # P2-INT-08: ステータス遷移
    def test_reminder_status_transitions(
        self,
        db: "Database",
        workspace_with_aggregation: tuple,
    ) -> None:
        """リマインダーのステータス遷移（pending→done/cancelled）が正しく動作"""
        ws, topic_room, agg_room = workspace_with_aggregation

        # リマインダーを作成
        due_date = datetime.now(UTC) + timedelta(hours=1)
        reminder = db.create_reminder(
            workspace_id=ws.id,
            title="ステータステスト",
            due_date=due_date,
        )
        assert reminder.status == "pending"

        # pending → done
        updated = db.update_reminder_status(reminder.id, "done")
        assert updated.status == "done"

        # done → cancelled（ステータスは変更可能）
        updated = db.update_reminder_status(reminder.id, "cancelled")
        assert updated.status == "cancelled"

        # get_pending_remindersには含まれない
        pending = db.get_pending_reminders(hours_ahead=24)
        assert len([r for r in pending if r.id == reminder.id]) == 0

    # P2-INT-10: 正しいWorkspaceの統合Roomへ通知
    @pytest.mark.asyncio
    async def test_reminder_notification_to_correct_room(
        self,
        db: "Database",
        mock_bot: MagicMock,
    ) -> None:
        """リマインダー通知が正しいWorkspaceの統合Roomに届く"""
        from src.bot.notifier import ReminderNotifier

        # Workspace A を作成
        ws_a = db.create_workspace(name="Workspace A", discord_server_id="guild_a")
        db.create_room(
            workspace_id=ws_a.id,
            name="Topic A",
            discord_channel_id="111111111",
            room_type="topic",
        )
        agg_a = db.create_room(
            workspace_id=ws_a.id,
            name="Aggregation A",
            discord_channel_id="222222222",
            room_type="aggregation",
        )

        # Workspace B を作成
        ws_b = db.create_workspace(name="Workspace B", discord_server_id="guild_b")
        db.create_room(
            workspace_id=ws_b.id,
            name="Topic B",
            discord_channel_id="333333333",
            room_type="topic",
        )
        agg_b = db.create_room(
            workspace_id=ws_b.id,
            name="Aggregation B",
            discord_channel_id="444444444",
            room_type="aggregation",
        )

        # Workspace A にリマインダーを作成
        due_date = datetime.now(UTC) + timedelta(hours=1)
        db.create_reminder(
            workspace_id=ws_a.id,
            title="Workspace Aのリマインダー",
            due_date=due_date,
        )

        # チャンネルモックを設定
        channel_a = MagicMock(spec=discord.TextChannel)
        channel_a.send = AsyncMock()
        channel_b = MagicMock(spec=discord.TextChannel)
        channel_b.send = AsyncMock()

        def get_channel(channel_id: int) -> MagicMock:
            if channel_id == int(agg_a.discord_channel_id):
                return channel_a
            if channel_id == int(agg_b.discord_channel_id):
                return channel_b
            return MagicMock()

        mock_bot.get_channel.side_effect = get_channel

        notifier = ReminderNotifier(db=db, bot=mock_bot, hours_ahead=24)
        await notifier.check_and_notify()

        # Workspace A の統合Roomにのみ通知
        channel_a.send.assert_called_once()
        channel_b.send.assert_not_called()


class TestVoiceRecordingIntegration:
    """通話録音・文字起こし機能の統合テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_storage(self, tmp_path: Path) -> "LocalStorage":
        """テスト用ストレージ"""
        from src.storage.local import LocalStorage

        storage = LocalStorage(base_path=tmp_path)
        return storage

    @pytest.fixture
    def workspace_with_voice(self, db: "Database") -> tuple:
        """VoiceRoom付きWorkspaceセットアップ"""
        ws = db.create_workspace(name="Voice Workspace", discord_server_id="voice_guild")
        voice_room = db.create_room(
            workspace_id=ws.id,
            name="Voice Room",
            discord_channel_id="voice_channel_123",
            room_type="topic",
        )
        return ws, voice_room

    # P2-INT-04: 録音ライフサイクル
    @pytest.mark.asyncio
    async def test_voice_recording_lifecycle(
        self,
        db: "Database",
        mock_storage: MagicMock,
        workspace_with_voice: tuple,
    ) -> None:
        """録音開始→DB作成→停止→ファイル保存→DB更新"""
        from src.bot.voice_recorder import VoiceRecorder

        ws, voice_room = workspace_with_voice

        recorder = VoiceRecorder(db=db, storage=mock_storage)

        # VoiceChannelモック
        mock_voice_channel = MagicMock(spec=discord.VoiceChannel)
        mock_voice_channel.guild.id = int(ws.discord_server_id.replace("voice_guild", "12345"))
        mock_voice_channel.id = 67890
        mock_voice_channel.name = "Test Voice Channel"
        mock_voice_channel.members = []

        # VoiceClientモック
        mock_voice_client = MagicMock(spec=discord.VoiceClient)
        mock_voice_client.disconnect = AsyncMock()
        mock_voice_channel.connect = AsyncMock(return_value=mock_voice_client)

        # 1. 録音開始
        session_id = await recorder.start_recording(
            voice_channel=mock_voice_channel,
            room_id=voice_room.id,
            workspace_id=ws.id,
        )

        # 2. DBにVoiceSessionが作成されている
        voice_session = db.get_voice_session_by_id(session_id)
        assert voice_session is not None
        assert voice_session.room_id == voice_room.id
        assert voice_session.end_time is None
        assert voice_session.file_path is None

        # 3. 録音中かどうかを確認
        assert recorder.is_recording(mock_voice_channel.guild.id) is True

        # 4. 録音停止
        file_path = await recorder.stop_recording(mock_voice_channel.guild.id)

        # 5. ファイルが保存されている
        assert file_path.exists()
        assert file_path.suffix == ".wav"

        # 6. DBが更新されている
        updated_session = db.get_voice_session_by_id(session_id)
        assert updated_session is not None
        assert updated_session.end_time is not None
        assert updated_session.file_path is not None

        # 7. 録音が停止している
        assert recorder.is_recording(mock_voice_channel.guild.id) is False

    # P2-INT-05: 録音→文字起こしフロー
    @pytest.mark.asyncio
    async def test_voice_session_transcription_flow(
        self,
        db: "Database",
        mock_storage: MagicMock,
        workspace_with_voice: tuple,
    ) -> None:
        """録音→文字起こし→DB保存の全フロー"""
        from src.bot.voice_recorder import VoiceRecorder

        ws, voice_room = workspace_with_voice

        recorder = VoiceRecorder(db=db, storage=mock_storage)

        # VoiceChannelモック
        mock_voice_channel = MagicMock(spec=discord.VoiceChannel)
        mock_voice_channel.guild.id = 12345
        mock_voice_channel.id = 67890
        mock_voice_channel.name = "Transcription Test Channel"
        mock_voice_channel.members = []

        mock_voice_client = MagicMock(spec=discord.VoiceClient)
        mock_voice_client.disconnect = AsyncMock()
        mock_voice_channel.connect = AsyncMock(return_value=mock_voice_client)

        # 1. 録音を完了させる
        session_id = await recorder.start_recording(
            voice_channel=mock_voice_channel,
            room_id=voice_room.id,
            workspace_id=ws.id,
        )
        file_path = await recorder.stop_recording(mock_voice_channel.guild.id)

        # 2. 音声ファイルを読み込む
        audio_data = file_path.read_bytes()
        assert len(audio_data) > 0

        # 3. 文字起こし（WhisperProviderモック）
        transcription_text = "これはテストの文字起こし結果です。"

        with patch("src.ai.transcription.whisper.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.audio.transcriptions.create = AsyncMock(return_value=transcription_text)

            from src.ai.transcription.whisper import WhisperProvider

            provider = WhisperProvider(api_key="test-key")
            result = await provider.transcribe(audio_data, language="ja")

            assert result == transcription_text

        # 4. DBに文字起こし結果を保存
        db.update_voice_session_transcription(session_id, transcription_text)

        # 5. DBが更新されていることを確認
        updated_session = db.get_voice_session_by_id(session_id)
        assert updated_session is not None
        assert updated_session.transcription == transcription_text

    # P2-INT-06: WhisperProvider統合
    @pytest.mark.asyncio
    async def test_transcription_with_whisper(self) -> None:
        """WhisperProviderの統合テスト"""
        # モックデータ
        audio_data = b"\x00" * 1000  # ダミー音声データ
        expected_text = "Whisperテストの文字起こし結果"

        with patch("src.ai.transcription.whisper.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.audio.transcriptions.create = AsyncMock(return_value=expected_text)

            from src.ai.transcription.whisper import WhisperProvider

            provider = WhisperProvider(api_key="test-key", model="whisper-1")

            # プロパティ確認
            assert provider.name == "openai"
            assert provider.model == "whisper-1"

            # 文字起こし実行
            result = await provider.transcribe(
                audio=audio_data,
                language="ja",
                prompt="技術会議の録音です",
            )

            assert result == expected_text
            mock_client.audio.transcriptions.create.assert_called_once()

    # P2-INT-09: 複数Room同時録音管理
    @pytest.mark.asyncio
    async def test_voice_session_multiple_rooms(
        self,
        db: "Database",
        mock_storage: MagicMock,
    ) -> None:
        """複数のRoomで同時に録音セッションが管理できる"""
        from src.bot.voice_recorder import VoiceRecorder

        # 2つのWorkspace/Roomを作成
        ws1 = db.create_workspace(name="Workspace 1", discord_server_id="guild_1")
        room1 = db.create_room(
            workspace_id=ws1.id,
            name="Voice Room 1",
            discord_channel_id="channel_1",
            room_type="topic",
        )

        ws2 = db.create_workspace(name="Workspace 2", discord_server_id="guild_2")
        room2 = db.create_room(
            workspace_id=ws2.id,
            name="Voice Room 2",
            discord_channel_id="channel_2",
            room_type="topic",
        )

        recorder = VoiceRecorder(db=db, storage=mock_storage)

        # Guild 1 のVoiceChannelモック
        mock_channel_1 = MagicMock(spec=discord.VoiceChannel)
        mock_channel_1.guild.id = 11111
        mock_channel_1.id = 22222
        mock_channel_1.name = "Voice 1"
        mock_channel_1.members = []
        mock_client_1 = MagicMock(spec=discord.VoiceClient)
        mock_client_1.disconnect = AsyncMock()
        mock_channel_1.connect = AsyncMock(return_value=mock_client_1)

        # Guild 2 のVoiceChannelモック
        mock_channel_2 = MagicMock(spec=discord.VoiceChannel)
        mock_channel_2.guild.id = 33333
        mock_channel_2.id = 44444
        mock_channel_2.name = "Voice 2"
        mock_channel_2.members = []
        mock_client_2 = MagicMock(spec=discord.VoiceClient)
        mock_client_2.disconnect = AsyncMock()
        mock_channel_2.connect = AsyncMock(return_value=mock_client_2)

        # 両方で録音開始
        session_id_1 = await recorder.start_recording(
            voice_channel=mock_channel_1,
            room_id=room1.id,
            workspace_id=ws1.id,
        )
        session_id_2 = await recorder.start_recording(
            voice_channel=mock_channel_2,
            room_id=room2.id,
            workspace_id=ws2.id,
        )

        # 両方とも録音中
        assert recorder.is_recording(mock_channel_1.guild.id) is True
        assert recorder.is_recording(mock_channel_2.guild.id) is True

        # Guild 1 のみ停止
        await recorder.stop_recording(mock_channel_1.guild.id)

        # Guild 1 は停止、Guild 2 は録音中
        assert recorder.is_recording(mock_channel_1.guild.id) is False
        assert recorder.is_recording(mock_channel_2.guild.id) is True

        # VoiceSessionが別々に管理されている
        session_1 = db.get_voice_session_by_id(session_id_1)
        session_2 = db.get_voice_session_by_id(session_id_2)

        assert session_1 is not None
        assert session_2 is not None
        assert session_1.room_id == room1.id
        assert session_2.room_id == room2.id
        assert session_1.end_time is not None  # 停止済み
        assert session_2.end_time is None  # まだ録音中

        # 後片付け
        await recorder.stop_recording(mock_channel_2.guild.id)


class TestCoexistenceIntegration:
    """リマインダーと録音機能の共存テスト"""

    @pytest.fixture
    def db(self) -> Generator["Database", None, None]:
        """テスト用データベース"""
        from src.db.database import Database

        database = Database(":memory:")
        database.create_tables()
        yield database
        database.close()

    @pytest.fixture
    def mock_storage(self, tmp_path: Path) -> "LocalStorage":
        """テスト用ストレージ"""
        from src.storage.local import LocalStorage

        storage = LocalStorage(base_path=tmp_path)
        return storage

    # P2-INT-07: 両機能の同時動作
    @pytest.mark.asyncio
    async def test_reminder_and_voice_coexistence(
        self,
        db: "Database",
        mock_storage: MagicMock,
    ) -> None:
        """リマインダーと録音機能が同時に動作しても干渉しない"""
        from src.bot.notifier import ReminderNotifier
        from src.bot.voice_recorder import VoiceRecorder

        # Workspaceを作成
        ws = db.create_workspace(name="Coexistence Test", discord_server_id="guild_coexist")
        voice_room = db.create_room(
            workspace_id=ws.id,
            name="Voice Room",
            discord_channel_id="555555555",
            room_type="topic",
        )
        db.create_room(
            workspace_id=ws.id,
            name="Aggregation",
            discord_channel_id="666666666",
            room_type="aggregation",
        )

        # リマインダーを作成
        due_date = datetime.now(UTC) + timedelta(hours=1)
        reminder = db.create_reminder(
            workspace_id=ws.id,
            title="共存テストリマインダー",
            due_date=due_date,
        )

        # 録音を開始
        recorder = VoiceRecorder(db=db, storage=mock_storage)
        mock_voice_channel = MagicMock(spec=discord.VoiceChannel)
        mock_voice_channel.guild.id = 99999
        mock_voice_channel.id = 88888
        mock_voice_channel.name = "Coexist Voice"
        mock_voice_channel.members = []
        mock_voice_client = MagicMock(spec=discord.VoiceClient)
        mock_voice_client.disconnect = AsyncMock()
        mock_voice_channel.connect = AsyncMock(return_value=mock_voice_client)

        session_id = await recorder.start_recording(
            voice_channel=mock_voice_channel,
            room_id=voice_room.id,
            workspace_id=ws.id,
        )

        # リマインダー通知を実行
        mock_bot = MagicMock(spec=discord.Client)
        channel = MagicMock(spec=discord.TextChannel)
        channel.send = AsyncMock()
        mock_bot.get_channel.return_value = channel

        notifier = ReminderNotifier(db=db, bot=mock_bot, hours_ahead=24)
        notified_count = await notifier.check_and_notify()

        # リマインダー通知は正常に動作
        assert notified_count == 1

        # 録音は引き続き動作中
        assert recorder.is_recording(mock_voice_channel.guild.id) is True

        # 録音を停止
        await recorder.stop_recording(mock_voice_channel.guild.id)

        # 両方のデータが正しく保存されている
        updated_reminder = db.get_reminder_by_id(reminder.id)
        assert updated_reminder is not None
        assert updated_reminder.notified is True

        voice_session = db.get_voice_session_by_id(session_id)
        assert voice_session is not None
        assert voice_session.end_time is not None
