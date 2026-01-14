"""Database operations.

データベースへのCRUD操作を提供。
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import (
    Attachment,
    Base,
    Message,
    Reminder,
    Room,
    RoomLink,
    VoiceSession,
    Workspace,
)


class Database:
    """Database operations class.

    SQLite/PostgreSQL両対応。
    """

    def __init__(self, db_url: str = "sqlite:///data/app.db") -> None:
        """Initialize database connection.

        Args:
            db_url: Database URL. Use ":memory:" for in-memory SQLite.
        """
        if db_url == ":memory:":
            db_url = "sqlite:///:memory:"

        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        """Get or create session."""
        if self._session is None:
            self._session = self.SessionLocal()
        return self._session

    def create_tables(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Close database connection."""
        if self._session is not None:
            self._session.close()
            self._session = None

    # Workspace operations

    def create_workspace(
        self,
        name: str,
        discord_server_id: str,
        ai_config: dict[str, Any] | None = None,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            name: Workspace name.
            discord_server_id: Discord server ID.
            ai_config: AI configuration override.

        Returns:
            Created Workspace object.
        """
        workspace = Workspace(
            name=name,
            discord_server_id=discord_server_id,
            ai_config=ai_config,
        )
        self.session.add(workspace)
        self.session.commit()
        self.session.refresh(workspace)
        return workspace

    def get_workspace_by_discord_id(self, discord_server_id: str) -> Workspace | None:
        """Get workspace by Discord server ID.

        Args:
            discord_server_id: Discord server ID.

        Returns:
            Workspace object or None.
        """
        stmt = select(Workspace).where(Workspace.discord_server_id == discord_server_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_workspace_by_id(self, workspace_id: int) -> Workspace | None:
        """Get workspace by ID.

        Args:
            workspace_id: Workspace ID.

        Returns:
            Workspace object or None.
        """
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        return self.session.execute(stmt).scalar_one_or_none()

    # Room operations

    def create_room(
        self,
        workspace_id: int,
        name: str,
        discord_channel_id: str,
        room_type: str,
        ai_config: dict[str, Any] | None = None,
    ) -> Room:
        """Create a new room.

        Args:
            workspace_id: Parent workspace ID.
            name: Room name.
            discord_channel_id: Discord channel ID.
            room_type: Room type (topic / member / aggregation).
            ai_config: AI configuration override.

        Returns:
            Created Room object.
        """
        room = Room(
            workspace_id=workspace_id,
            name=name,
            discord_channel_id=discord_channel_id,
            room_type=room_type,
            ai_config=ai_config,
        )
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def get_room_by_discord_id(self, discord_channel_id: str) -> Room | None:
        """Get room by Discord channel ID.

        Args:
            discord_channel_id: Discord channel ID.

        Returns:
            Room object or None.
        """
        stmt = select(Room).where(Room.discord_channel_id == discord_channel_id)
        return self.session.execute(stmt).scalar_one_or_none()

    # RoomLink operations

    def create_room_link(
        self,
        source_room_id: int,
        target_room_id: int,
        link_type: str,
    ) -> RoomLink:
        """Create a room link.

        Args:
            source_room_id: Source room ID.
            target_room_id: Target room ID.
            link_type: Link type (bidirectional / one_way).

        Returns:
            Created RoomLink object.
        """
        link = RoomLink(
            source_room_id=source_room_id,
            target_room_id=target_room_id,
            link_type=link_type,
        )
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link

    def get_linked_rooms(self, room_id: int) -> list[Room]:
        """Get rooms linked to a target room.

        Args:
            room_id: Target room ID.

        Returns:
            List of linked source rooms.
        """
        stmt = select(RoomLink).where(RoomLink.target_room_id == room_id)
        links = self.session.execute(stmt).scalars().all()
        return [link.source_room for link in links]

    def get_target_rooms(self, source_room_id: int) -> list[Room]:
        """Get target rooms linked from a source room.

        Args:
            source_room_id: Source room ID.

        Returns:
            List of target rooms.
        """
        stmt = select(RoomLink).where(RoomLink.source_room_id == source_room_id)
        links = self.session.execute(stmt).scalars().all()
        return [link.target_room for link in links]

    def get_aggregation_rooms(self, workspace_id: int) -> list[Room]:
        """Get aggregation rooms in a workspace.

        Args:
            workspace_id: Workspace ID.

        Returns:
            List of aggregation rooms.
        """
        stmt = select(Room).where(
            Room.workspace_id == workspace_id,
            Room.room_type == "aggregation",
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_room_by_id(self, room_id: int) -> Room | None:
        """Get room by ID.

        Args:
            room_id: Room ID.

        Returns:
            Room object or None.
        """
        stmt = select(Room).where(Room.id == room_id)
        return self.session.execute(stmt).scalar_one_or_none()

    # Message operations

    def save_message(
        self,
        room_id: int,
        sender_name: str,
        sender_id: str,
        content: str,
        message_type: str,
        discord_message_id: str,
    ) -> Message:
        """Save a message.

        Args:
            room_id: Room ID.
            sender_name: Sender name.
            sender_id: Sender Discord user ID.
            content: Message content.
            message_type: Message type (text / image / video / voice).
            discord_message_id: Discord message ID.

        Returns:
            Created Message object.
        """
        message = Message(
            room_id=room_id,
            sender_name=sender_name,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            discord_message_id=discord_message_id,
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def get_messages_by_room(
        self,
        room_id: int,
        limit: int | None = None,
    ) -> list[Message]:
        """Get messages by room.

        Args:
            room_id: Room ID.
            limit: Maximum number of messages to return.

        Returns:
            List of messages.
        """
        stmt = select(Message).where(Message.room_id == room_id).order_by(Message.timestamp.desc())
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def search_messages(
        self,
        workspace_id: int,
        keyword: str,
        limit: int = 50,
    ) -> list[Message]:
        """Search messages in a workspace.

        Workspace内のみ検索（他Workspaceは検索不可）。

        Args:
            workspace_id: Workspace ID to search in.
            keyword: Search keyword.
            limit: Maximum number of results.

        Returns:
            List of matching messages.
        """
        # Get all rooms in the workspace
        stmt = select(Room.id).where(Room.workspace_id == workspace_id)
        room_ids = list(self.session.execute(stmt).scalars().all())

        if not room_ids:
            return []

        # Search messages in those rooms only
        stmt = (
            select(Message)
            .where(Message.room_id.in_(room_ids))
            .where(Message.content.contains(keyword))
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    # Attachment operations

    def save_attachment(
        self,
        message_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int,
        drive_path: str | None = None,
        transcription: str | None = None,
    ) -> Attachment:
        """Save an attachment.

        Args:
            message_id: Parent message ID.
            file_name: Original file name.
            file_path: Local file path.
            file_type: File type (image / video / voice / document).
            file_size: File size in bytes.
            drive_path: Google Drive path (optional).
            transcription: Transcription for audio (optional).

        Returns:
            Created Attachment object.
        """
        attachment = Attachment(
            message_id=message_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            drive_path=drive_path,
            transcription=transcription,
        )
        self.session.add(attachment)
        self.session.commit()
        self.session.refresh(attachment)
        return attachment

    def get_latest_attachment_by_room(self, room_id: int) -> Attachment | None:
        """Get latest attachment in a room.

        Args:
            room_id: Room ID.

        Returns:
            Latest Attachment or None.
        """
        stmt = (
            select(Attachment)
            .join(Message, Attachment.message_id == Message.id)
            .where(Message.room_id == room_id)
            .order_by(Message.timestamp.desc(), Attachment.id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def update_attachment_drive_path(self, attachment_id: int, drive_path: str) -> None:
        """Update drive_path for an attachment.

        Args:
            attachment_id: Attachment ID.
            drive_path: Google Drive file ID or path.
        """
        attachment = self.session.get(Attachment, attachment_id)
        if not attachment:
            return
        attachment.drive_path = drive_path
        self.session.commit()

    # Reminder operations

    def create_reminder(
        self,
        workspace_id: int,
        title: str,
        due_date: datetime,
        description: str | None = None,
    ) -> Reminder:
        """Create a reminder.

        Args:
            workspace_id: Workspace ID.
            title: Reminder title.
            due_date: Due date (aware datetime with UTC timezone).
            description: Optional description.

        Returns:
            Created Reminder object.
        """
        reminder = Reminder(
            workspace_id=workspace_id,
            title=title,
            due_date=due_date,
            description=description,
        )
        self.session.add(reminder)
        self.session.commit()
        self.session.refresh(reminder)
        return reminder

    def get_reminders_by_workspace(
        self,
        workspace_id: int,
        include_done: bool = True,
    ) -> list[Reminder]:
        """Get reminders by workspace.

        Args:
            workspace_id: Workspace ID.
            include_done: Include completed/cancelled reminders.

        Returns:
            List of reminders.
        """
        stmt = select(Reminder).where(Reminder.workspace_id == workspace_id)
        if not include_done:
            stmt = stmt.where(Reminder.status == "pending")
        stmt = stmt.order_by(Reminder.due_date)
        return list(self.session.execute(stmt).scalars().all())

    def get_pending_reminders(
        self,
        hours_ahead: int = 24,
    ) -> list[Reminder]:
        """Get pending reminders due within the specified hours.

        Args:
            hours_ahead: Number of hours ahead to check.

        Returns:
            List of pending reminders due soon.
        """
        now = datetime.now(UTC)
        deadline = now + timedelta(hours=hours_ahead)

        stmt = (
            select(Reminder)
            .where(Reminder.status == "pending")
            .where(Reminder.notified.is_(False))
            .where(Reminder.due_date <= deadline)
            .order_by(Reminder.due_date)
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_reminder_by_id(self, reminder_id: int) -> Reminder | None:
        """Get reminder by ID.

        Args:
            reminder_id: Reminder ID.

        Returns:
            Reminder object or None.
        """
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_reminder_status(
        self,
        reminder_id: int,
        status: str,
    ) -> Reminder:
        """Update reminder status.

        Args:
            reminder_id: Reminder ID.
            status: New status (pending / done / cancelled).

        Returns:
            Updated Reminder object.
        """
        reminder = self.get_reminder_by_id(reminder_id)
        if reminder is None:
            raise ValueError(f"Reminder with ID {reminder_id} not found")
        reminder.status = status
        self.session.commit()
        self.session.refresh(reminder)
        return reminder

    def update_reminder_notified(
        self,
        reminder_id: int,
        notified: bool,
    ) -> Reminder:
        """Update reminder notified flag.

        Args:
            reminder_id: Reminder ID.
            notified: Whether the reminder has been notified.

        Returns:
            Updated Reminder object.
        """
        reminder = self.get_reminder_by_id(reminder_id)
        if reminder is None:
            raise ValueError(f"Reminder with ID {reminder_id} not found")
        reminder.notified = notified
        self.session.commit()
        self.session.refresh(reminder)
        return reminder

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder.

        Args:
            reminder_id: Reminder ID.

        Returns:
            True if deleted, False if not found.
        """
        reminder = self.get_reminder_by_id(reminder_id)
        if reminder is None:
            return False
        self.session.delete(reminder)
        self.session.commit()
        return True

    # VoiceSession operations

    def create_voice_session(
        self,
        room_id: int,
        start_time: datetime,
        participants: list[str] | None = None,
    ) -> VoiceSession:
        """Create a voice session.

        Args:
            room_id: Room ID.
            start_time: Session start time (aware datetime with UTC timezone).
            participants: List of participant user IDs.

        Returns:
            Created VoiceSession object.
        """
        session = VoiceSession(
            room_id=room_id,
            start_time=start_time,
            participants=participants,
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return session

    def get_voice_session_by_id(self, session_id: int) -> VoiceSession | None:
        """Get voice session by ID.

        Args:
            session_id: VoiceSession ID.

        Returns:
            VoiceSession object or None.
        """
        stmt = select(VoiceSession).where(VoiceSession.id == session_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_voice_sessions_by_room(
        self,
        room_id: int,
        limit: int | None = None,
    ) -> list[VoiceSession]:
        """Get voice sessions by room.

        Args:
            room_id: Room ID.
            limit: Maximum number of sessions to return.

        Returns:
            List of voice sessions.
        """
        stmt = (
            select(VoiceSession)
            .where(VoiceSession.room_id == room_id)
            .order_by(VoiceSession.start_time.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def get_active_voice_sessions(self, room_id: int) -> list[VoiceSession]:
        """Get active (recording) voice sessions.

        Args:
            room_id: Room ID.

        Returns:
            List of active voice sessions (end_time is None).
        """
        stmt = (
            select(VoiceSession)
            .where(VoiceSession.room_id == room_id)
            .where(VoiceSession.end_time.is_(None))
            .order_by(VoiceSession.start_time.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_voice_session_end(
        self,
        session_id: int,
        end_time: datetime,
        file_path: str,
    ) -> VoiceSession:
        """Update voice session end time and file path.

        Args:
            session_id: VoiceSession ID.
            end_time: Session end time.
            file_path: Path to the recorded audio file.

        Returns:
            Updated VoiceSession object.
        """
        voice_session = self.get_voice_session_by_id(session_id)
        if voice_session is None:
            raise ValueError(f"VoiceSession with ID {session_id} not found")
        voice_session.end_time = end_time
        voice_session.file_path = file_path
        self.session.commit()
        self.session.refresh(voice_session)
        return voice_session

    def update_voice_session_transcription(
        self,
        session_id: int,
        transcription: str,
    ) -> VoiceSession:
        """Update voice session transcription.

        Args:
            session_id: VoiceSession ID.
            transcription: Transcription text.

        Returns:
            Updated VoiceSession object.
        """
        voice_session = self.get_voice_session_by_id(session_id)
        if voice_session is None:
            raise ValueError(f"VoiceSession with ID {session_id} not found")
        voice_session.transcription = transcription
        self.session.commit()
        self.session.refresh(voice_session)
        return voice_session

    def delete_voice_session(self, session_id: int) -> bool:
        """Delete a voice session.

        Args:
            session_id: VoiceSession ID.

        Returns:
            True if deleted, False if not found.
        """
        voice_session = self.get_voice_session_by_id(session_id)
        if voice_session is None:
            return False
        self.session.delete(voice_session)
        self.session.commit()
        return True
