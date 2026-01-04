"""Discord Botクライアント

このモジュールはDiscord Botの基盤となるクライアントクラスを提供します。
discord.pyのClientを継承し、必要なIntentsを設定します。
"""

from collections.abc import Awaitable, Callable
from typing import Any

import discord


class BotClient(discord.Client):
    """Discord Botのクライアントクラス

    discord.Clientを継承し、メッセージ監視に必要なIntentsを設定します。

    Attributes:
        on_ready_callback: Bot起動時に呼ばれるコールバック関数

    Example:
        >>> async def on_ready():
        ...     print("Botが起動しました")
        >>> client = BotClient(on_ready_callback=on_ready)
        >>> client.run("YOUR_TOKEN")
    """

    def __init__(
        self,
        intents: discord.Intents | None = None,
        on_ready_callback: Callable[[], Awaitable[None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """BotClientを初期化します。

        Args:
            intents: Discord Intents。Noneの場合はデフォルトのIntentsを使用
            on_ready_callback: Bot起動時に呼ばれる非同期コールバック関数
            **kwargs: discord.Clientに渡す追加の引数
        """
        if intents is None:
            intents = self._get_default_intents()

        super().__init__(intents=intents, **kwargs)
        self._on_ready_callback = on_ready_callback

    def _get_default_intents(self) -> discord.Intents:
        """デフォルトのIntentsを取得します。

        メッセージ監視に必要なIntentsを有効化します：
        - messages: メッセージイベントを受信
        - message_content: メッセージ内容を取得
        - guilds: サーバー情報を取得

        Returns:
            設定済みのIntentsオブジェクト
        """
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        intents.guilds = True
        return intents

    async def on_ready(self) -> None:
        """Bot起動時に呼ばれるイベントハンドラ

        Botが正常に起動し、Discordに接続できた時に呼ばれます。
        on_ready_callbackが設定されている場合、それを呼び出します。
        """
        if self.user:
            print(f"Logged in as {self.user.name} (ID: {self.user.id})")
        else:
            print("Bot is ready (user info not available)")

        if self._on_ready_callback:
            await self._on_ready_callback()
