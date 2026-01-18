"""Discordスラッシュコマンド

このモジュールはDiscordのスラッシュコマンド（Application Commands）を定義します。

コマンド一覧:
    /summary [days] - 直近の会話を要約
    /search {keyword} - 過去メッセージ検索
    /set_room_type {room_type} - Room種別を設定
    /remind {title} {date} [description] - リマインダー登録
    /reminders - リマインダー一覧表示
    /record {action} - 通話録音の開始/停止
    /transcribe {session_id} - 録音セッションを文字起こし

Example:
    >>> from discord import app_commands
    >>> from src.bot.commands import BotCommands
    >>>
    >>> tree = app_commands.CommandTree(client)
    >>> commands = BotCommands(tree, db, router)
"""

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from src.ai.transcription.whisper import WhisperProvider
from src.storage.base import StorageProvider
from src.storage.google_drive import GoogleDriveStorage

if TYPE_CHECKING:
    from src.ai.router import AIRouter
    from src.bot.voice_recorder import VoiceRecorder
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
        _voice_recorder: VoiceRecorder インスタンス（オプション）
        _storage: StorageProvider インスタンス（オプション）
        _drive_storage: GoogleDriveStorage インスタンス（オプション）
    """

    # 検索結果の最大表示件数
    MAX_SEARCH_RESULTS = 10

    def __init__(
        self,
        tree: app_commands.CommandTree,
        db: "Database",
        router: "AIRouter",
        voice_recorder: "VoiceRecorder | None" = None,
        *,
        storage: StorageProvider | None = None,
        drive_storage: GoogleDriveStorage | None = None,
    ) -> None:
        """BotCommandsを初期化

        Args:
            tree: discord.py CommandTree
            db: Database インスタンス
            router: AIRouter インスタンス
            storage: StorageProvider インスタンス（オプション）
            drive_storage: GoogleDriveStorage インスタンス（オプション）
            voice_recorder: VoiceRecorder インスタンス（オプション）
        """
        self._tree = tree
        self._db = db
        self._router = router
        self._voice_recorder = voice_recorder
        self._storage = storage
        self._drive_storage = drive_storage
        self._register_commands()

    def _register_commands(self) -> None:
        """コマンドを登録"""
        self._register_summary_command()
        self._register_search_command()
        self._register_set_room_type_command()
        self._register_remind_command()
        self._register_reminders_command()
        self._register_record_command()
        self._register_transcribe_command()
        self._register_save_command()

    def _register_save_command(self) -> None:
        """/save コマンドを登録"""

        @self._tree.command(
            name="save",
            description="最新の添付ファイルをGoogle Driveに保存します",
        )
        @app_commands.describe(folder="保存先フォルダ（例: client-a/design）")
        async def save_command(
            interaction: discord.Interaction,
            folder: str | None = None,
        ) -> None:
            """添付ファイルをGoogle Driveに保存するコマンド"""
            await self._handle_save(interaction, folder)

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

    def _register_set_room_type_command(self) -> None:
        """/set_room_type コマンドを登録"""

        @self._tree.command(
            name="set_room_type",
            description="このチャンネルのRoom種別を設定します",
        )
        @app_commands.describe(room_type="Room種別 (topic/aggregation)")
        @app_commands.choices(
            room_type=[
                app_commands.Choice(name="topic", value="topic"),
                app_commands.Choice(name="aggregation", value="aggregation"),
            ]
        )
        async def set_room_type_command(
            interaction: discord.Interaction,
            room_type: app_commands.Choice[str],
        ) -> None:
            """Room種別を設定するコマンド"""
            await self._handle_set_room_type(interaction, room_type.value)

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

    def _register_reminders_command(self) -> None:
        """/reminders コマンドを登録"""

        @self._tree.command(
            name="reminders",
            description="リマインダー一覧を表示します",
        )
        async def reminders_command(
            interaction: discord.Interaction,
        ) -> None:
            """リマインダー一覧を表示するコマンド"""
            await self._handle_reminders(interaction)

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
            channel = interaction.channel

            if not guild or not channel:
                await interaction.followup.send("このコマンドはサーバー内でのみ使用できます。")
                return

            # Workspaceを取得
            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            # Roomを取得
            room = self._db.get_room_by_discord_id(str(channel.id))
            if not room:
                await interaction.followup.send(
                    "このチャンネルは登録されていません。"
                    "メッセージを送信するとチャンネルが登録されます。"
                )
                return

            # 検索を実行
            if room.room_type == "aggregation":
                results = self._db.search_messages(
                    workspace_id=workspace.id,
                    keyword=keyword,
                    limit=self.MAX_SEARCH_RESULTS,
                )
            else:
                results = self._db.search_messages_in_rooms(
                    room_ids=[room.id],
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

            room_name_cache: dict[int, str] = {}

            for i, msg in enumerate(results[: self.MAX_SEARCH_RESULTS], 1):
                # メッセージ内容を短縮
                content = msg.content
                if len(content) > 100:
                    content = content[:100] + "..."

                # 日時をフォーマット
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")

                # Room名を取得
                room_name = room_name_cache.get(msg.room_id)
                if room_name is None:
                    room = self._db.get_room_by_id(msg.room_id)
                    room_name = room.name if room else "不明"
                    room_name_cache[msg.room_id] = room_name

                embed.add_field(
                    name=f"{i}. {timestamp} | {msg.sender_name} | #{room_name}",
                    value=content,
                    inline=False,
                )

            embed.set_footer(text="このWorkspace内で検索されました")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    async def _handle_set_room_type(
        self,
        interaction: discord.Interaction,
        room_type: str,
    ) -> None:
        """/set_room_type コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            room_type: Room種別 (topic/aggregation)
        """
        await interaction.response.defer(thinking=True)

        try:
            guild = interaction.guild
            channel = interaction.channel

            if not guild or not channel:
                await interaction.followup.send("このコマンドはサーバー内でのみ使用できます。")
                return

            user = interaction.user
            if not isinstance(user, discord.Member) or not user.guild_permissions.administrator:
                await interaction.followup.send("このコマンドは管理者のみ実行できます。")
                return

            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            room = self._db.get_room_by_discord_id(str(channel.id))
            if not room:
                await interaction.followup.send(
                    "このチャンネルは登録されていません。"
                    "メッセージを送信するとチャンネルが登録されます。"
                )
                return

            updated_room = self._db.update_room_type(room.id, room_type)
            if not updated_room:
                await interaction.followup.send("Room種別の更新に失敗しました。")
                return

            await interaction.followup.send(f"Room種別を {room_type} に変更しました。")

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

    async def _handle_reminders(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """/reminders コマンドのハンドラ

        Args:
            interaction: Discord Interaction
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

            # リマインダー一覧を取得（未完了のみ）
            reminders = self._db.get_reminders_by_workspace(
                workspace.id,
                include_done=False,
            )

            if not reminders:
                await interaction.followup.send("リマインダーがありません。")
                return

            # 結果を送信
            embed = discord.Embed(
                title="リマインダー一覧",
                description=f"{len(reminders)}件のリマインダーがあります",
                color=discord.Color.blue(),
                timestamp=datetime.now(UTC),
            )

            for reminder in reminders[:10]:  # 最大10件表示
                due_str = reminder.due_date.strftime("%Y-%m-%d %H:%M")
                status_emoji = "⏰" if reminder.status == "pending" else "✅"

                value = f"期限: {due_str}"
                if reminder.description:
                    # 説明を短縮
                    desc = reminder.description
                    if len(desc) > 50:
                        desc = desc[:50] + "..."
                    value += f"\n{desc}"

                embed.add_field(
                    name=f"{status_emoji} {reminder.title}",
                    value=value,
                    inline=False,
                )

            if len(reminders) > 10:
                embed.set_footer(text=f"他{len(reminders) - 10}件のリマインダーがあります")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    def _register_record_command(self) -> None:
        """/record コマンドを登録"""

        @self._tree.command(
            name="record",
            description="通話の録音を開始または停止します",
        )
        @app_commands.describe(action="on: 録音開始, off: 録音停止")
        @app_commands.choices(
            action=[
                app_commands.Choice(name="on - 録音開始", value="on"),
                app_commands.Choice(name="off - 録音停止", value="off"),
            ]
        )
        async def record_command(
            interaction: discord.Interaction,
            action: app_commands.Choice[str],
        ) -> None:
            """通話録音を制御するコマンド"""
            await self._handle_record(interaction, action.value)

    async def _handle_record(
        self,
        interaction: discord.Interaction,
        action: str,
    ) -> None:
        """/record コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            action: "on" または "off"
        """
        # 即座に応答
        await interaction.response.defer(thinking=True)

        try:
            # VoiceRecorderが設定されていない場合
            if self._voice_recorder is None:
                await interaction.followup.send(
                    "録音機能は現在利用できません。Bot管理者にお問い合わせください。"
                )
                return

            guild = interaction.guild
            user = interaction.user

            if not guild:
                await interaction.followup.send("このコマンドはサーバー内でのみ使用できます。")
                return

            # Workspaceを取得
            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            if action == "on":
                await self._handle_record_on(interaction, workspace, user)
            else:
                await self._handle_record_off(interaction)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    async def _handle_record_on(
        self,
        interaction: discord.Interaction,
        workspace: "Workspace",
        user: discord.User | discord.Member,
    ) -> None:
        """録音開始の処理

        Args:
            interaction: Discord Interaction
            workspace: Workspace オブジェクト
            user: コマンド実行者
        """
        from src.bot.voice_recorder import VoiceRecorderError

        guild = interaction.guild
        assert guild is not None  # 呼び出し元でチェック済み
        assert self._voice_recorder is not None  # 呼び出し元でチェック済み

        # ユーザーがボイスチャンネルに接続しているか確認
        if not isinstance(user, discord.Member) or user.voice is None:
            await interaction.followup.send(
                "ボイスチャンネルに接続してからこのコマンドを使用してください。"
            )
            return

        voice_channel = user.voice.channel
        if not isinstance(voice_channel, discord.VoiceChannel):
            await interaction.followup.send("通常のボイスチャンネルでのみ録音できます。")
            return

        # 既に録音中か確認
        if self._voice_recorder.is_recording(guild.id):
            await interaction.followup.send(
                "このサーバーでは既に録音中です。「/record off」で停止してください。"
            )
            return

        # ボイスチャンネル用のRoomを取得または作成
        room = self._db.get_room_by_discord_id(str(voice_channel.id))
        if not room:
            # Roomが存在しない場合は作成
            room = self._db.create_room(
                workspace_id=workspace.id,
                name=voice_channel.name,
                discord_channel_id=str(voice_channel.id),
                room_type="voice",
            )

        # 通知先のテキストチャンネルを取得
        notify_channel = None
        if isinstance(interaction.channel, discord.TextChannel):
            notify_channel = interaction.channel

        # 録音開始
        try:
            session_id = await self._voice_recorder.start_recording(
                voice_channel=voice_channel,
                room_id=room.id,
                workspace_id=workspace.id,
                notify_channel=notify_channel,
            )

            await interaction.followup.send(
                f"録音を開始しました。（セッションID: {session_id}）\n"
                f"「/record off」で録音を停止できます。"
            )

        except VoiceRecorderError as e:
            await interaction.followup.send(f"録音の開始に失敗しました: {e}")

    async def _handle_record_off(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """録音停止の処理

        Args:
            interaction: Discord Interaction
        """
        from src.bot.voice_recorder import VoiceRecorderError

        guild = interaction.guild
        assert guild is not None  # 呼び出し元でチェック済み
        assert self._voice_recorder is not None  # 呼び出し元でチェック済み

        # 録音中か確認
        if not self._voice_recorder.is_recording(guild.id):
            await interaction.followup.send("このサーバーでは録音していません。")
            return

        # 録音停止
        try:
            file_path = await self._voice_recorder.stop_recording(guild.id)

            await interaction.followup.send(
                f"録音を停止しました。\n" f"ファイル: `{file_path.name}`"
            )

        except VoiceRecorderError as e:
            await interaction.followup.send(f"録音の停止に失敗しました: {e}")

    def _register_transcribe_command(self) -> None:
        """/transcribe コマンドを登録"""

        @self._tree.command(
            name="transcribe",
            description="録音セッションを文字起こしします",
        )
        @app_commands.describe(session_id="録音セッションID")
        async def transcribe_command(
            interaction: discord.Interaction,
            session_id: int,
        ) -> None:
            """録音を文字起こしするコマンド"""
            await self._handle_transcribe(interaction, session_id)

    async def _handle_transcribe(
        self,
        interaction: discord.Interaction,
        session_id: int,
    ) -> None:
        """/transcribe コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            session_id: VoiceSession ID
        """
        # 即座に応答（処理中であることを通知）
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

            # VoiceSessionを取得
            session = self._db.get_voice_session_by_id(session_id)
            if not session:
                await interaction.followup.send(f"セッションID {session_id} が見つかりません。")
                return

            # 音声ファイルの存在確認
            if not session.file_path:
                await interaction.followup.send(
                    "このセッションには音声ファイルがありません。"
                    "録音が完了しているか確認してください。"
                )
                return

            audio_path = Path(session.file_path)
            if not audio_path.exists():
                await interaction.followup.send(f"音声ファイルが見つかりません: {audio_path.name}")
                return

            # 音声ファイルを読み込み
            audio_bytes = audio_path.read_bytes()

            # APIキーの確認
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                await interaction.followup.send(
                    "文字起こし機能が設定されていません。Bot管理者にお問い合わせください。"
                )
                return

            # WhisperProviderで文字起こし
            provider = WhisperProvider(api_key=api_key, model="whisper-1")
            transcription = await provider.transcribe(audio_bytes, language="ja")

            # DBに保存
            self._db.update_voice_session_transcription(session_id, transcription)

            # 結果を送信（Discord Embedの制限は2048文字）
            description = transcription
            if len(description) > 2000:
                description = description[:2000] + "...\n(結果が長いため省略されました)"

            embed = discord.Embed(
                title="文字起こし完了",
                description=description,
                color=discord.Color.blue(),
                timestamp=datetime.now(UTC),
            )
            embed.set_footer(text=f"セッションID: {session_id}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    async def _handle_save(
        self,
        interaction: discord.Interaction,
        folder: str | None,
    ) -> None:
        """/save コマンドのハンドラ

        Args:
            interaction: Discord Interaction
            folder: 保存先フォルダ（任意）
        """
        await interaction.response.defer(thinking=True)

        try:
            if self._drive_storage is None:
                await interaction.followup.send(
                    "Google Drive連携が設定されていません。設定を確認してください。"
                )
                return
            if self._storage is None:
                await interaction.followup.send(
                    "ストレージ設定が不足しています。Bot管理者に確認してください。"
                )
                return

            guild = interaction.guild
            channel = interaction.channel

            if not guild or not channel:
                await interaction.followup.send(
                    "このコマンドはサーバー内のチャンネルでのみ使用できます。"
                )
                return

            workspace = self._db.get_workspace_by_discord_id(str(guild.id))
            if not workspace:
                await interaction.followup.send("このサーバーは登録されていません。")
                return

            room = self._db.get_room_by_discord_id(str(channel.id))
            if not room:
                await interaction.followup.send(
                    "このチャンネルは登録されていません。メッセージ送信後に再度実行してください。"
                )
                return

            attachment = self._db.get_latest_attachment_by_room(room.id)
            if not attachment:
                await interaction.followup.send("保存対象の添付ファイルが見つかりませんでした。")
                return

            if attachment.drive_path:
                await interaction.followup.send("この添付ファイルは既にDriveへ保存済みです。")
                return

            try:
                content = await self._storage.get_file(Path(attachment.file_path))
            except FileNotFoundError:
                await interaction.followup.send(
                    "ローカルファイルが見つかりませんでした。再アップロードしてください。"
                )
                return

            folder_parts = self._build_drive_folder_parts(workspace.name, folder)
            drive_file_path = await self._drive_storage.save_file_with_folder(
                content=content,
                filename=attachment.file_name,
                folder_parts=folder_parts,
            )
            self._db.update_attachment_drive_path(attachment.id, str(drive_file_path))

            description = "\n".join(
                [
                    f"ファイル: {attachment.file_name}",
                    f"保存先: {'/'.join(folder_parts)}",
                    f"Drive ID: {drive_file_path}",
                ]
            )
            embed = discord.Embed(
                title="Google Driveに保存しました",
                description=description,
                color=discord.Color.green(),
                timestamp=datetime.now(UTC),
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"エラーが発生しました: {e}")

    @staticmethod
    def _split_folder_parts(folder: str) -> list[str]:
        cleaned: list[str] = []
        for part in folder.replace("\\", "/").split("/"):
            part = part.strip()
            if not part or part in (".", ".."):
                continue
            cleaned.append(part)
        return cleaned

    def _build_drive_folder_parts(self, workspace_name: str, folder: str | None) -> list[str]:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        parts = [workspace_name, date_str]
        if folder:
            parts.extend(self._split_folder_parts(folder))
        return parts


# Workspace型をインポート（循環参照回避のため遅延インポート）
if TYPE_CHECKING:
    from src.db.models import Workspace


# 後方互換性のためのエイリアス
SummaryCommands = BotCommands


async def setup_commands(
    client: discord.Client,
    db: "Database",
    router: "AIRouter",
    voice_recorder: "VoiceRecorder | None" = None,
    *,
    storage: StorageProvider | None = None,
    drive_storage: GoogleDriveStorage | None = None,
) -> app_commands.CommandTree:
    """コマンドをセットアップ

    Args:
        client: Discord Client
        db: Database インスタンス
        router: AIRouter インスタンス
        storage: StorageProvider インスタンス（オプション）
        drive_storage: GoogleDriveStorage インスタンス（オプション）
        voice_recorder: VoiceRecorder インスタンス（オプション）

    Returns:
        設定済みの CommandTree
    """
    tree = app_commands.CommandTree(client)
    BotCommands(
        tree,
        db,
        router,
        voice_recorder,
        storage=storage,
        drive_storage=drive_storage,
    )
    return tree
