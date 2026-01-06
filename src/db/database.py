"""Database operations.

データベースへのCRUD操作を提供。
"""

from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import (
    Attachment,
    Base,
    Message,
    Room,
    RoomLink,
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
