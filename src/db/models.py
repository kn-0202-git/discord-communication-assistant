"""Database models.

REQUIREMENTS.md #7 データモデルに基づく実装。
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    """現在のUTC時刻を返す（Python 3.12対応）."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Workspace(Base):
    """Workspace（最上位の部屋）.

    請負者ごと or プロジェクトごとに作成。
    Workspace間は完全分離（相互に見えない）。
    """

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discord_server_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ai_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="workspace")
    reminders: Mapped[list["Reminder"]] = relationship("Reminder", back_populates="workspace")


class Room(Base):
    """Room（中の部屋）.

    トピック別 or メンバー別に作成。
    同一Workspace内では情報共有可能。
    """

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discord_channel_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Room type: topic / member / aggregation
    room_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="rooms")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="room")
    voice_sessions: Mapped[list["VoiceSession"]] = relationship(
        "VoiceSession", back_populates="room"
    )

    # Room links (as source)
    outgoing_links: Mapped[list["RoomLink"]] = relationship(
        "RoomLink",
        foreign_keys="RoomLink.source_room_id",
        back_populates="source_room",
    )
    # Room links (as target)
    incoming_links: Mapped[list["RoomLink"]] = relationship(
        "RoomLink",
        foreign_keys="RoomLink.target_room_id",
        back_populates="target_room",
    )


class RoomLink(Base):
    """RoomLink（Room間の情報共有設定）.

    Room間の情報共有を管理。
    """

    __tablename__ = "room_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    target_room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)  # bidirectional / one_way

    # Relationships
    source_room: Mapped["Room"] = relationship(
        "Room",
        foreign_keys=[source_room_id],
        back_populates="outgoing_links",
    )
    target_room: Mapped["Room"] = relationship(
        "Room",
        foreign_keys=[target_room_id],
        back_populates="incoming_links",
    )


class Message(Base):
    """Message（メッセージ）.

    すべてのテキストメッセージを保存。
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Message type: text / image / video / voice
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    discord_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utc_now)

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="message")


class Attachment(Base):
    """Attachment（添付ファイル）.

    写真・動画・ボイスメッセージを保存。
    """

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    drive_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # File type: image / video / voice / document
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="attachments")


class Reminder(Base):
    """Reminder（リマインダー）.

    Phase 2で実装予定だが、モデルは先に定義。
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey("workspaces.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending / done / cancelled
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="reminders")


class VoiceSession(Base):
    """VoiceSession（通話録音）.

    通話録音セッションを管理。
    """

    __tablename__ = "voice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("rooms.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    participants: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="voice_sessions")
