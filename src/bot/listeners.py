"""Discord イベントリスナー

このモジュールはDiscordのイベントを処理するリスナークラスを提供します。
メッセージ受信などのイベントをハンドリングし、必要な処理を行います。
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

import discord


class MessageData(TypedDict):
    """メッセージデータの型定義"""

    content: str
    author_name: str
    author_id: int
    guild_id: int | None
    channel_id: int
    message_id: int
    attachments: list[dict[str, Any]]


class MessageListener:
    """メッセージイベントのリスナークラス

    Discordのメッセージイベントを監視し、必要な情報を抽出します。
    Botからのメッセージは無視し、ユーザーからのメッセージのみ処理します。

    Attributes:
        client: Discord Botクライアント
        on_message_callback: メッセージ受信時に呼ばれるコールバック関数

    Example:
        >>> client = BotClient()
        >>> async def handle_message(data: MessageData):
        ...     print(f"Message received: {data['content']}")
        >>> listener = MessageListener(client, on_message_callback=handle_message)
    """

    def __init__(
        self,
        client: discord.Client,
        on_message_callback: Callable[[MessageData], Awaitable[None]] | None = None,
    ) -> None:
        """MessageListenerを初期化します。

        Args:
            client: Discord Botクライアント
            on_message_callback: メッセージ受信時に呼ばれる非同期コールバック関数
        """
        self.client = client
        self._on_message_callback = on_message_callback

    async def on_message(self, message: discord.Message) -> MessageData | None:
        """メッセージ受信イベントを処理します。

        Botからのメッセージは無視し、ユーザーからのメッセージのみ処理します。
        メッセージの内容、送信者情報、サーバー・チャンネル情報を抽出します。

        Args:
            message: 受信したDiscordメッセージ

        Returns:
            メッセージデータの辞書。Botからのメッセージの場合はNone
        """
        # Botからのメッセージは無視
        if message.author.bot:
            return None

        # メッセージデータを抽出
        data: MessageData = {
            "content": message.content,
            "author_name": message.author.name,
            "author_id": message.author.id,
            "guild_id": message.guild.id if message.guild else None,
            "channel_id": message.channel.id,
            "message_id": message.id,
            "attachments": self._extract_attachments(message),
        }

        # コールバックが設定されている場合は呼び出し
        if self._on_message_callback:
            await self._on_message_callback(data)

        return data

    def _extract_attachments(self, message: discord.Message) -> list[dict[str, Any]]:
        """メッセージから添付ファイル情報を抽出します。

        Args:
            message: Discordメッセージ

        Returns:
            添付ファイル情報のリスト
        """
        attachments = []
        for attachment in message.attachments:
            attachments.append(
                {
                    "id": attachment.id,
                    "filename": attachment.filename,
                    "url": attachment.url,
                    "size": attachment.size,
                    "content_type": attachment.content_type,
                }
            )
        return attachments


class GuildListener:
    """サーバー（Guild）イベントのリスナークラス

    サーバー参加・退出などのイベントを監視します。

    Attributes:
        client: Discord Botクライアント
    """

    def __init__(self, client: discord.Client) -> None:
        """GuildListenerを初期化します。

        Args:
            client: Discord Botクライアント
        """
        self.client = client

    async def on_guild_join(self, guild: discord.Guild) -> dict[str, Any]:
        """サーバー参加イベントを処理します。

        Args:
            guild: 参加したサーバー

        Returns:
            サーバー情報の辞書
        """
        return {
            "guild_id": guild.id,
            "guild_name": guild.name,
            "member_count": guild.member_count,
            "owner_id": guild.owner_id,
        }

    async def on_guild_remove(self, guild: discord.Guild) -> dict[str, Any]:
        """サーバー退出イベントを処理します。

        Args:
            guild: 退出したサーバー

        Returns:
            サーバー情報の辞書
        """
        return {
            "guild_id": guild.id,
            "guild_name": guild.name,
        }
