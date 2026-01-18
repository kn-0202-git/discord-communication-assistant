"""Database model tests.

TEST_PLAN.md: DB-01 ~ DB-08
"""

import pytest

from src.db.database import Database


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = Database(":memory:")
    database.create_tables()
    yield database
    database.close()


class TestWorkspace:
    """Workspace model tests."""

    def test_create_workspace(self, db: Database) -> None:
        """DB-01: Workspace作成."""
        workspace = db.create_workspace(
            name="A社",
            discord_server_id="123456789",
        )

        assert workspace.id is not None
        assert workspace.name == "A社"
        assert workspace.discord_server_id == "123456789"
        assert workspace.created_at is not None

    def test_create_workspace_with_ai_config(self, db: Database) -> None:
        """Workspace作成（AI設定あり）."""
        ai_config = {"summary": {"provider": "google", "model": "gemini-1.5-flash"}}
        workspace = db.create_workspace(
            name="B社",
            discord_server_id="987654321",
            ai_config=ai_config,
        )

        assert workspace.ai_config == ai_config


class TestRoom:
    """Room model tests."""

    def test_create_room(self, db: Database) -> None:
        """DB-02: Room作成."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")

        room = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_123",
            room_type="topic",
        )

        assert room.id is not None
        assert room.workspace_id == workspace.id
        assert room.name == "技術相談"
        assert room.discord_channel_id == "channel_123"
        assert room.room_type == "topic"

    def test_create_aggregation_room(self, db: Database) -> None:
        """統合Room作成."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")

        room = db.create_room(
            workspace_id=workspace.id,
            name="統合Room",
            discord_channel_id="channel_456",
            room_type="aggregation",
        )

        assert room.room_type == "aggregation"

    def test_update_room_type(self, db: Database) -> None:
        """Room種別の更新."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")

        room = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_123",
            room_type="topic",
        )

        updated = db.update_room_type(room.id, "aggregation")

        assert updated is not None
        assert updated.room_type == "aggregation"
        assert db.get_room_by_id(room.id).room_type == "aggregation"


class TestMessage:
    """Message model tests."""

    def test_save_message(self, db: Database) -> None:
        """DB-03: メッセージ保存."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_123",
            room_type="topic",
        )

        message = db.save_message(
            room_id=room.id,
            sender_name="田中",
            sender_id="user_123",
            content="製品Xが変色しています",
            message_type="text",
            discord_message_id="msg_123",
        )

        assert message.id is not None
        assert message.room_id == room.id
        assert message.sender_name == "田中"
        assert message.content == "製品Xが変色しています"
        assert message.message_type == "text"
        assert message.timestamp is not None

    def test_save_message_with_attachment(self, db: Database) -> None:
        """DB-04: 添付ファイル付きメッセージ保存."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_123",
            room_type="topic",
        )

        message = db.save_message(
            room_id=room.id,
            sender_name="田中",
            sender_id="user_123",
            content="写真を添付します",
            message_type="image",
            discord_message_id="msg_124",
        )

        attachment = db.save_attachment(
            message_id=message.id,
            file_name="photo.jpg",
            file_path="/data/files/1/channel_123/2025-01-01/photo.jpg",
            file_type="image",
            file_size=1024000,
        )

        assert attachment.id is not None
        assert attachment.message_id == message.id
        assert attachment.file_name == "photo.jpg"
        assert attachment.file_type == "image"

    def test_get_messages_by_room(self, db: Database) -> None:
        """DB-05: Room別メッセージ取得."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_1",
            room_type="topic",
        )
        room2 = db.create_room(
            workspace_id=workspace.id,
            name="事務連絡",
            discord_channel_id="channel_2",
            room_type="topic",
        )

        # Room1にメッセージを2件保存
        db.save_message(
            room_id=room1.id,
            sender_name="田中",
            sender_id="user_1",
            content="メッセージ1",
            message_type="text",
            discord_message_id="msg_1",
        )
        db.save_message(
            room_id=room1.id,
            sender_name="佐藤",
            sender_id="user_2",
            content="メッセージ2",
            message_type="text",
            discord_message_id="msg_2",
        )

        # Room2にメッセージを1件保存
        db.save_message(
            room_id=room2.id,
            sender_name="鈴木",
            sender_id="user_3",
            content="メッセージ3",
            message_type="text",
            discord_message_id="msg_3",
        )

        # Room1のメッセージのみ取得
        messages = db.get_messages_by_room(room1.id)
        assert len(messages) == 2
        assert all(m.room_id == room1.id for m in messages)

    def test_search_messages_in_workspace(self, db: Database) -> None:
        """DB-06: Workspace内検索."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_1",
            room_type="topic",
        )

        db.save_message(
            room_id=room.id,
            sender_name="田中",
            sender_id="user_1",
            content="製品Xが変色しています",
            message_type="text",
            discord_message_id="msg_1",
        )
        db.save_message(
            room_id=room.id,
            sender_name="佐藤",
            sender_id="user_2",
            content="製品Yは正常です",
            message_type="text",
            discord_message_id="msg_2",
        )

        # 「変色」で検索
        results = db.search_messages(workspace.id, "変色")
        assert len(results) == 1
        assert "変色" in results[0].content


class TestWorkspaceIsolation:
    """Workspace isolation tests."""

    def test_workspace_isolation(self, db: Database) -> None:
        """DB-07: Workspace A↔B分離."""
        # Workspace AとBを作成
        workspace_a = db.create_workspace(name="A社", discord_server_id="server_a")
        workspace_b = db.create_workspace(name="B社", discord_server_id="server_b")

        room_a = db.create_room(
            workspace_id=workspace_a.id,
            name="A社技術相談",
            discord_channel_id="channel_a",
            room_type="topic",
        )
        room_b = db.create_room(
            workspace_id=workspace_b.id,
            name="B社技術相談",
            discord_channel_id="channel_b",
            room_type="topic",
        )

        # 各Workspaceにメッセージを保存
        db.save_message(
            room_id=room_a.id,
            sender_name="A社田中",
            sender_id="user_a",
            content="A社の機密情報",
            message_type="text",
            discord_message_id="msg_a",
        )
        db.save_message(
            room_id=room_b.id,
            sender_name="B社佐藤",
            sender_id="user_b",
            content="B社の機密情報",
            message_type="text",
            discord_message_id="msg_b",
        )

        # Workspace Aから検索 → Aのメッセージのみ
        results_a = db.search_messages(workspace_a.id, "機密情報")
        assert len(results_a) == 1
        assert "A社" in results_a[0].content

        # Workspace Bから検索 → Bのメッセージのみ
        results_b = db.search_messages(workspace_b.id, "機密情報")
        assert len(results_b) == 1
        assert "B社" in results_b[0].content


class TestRoomLink:
    """Room link tests."""

    def test_room_link(self, db: Database) -> None:
        """DB-08: Room間情報共有設定."""
        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="技術相談",
            discord_channel_id="channel_1",
            room_type="topic",
        )
        room2 = db.create_room(
            workspace_id=workspace.id,
            name="事務連絡",
            discord_channel_id="channel_2",
            room_type="topic",
        )
        aggregation_room = db.create_room(
            workspace_id=workspace.id,
            name="統合Room",
            discord_channel_id="channel_agg",
            room_type="aggregation",
        )

        # Room1とRoom2から統合Roomへのリンクを作成
        link1 = db.create_room_link(
            source_room_id=room1.id,
            target_room_id=aggregation_room.id,
            link_type="one_way",
        )
        link2 = db.create_room_link(
            source_room_id=room2.id,
            target_room_id=aggregation_room.id,
            link_type="one_way",
        )

        assert link1.id is not None
        assert link2.id is not None
        assert link1.source_room_id == room1.id
        assert link1.target_room_id == aggregation_room.id
        assert link1.link_type == "one_way"

        # リンク先の取得
        linked_rooms = db.get_linked_rooms(aggregation_room.id)
        assert len(linked_rooms) == 2


class TestReminder:
    """Reminder model tests."""

    def test_create_reminder(self, db: Database) -> None:
        """DB-09: リマインダー作成."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        due_date = datetime.now(UTC) + timedelta(days=1)

        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="納品締め切り",
            due_date=due_date,
            description="製品Xの納品日",
        )

        assert reminder.id is not None
        assert reminder.workspace_id == workspace.id
        assert reminder.title == "納品締め切り"
        assert reminder.description == "製品Xの納品日"
        # SQLiteはタイムゾーン情報を保存しないため、日時の値のみ比較
        assert reminder.due_date.replace(tzinfo=None) == due_date.replace(tzinfo=None)
        assert reminder.status == "pending"
        assert reminder.notified is False

    def test_create_reminder_without_description(self, db: Database) -> None:
        """リマインダー作成（説明なし）."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        due_date = datetime.now(UTC) + timedelta(hours=3)

        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="会議",
            due_date=due_date,
        )

        assert reminder.description is None

    def test_get_reminders_by_workspace(self, db: Database) -> None:
        """DB-10: Workspace内リマインダー一覧取得."""
        from datetime import UTC, datetime, timedelta

        workspace_a = db.create_workspace(name="A社", discord_server_id="server_a")
        workspace_b = db.create_workspace(name="B社", discord_server_id="server_b")

        # A社に2件
        db.create_reminder(
            workspace_id=workspace_a.id,
            title="A社タスク1",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )
        db.create_reminder(
            workspace_id=workspace_a.id,
            title="A社タスク2",
            due_date=datetime.now(UTC) + timedelta(days=2),
        )

        # B社に1件
        db.create_reminder(
            workspace_id=workspace_b.id,
            title="B社タスク",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )

        # A社のリマインダーのみ取得
        reminders_a = db.get_reminders_by_workspace(workspace_a.id)
        assert len(reminders_a) == 2
        assert all(r.workspace_id == workspace_a.id for r in reminders_a)

        # B社のリマインダーのみ取得
        reminders_b = db.get_reminders_by_workspace(workspace_b.id)
        assert len(reminders_b) == 1

    def test_get_pending_reminders(self, db: Database) -> None:
        """DB-11: 期限が近いリマインダー取得."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")

        # 期限が1時間後（通知対象）
        db.create_reminder(
            workspace_id=workspace.id,
            title="急ぎタスク",
            due_date=datetime.now(UTC) + timedelta(hours=1),
        )

        # 期限が3日後（対象外）
        db.create_reminder(
            workspace_id=workspace.id,
            title="後日タスク",
            due_date=datetime.now(UTC) + timedelta(days=3),
        )

        # 既に期限切れで通知済み（対象外）
        reminder_notified = db.create_reminder(
            workspace_id=workspace.id,
            title="通知済みタスク",
            due_date=datetime.now(UTC) - timedelta(hours=1),
        )
        db.update_reminder_notified(reminder_notified.id, notified=True)

        # 24時間以内に期限が来る、未通知のリマインダーを取得
        pending = db.get_pending_reminders(hours_ahead=24)
        assert len(pending) == 1
        assert pending[0].title == "急ぎタスク"

    def test_update_reminder_status(self, db: Database) -> None:
        """DB-12: リマインダーステータス更新."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="タスク",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )

        assert reminder.status == "pending"

        # 完了に更新
        updated = db.update_reminder_status(reminder.id, "done")
        assert updated.status == "done"

        # キャンセルに更新
        updated = db.update_reminder_status(reminder.id, "cancelled")
        assert updated.status == "cancelled"

    def test_update_reminder_notified(self, db: Database) -> None:
        """DB-13: リマインダー通知済み更新."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="タスク",
            due_date=datetime.now(UTC) + timedelta(hours=1),
        )

        assert reminder.notified is False

        # 通知済みに更新
        updated = db.update_reminder_notified(reminder.id, notified=True)
        assert updated.notified is True

    def test_get_reminder_by_id(self, db: Database) -> None:
        """DB-14: IDでリマインダー取得."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="タスク",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )

        # 存在するIDで取得
        found = db.get_reminder_by_id(reminder.id)
        assert found is not None
        assert found.id == reminder.id
        assert found.title == "タスク"

        # 存在しないIDで取得
        not_found = db.get_reminder_by_id(99999)
        assert not_found is None

    def test_delete_reminder(self, db: Database) -> None:
        """DB-15: リマインダー削除."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        reminder = db.create_reminder(
            workspace_id=workspace.id,
            title="削除対象",
            due_date=datetime.now(UTC) + timedelta(days=1),
        )
        reminder_id = reminder.id

        # 削除
        result = db.delete_reminder(reminder_id)
        assert result is True

        # 削除後は取得できない
        found = db.get_reminder_by_id(reminder_id)
        assert found is None

        # 存在しないIDの削除はFalse
        result = db.delete_reminder(99999)
        assert result is False


class TestVoiceSession:
    """VoiceSession model tests."""

    def test_create_voice_session(self, db: Database) -> None:
        """DB-16: VoiceSession作成."""
        from datetime import UTC, datetime

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        start_time = datetime.now(UTC)
        session = db.create_voice_session(
            room_id=room.id,
            start_time=start_time,
            participants=["user_1", "user_2"],
        )

        assert session.id is not None
        assert session.room_id == room.id
        assert session.start_time.replace(tzinfo=None) == start_time.replace(tzinfo=None)
        assert session.end_time is None
        assert session.file_path is None
        assert session.transcription is None
        assert session.participants == ["user_1", "user_2"]

    def test_get_voice_session_by_id(self, db: Database) -> None:
        """DB-17: IDでVoiceSession取得."""
        from datetime import UTC, datetime

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user_1"],
        )

        # 存在するIDで取得
        found = db.get_voice_session_by_id(session.id)
        assert found is not None
        assert found.id == session.id

        # 存在しないIDで取得
        not_found = db.get_voice_session_by_id(99999)
        assert not_found is None

    def test_get_voice_sessions_by_room(self, db: Database) -> None:
        """DB-18: Room別VoiceSession取得."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room1 = db.create_room(
            workspace_id=workspace.id,
            name="通話1",
            discord_channel_id="voice_1",
            room_type="topic",
        )
        room2 = db.create_room(
            workspace_id=workspace.id,
            name="通話2",
            discord_channel_id="voice_2",
            room_type="topic",
        )

        # Room1に2件作成
        db.create_voice_session(
            room_id=room1.id,
            start_time=datetime.now(UTC),
            participants=["user_1"],
        )
        db.create_voice_session(
            room_id=room1.id,
            start_time=datetime.now(UTC) + timedelta(hours=1),
            participants=["user_2"],
        )

        # Room2に1件作成
        db.create_voice_session(
            room_id=room2.id,
            start_time=datetime.now(UTC),
            participants=["user_3"],
        )

        # Room1のセッションのみ取得
        sessions = db.get_voice_sessions_by_room(room1.id)
        assert len(sessions) == 2
        assert all(s.room_id == room1.id for s in sessions)

    def test_update_voice_session_end(self, db: Database) -> None:
        """DB-19: VoiceSession終了更新."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        start_time = datetime.now(UTC)
        session = db.create_voice_session(
            room_id=room.id,
            start_time=start_time,
            participants=["user_1"],
        )

        assert session.end_time is None
        assert session.file_path is None

        # 終了時刻とファイルパスを更新
        end_time = start_time + timedelta(hours=1)
        file_path = "/data/voice/session_1.ogg"
        updated = db.update_voice_session_end(
            session_id=session.id,
            end_time=end_time,
            file_path=file_path,
        )

        assert updated.end_time.replace(tzinfo=None) == end_time.replace(tzinfo=None)
        assert updated.file_path == file_path

    def test_update_voice_session_transcription(self, db: Database) -> None:
        """DB-20: VoiceSession文字起こし更新."""
        from datetime import UTC, datetime

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user_1"],
        )

        assert session.transcription is None

        # 文字起こしを更新
        transcription = "こんにちは、本日の議題は..."
        updated = db.update_voice_session_transcription(session.id, transcription)

        assert updated.transcription == transcription

    def test_get_active_voice_sessions(self, db: Database) -> None:
        """DB-21: 録音中のVoiceSession取得."""
        from datetime import UTC, datetime, timedelta

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        # 録音中（end_time = None）
        active_session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user_1"],
        )

        # 終了済み（end_time あり）
        ended_session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC) - timedelta(hours=2),
            participants=["user_2"],
        )
        db.update_voice_session_end(
            session_id=ended_session.id,
            end_time=datetime.now(UTC) - timedelta(hours=1),
            file_path="/data/voice/ended.ogg",
        )

        # 録音中のセッションのみ取得
        active_sessions = db.get_active_voice_sessions(room.id)
        assert len(active_sessions) == 1
        assert active_sessions[0].id == active_session.id

    def test_delete_voice_session(self, db: Database) -> None:
        """DB-22: VoiceSession削除."""
        from datetime import UTC, datetime

        workspace = db.create_workspace(name="A社", discord_server_id="123")
        room = db.create_room(
            workspace_id=workspace.id,
            name="通話チャンネル",
            discord_channel_id="voice_123",
            room_type="topic",
        )

        session = db.create_voice_session(
            room_id=room.id,
            start_time=datetime.now(UTC),
            participants=["user_1"],
        )
        session_id = session.id

        # 削除
        result = db.delete_voice_session(session_id)
        assert result is True

        # 削除後は取得できない
        found = db.get_voice_session_by_id(session_id)
        assert found is None

        # 存在しないIDの削除はFalse
        result = db.delete_voice_session(99999)
        assert result is False
