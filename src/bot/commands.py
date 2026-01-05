"""Discordスラッシュコマンド

このモジュールはDiscordのスラッシュコマンド（Application Commands）を定義します。

コマンド一覧:
    /summary [days] - 直近の会話を要約

Example:
    >>> from discord import app_commands
    >>> from src.bot.commands import SummaryCommands
    >>>
    >>> tree = app_commands.CommandTree(client)
    >>> summary_cog = SummaryCommands(tree, db, router)
"""

from datetime import datetime
from typing import TYPE_CHECKING

import discord
from discord import app_commands

if TYPE_CHECKING:
    from src.ai.router import AIRouter
    from src.db.database import Database


class SummaryCommands:
    """要約関連のスラッシュコマンド

    /summaryコマンドを提供します。

    Attributes:
        _tree: CommandTree インスタンス
        _db: Database インスタンス
        _router: AIRouter インスタンス
    """

    def __init__(
        self,
        tree: app_commands.CommandTree,
        db: "Database",
        router: "AIRouter",
    ) -> None:
        """SummaryCommandsを初期化

        Args:
            tree: discord.py CommandTree
            db: Database インスタンス
            router: AIRouter インスタンス
        """
        self._tree = tree
        self._db = db
        self._router = router
        self._register_commands()

    def _register_commands(self) -> None:
        """コマンドを登録"""

        @self._tree.command(
            name="summary",
            description="直近の会話を要約します",
        )
        @app_commands.describe(days="要約対象の日数（デフォルト: 7日）")
        async def summary_command(
            interaction: discord.Interaction,
            days: int = 7,
        ) -> None:
            """会話を要約するコマンド

            Args:
                interaction: Discord Interaction
                days: 要約対象の日数
            """
            await self._handle_summary(interaction, days)

    async def _handle_summary(
        self,
        interaction: discord.Interaction,
        days: int,
    ) -> None:
        """/summary コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            days: 要約対象の日数
        """
        # 即座に応答（処理中であることを通知）
        await interaction.response.defer(thinking=True)

        try:
            # チャンネルとサーバー情報を取得
            channel = interaction.channel
            guild = interaction.guild

            if not guild or not channel:
                await interaction.followup.send(
                    "このコマンドはサーバー内のチャンネルでのみ使用できます。"
                )
                return

            # Roomを取得
            room = self._db.get_room_by_discord_id(str(channel.id))
            if not room:
                await interaction.followup.send(
                    "このチャンネルは登録されていません。メッセージを送信するとチャンネルが登録されます。"
                )
                return

            # Workspaceを取得
            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            # メッセージを取得
            db_messages = self._db.get_messages_by_room(room.id, limit=500)

            if not db_messages:
                await interaction.followup.send("このチャンネルにはメッセージがありません。")
                return

            # メッセージをSummarizer用の形式に変換
            messages = [
                {
                    "sender_name": msg.sender_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                }
                for msg in db_messages
            ]

            # 要約を生成
            from src.ai.summarizer import Summarizer, SummaryError

            summarizer = Summarizer(self._router)

            try:
                summary = await summarizer.summarize(
                    messages,
                    days=days,
                    workspace_id=str(workspace.id),
                    room_id=str(room.id),
                )
            except SummaryError as e:
                await interaction.followup.send(f"要約の生成に失敗しました: {e}")
                return

            # 結果を送信
            embed = discord.Embed(
                title=f"直近{days}日間の要約",
                description=summary,
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"要約対象: {len(messages)}件のメッセージ")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")


async def setup_commands(
    client: discord.Client,
    db: "Database",
    router: "AIRouter",
) -> app_commands.CommandTree:
    """コマンドをセットアップ

    Args:
        client: Discord Client
        db: Database インスタンス
        router: AIRouter インスタンス

    Returns:
        設定済みの CommandTree
    """
    tree = app_commands.CommandTree(client)
    SummaryCommands(tree, db, router)
    return tree
