"""Discord音声録音機能

このモジュールはDiscordの音声チャンネルでの録音セッションを管理します。

Note:
    実際の音声キャプチャ機能は追加の依存関係（py-cord または ffmpeg）が必要です。
    現在の実装ではセッション管理とボイスチャンネル接続のみを行います。
    音声ファイルはプレースホルダーとして作成されます。

Example:
    >>> recorder = VoiceRecorder(db, storage)
    >>> session = await recorder.start_recording(voice_channel, room_id)
    >>> # ... 録音中 ...
    >>> file_path = await recorder.stop_recording(voice_channel.guild.id)
"""

import io
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from src.db.database import Database
    from src.storage.local import LocalStorage


# 音声設定
SAMPLE_RATE = 48000  # 48kHz (Discord標準)
CHANNELS = 2  # ステレオ
SAMPLE_WIDTH = 2  # 16-bit


class VoiceRecorderError(Exception):
    """VoiceRecorder関連のエラー"""

    pass


class VoiceRecorder:
    """Discord音声録音セッションを管理するクラス

    ボイスチャンネルに接続してセッションを管理し、
    録音ファイル（現在はプレースホルダー）を保存します。

    Note:
        実際の音声キャプチャには py-cord または ffmpeg が必要です。
        現在はセッション管理のみを実装しています。

    Attributes:
        _db: Database インスタンス
        _storage: LocalStorage インスタンス
        _active_recordings: アクティブな録音セッション（guild_id -> data）
    """

    def __init__(self, db: "Database", storage: "LocalStorage") -> None:
        """VoiceRecorderを初期化

        Args:
            db: Database インスタンス
            storage: LocalStorage インスタンス
        """
        self._db = db
        self._storage = storage
        self._active_recordings: dict[int, dict] = {}

    def is_recording(self, guild_id: int) -> bool:
        """指定のサーバーで録音中かどうか

        Args:
            guild_id: Discord サーバーID

        Returns:
            録音中ならTrue
        """
        return guild_id in self._active_recordings

    def get_recording_info(self, guild_id: int) -> dict | None:
        """録音情報を取得

        Args:
            guild_id: Discord サーバーID

        Returns:
            録音情報（なければNone）
        """
        return self._active_recordings.get(guild_id)

    async def start_recording(
        self,
        voice_channel: discord.VoiceChannel,
        room_id: int,
        workspace_id: int,
        notify_channel: discord.TextChannel | None = None,
    ) -> int:
        """録音を開始

        Args:
            voice_channel: 録音するボイスチャンネル
            room_id: Room ID
            workspace_id: Workspace ID
            notify_channel: 通知を送るテキストチャンネル

        Returns:
            VoiceSession ID

        Raises:
            VoiceRecorderError: 既に録音中の場合
        """
        guild_id = voice_channel.guild.id

        # 既に録音中かチェック
        if self.is_recording(guild_id):
            raise VoiceRecorderError("このサーバーでは既に録音中です")

        # ボイスチャンネルに接続
        try:
            voice_client = await voice_channel.connect()
        except discord.ClientException as e:
            raise VoiceRecorderError(f"ボイスチャンネルへの接続に失敗しました: {e}") from e
        except TimeoutError as e:
            raise VoiceRecorderError("ボイスチャンネルへの接続がタイムアウトしました") from e

        # 録音開始
        start_time = datetime.now(UTC)

        # 現在の参加者を取得
        current_members = [str(member.id) for member in voice_channel.members if not member.bot]

        # VoiceSessionを作成
        voice_session = self._db.create_voice_session(
            room_id=room_id,
            start_time=start_time,
            participants=current_members,
        )

        # アクティブな録音情報を保存
        self._active_recordings[guild_id] = {
            "session_id": voice_session.id,
            "voice_client": voice_client,
            "start_time": start_time,
            "room_id": room_id,
            "workspace_id": workspace_id,
            "voice_channel_id": voice_channel.id,
            "voice_channel_name": voice_channel.name,
            "notify_channel": notify_channel,
            "participants": set(current_members),
        }

        # 通知を送信
        if notify_channel:
            embed = discord.Embed(
                title="録音開始",
                description=f"ボイスチャンネル「{voice_channel.name}」の録音を開始しました。",
                color=discord.Color.red(),
                timestamp=start_time,
            )
            embed.add_field(
                name="参加者",
                value=", ".join([f"<@{uid}>" for uid in current_members]) or "なし",
                inline=False,
            )
            embed.set_footer(text="「/record off」で録音を停止できます")
            await notify_channel.send(embed=embed)

        return voice_session.id

    async def stop_recording(self, guild_id: int) -> Path:
        """録音を停止

        Args:
            guild_id: Discord サーバーID

        Returns:
            保存されたファイルのパス

        Raises:
            VoiceRecorderError: 録音中でない場合
        """
        if not self.is_recording(guild_id):
            raise VoiceRecorderError("このサーバーでは録音していません")

        recording = self._active_recordings[guild_id]
        voice_client: discord.VoiceClient = recording["voice_client"]
        start_time: datetime = recording["start_time"]
        session_id: int = recording["session_id"]
        room_id: int = recording["room_id"]
        workspace_id: int = recording["workspace_id"]
        notify_channel: discord.TextChannel | None = recording["notify_channel"]
        participants: set[str] = recording["participants"]

        # 終了時刻
        end_time = datetime.now(UTC)

        # プレースホルダーWAVファイルを作成
        # Note: 実際の音声キャプチャは追加の依存関係が必要
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            # 1秒の無音データ（プレースホルダー）
            wav_file.writeframes(b"\x00" * SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH)

        # ファイルを保存
        filename = f"recording_{start_time.strftime('%Y%m%d_%H%M%S')}.wav"
        file_path = await self._storage.save_file(
            content=wav_buffer.getvalue(),
            workspace_id=workspace_id,
            room_id=room_id,
            filename=filename,
        )

        # VoiceSessionを更新
        self._db.update_voice_session_end(
            session_id=session_id,
            end_time=end_time,
            file_path=str(file_path),
        )

        # ボイスチャンネルから切断
        await voice_client.disconnect()

        # クリーンアップ
        del self._active_recordings[guild_id]

        # 通知を送信
        if notify_channel:
            duration = (end_time - start_time).total_seconds()
            minutes = int(duration // 60)
            seconds = int(duration % 60)

            embed = discord.Embed(
                title="録音停止",
                description="録音を停止しました。",
                color=discord.Color.green(),
                timestamp=end_time,
            )
            embed.add_field(name="録音時間", value=f"{minutes}分{seconds}秒", inline=True)
            embed.add_field(
                name="参加者",
                value=", ".join([f"<@{uid}>" for uid in participants]) or "なし",
                inline=True,
            )
            embed.add_field(name="ファイル", value=str(file_path.name), inline=False)
            embed.set_footer(text="Note: 音声キャプチャは今後のアップデートで対応予定")
            await notify_channel.send(embed=embed)

        return file_path

    async def cancel_recording(self, guild_id: int) -> None:
        """録音をキャンセル（ファイル保存なし）

        Args:
            guild_id: Discord サーバーID

        Raises:
            VoiceRecorderError: 録音中でない場合
        """
        if not self.is_recording(guild_id):
            raise VoiceRecorderError("このサーバーでは録音していません")

        recording = self._active_recordings[guild_id]
        voice_client: discord.VoiceClient = recording["voice_client"]
        session_id: int = recording["session_id"]

        # VoiceSessionを削除
        self._db.delete_voice_session(session_id)

        # ボイスチャンネルから切断
        await voice_client.disconnect()

        # クリーンアップ
        del self._active_recordings[guild_id]

    def add_participant(self, guild_id: int, user_id: str) -> None:
        """参加者を追加

        Args:
            guild_id: Discord サーバーID
            user_id: 追加するユーザーID
        """
        if guild_id in self._active_recordings:
            self._active_recordings[guild_id]["participants"].add(user_id)

    def remove_participant(self, guild_id: int, user_id: str) -> None:
        """参加者を削除

        Args:
            guild_id: Discord サーバーID
            user_id: 削除するユーザーID
        """
        if guild_id in self._active_recordings:
            self._active_recordings[guild_id]["participants"].discard(user_id)
