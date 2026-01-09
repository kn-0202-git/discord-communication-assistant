"""Discordスラッシュコマンド

このモジュールはDiscordのスラッシュコマンド（Application Commands）を定義します。

コマンド一覧:
    /summary [days] - 直近の会話を要約
    /search {keyword} - 過去メッセージ検索
    /remind {title} {date} [description] - リマインダー登録

Example:
    >>> from discord import app_commands
    >>> from src.bot.commands import BotCommands
    >>>
    >>> tree = app_commands.CommandTree(client)
    >>> commands = BotCommands(tree, db, router)
"""

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands

if TYPE_CHECKING:
    from src.ai.router import AIRouter
    from src.db.database import Database


def parse_due_date(date_str: str) -> datetime:
    """日時文字列をパースしてdatetimeを返す.

    サポート形式:
        - 相対日時: "3d"（3日後）, "2h"（2時間後）, "30m"（30分後）
        - 絶対日時: "2025-01-15", "2025-01-15 14:30"

    Args:
        date_str: 日時文字列

    Returns:
        パースされたdatetime（UTC）

    Raises:
        ValueError: 無効な形式の場合
    """
    date_str = date_str.strip()

    # 相対日時パターン: 数字 + d/h/m
    relative_pattern = re.compile(r"^(\d+)([dhm])$", re.IGNORECASE)
    match = relative_pattern.match(date_str)

    if match:
        value = int(match.group(1))
        unit = match.group(2).lower()

        if value <= 0:
            raise ValueError("0より大きい値を指定してください")

        now = datetime.now(UTC)
        if unit == "d":
            return now + timedelta(days=value)
        elif unit == "h":
            return now + timedelta(hours=value)
        elif unit == "m":
            return now + timedelta(minutes=value)

    # 絶対日時パターン: YYYY-MM-DD または YYYY-MM-DD HH:MM
    try:
        # まず日付と時刻を試す
        if " " in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        # UTCタイムゾーンを付与
        return dt.replace(tzinfo=UTC)
    except ValueError:
        pass

    raise ValueError(
        "日時の形式が正しくありません。\n"
        "例: 1d（1日後）, 2h（2時間後）, 30m（30分後）, 2025-01-15, 2025-01-15 14:30"
    )


class BotCommands:
    """Botのスラッシュコマンド

    /summary, /searchなどのコマンドを提供します。

    Attributes:
        _tree: CommandTree インスタンス
        _db: Database インスタンス
        _router: AIRouter インスタンス
    """

    # 検索結果の最大表示件数
    MAX_SEARCH_RESULTS = 10

    def __init__(
        self,
        tree: app_commands.CommandTree,
        db: "Database",
        router: "AIRouter",
    ) -> None:
        """BotCommandsを初期化

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
        self._register_summary_command()
        self._register_search_command()
        self._register_remind_command()

    def _register_summary_command(self) -> None:
        """/summary コマンドを登録"""

        @self._tree.command(
            name="summary",
            description="直近の会話を要約します",
        )
        @app_commands.describe(days="要約対象の日数（デフォルト: 7日）")
        async def summary_command(
            interaction: discord.Interaction,
            days: int = 7,
        ) -> None:
            """会話を要約するコマンド"""
            await self._handle_summary(interaction, days)

    def _register_search_command(self) -> None:
        """/search コマンドを登録"""

        @self._tree.command(
            name="search",
            description="過去のメッセージを検索します",
        )
        @app_commands.describe(keyword="検索キーワード")
        async def search_command(
            interaction: discord.Interaction,
            keyword: str,
        ) -> None:
            """メッセージを検索するコマンド"""
            await self._handle_search(interaction, keyword)

    def _register_remind_command(self) -> None:
        """/remind コマンドを登録"""

        @self._tree.command(
            name="remind",
            description="リマインダーを登録します",
        )
        @app_commands.describe(
            title="リマインダーのタイトル",
            date="期限（例: 1d, 2h, 30m, 2025-01-15, 2025-01-15 14:30）",
            description="詳細な説明（オプション）",
        )
        async def remind_command(
            interaction: discord.Interaction,
            title: str,
            date: str,
            description: str | None = None,
        ) -> None:
            """リマインダーを登録するコマンド"""
            await self._handle_remind(interaction, title, date, description)

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
                    "このチャンネルは登録されていません。"
                    "メッセージを送信するとチャンネルが登録されます。"
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

    async def _handle_search(
        self,
        interaction: discord.Interaction,
        keyword: str,
    ) -> None:
        """/search コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            keyword: 検索キーワード
        """
        # 即座に応答
        await interaction.response.defer(thinking=True)

        try:
            guild = interaction.guild

            if not guild:
                await interaction.followup.send("このコマンドはサーバー内でのみ使用できます。")
                return

            # Workspaceを取得
            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            # 検索を実行（Workspace内のみ）
            results = self._db.search_messages(
                workspace_id=workspace.id,
                keyword=keyword,
                limit=self.MAX_SEARCH_RESULTS,
            )

            if not results:
                await interaction.followup.send(
                    f"「{keyword}」に一致するメッセージが見つかりませんでした。"
                )
                return

            # 結果を整形
            embed = discord.Embed(
                title=f"検索結果: 「{keyword}」",
                description=f"{len(results)}件のメッセージが見つかりました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            for i, msg in enumerate(results[: self.MAX_SEARCH_RESULTS], 1):
                # メッセージ内容を短縮
                content = msg.content
                if len(content) > 100:
                    content = content[:100] + "..."

                # 日時をフォーマット
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")

                embed.add_field(
                    name=f"{i}. {msg.sender_name} ({timestamp})",
                    value=content,
                    inline=False,
                )

            embed.set_footer(text="このWorkspace内で検索されました")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    async def _handle_remind(
        self,
        interaction: discord.Interaction,
        title: str,
        date: str,
        description: str | None,
    ) -> None:
        """/remind コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            title: リマインダーのタイトル
            date: 期限（相対/絶対日時）
            description: 詳細な説明（オプション）
        """
        # 即座に応答
        await interaction.response.defer(thinking=True)

        try:
            guild = interaction.guild

            if not guild:
                await interaction.followup.send("このコマンドはサーバー内でのみ使用できます。")
                return

            # Workspaceを取得
            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            # 日時をパース
            try:
                due_date = parse_due_date(date)
            except ValueError as e:
                await interaction.followup.send(str(e))
                return

            # リマインダーを作成
            reminder = self._db.create_reminder(
                workspace_id=workspace.id,
                title=title,
                due_date=due_date,
                description=description,
            )

            # 結果を送信
            embed = discord.Embed(
                title="リマインダーを登録しました",
                color=discord.Color.blue(),
                timestamp=datetime.now(UTC),
            )
            embed.add_field(name="タイトル", value=title, inline=False)
            embed.add_field(
                name="期限",
                value=due_date.strftime("%Y-%m-%d %H:%M UTC"),
                inline=False,
            )
            if description:
                embed.add_field(name="説明", value=description, inline=False)
            embed.set_footer(text=f"リマインダーID: {reminder.id}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")


# 後方互換性のためのエイリアス
SummaryCommands = BotCommands


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
    BotCommands(tree, db, router)
    return tree
