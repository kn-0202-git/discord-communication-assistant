"""Discord Bot基盤のテスト"""

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from src.bot.client import BotClient
from src.bot.listeners import MessageListener


class TestBotClient:
    """BotClientのテスト"""

    def test_create_bot_client(self):
        """正常系: BotClientを作成できる"""
        client = BotClient()
        assert client is not None
        assert isinstance(client, discord.Client)

    def test_bot_client_has_correct_intents(self):
        """正常系: 必要なIntentsが設定されている"""
        client = BotClient()
        # メッセージ関連のintentsが有効であること
        assert client.intents.messages is True
        assert client.intents.message_content is True
        assert client.intents.guilds is True

    def test_bot_client_with_custom_intents(self):
        """正常系: カスタムIntentsを渡せる"""
        custom_intents = discord.Intents.default()
        custom_intents.members = True
        client = BotClient(intents=custom_intents)
        assert client.intents.members is True


class TestMessageListener:
    """MessageListenerのテスト"""

    def test_create_message_listener(self):
        """正常系: MessageListenerを作成できる"""
        mock_client = MagicMock(spec=discord.Client)
        listener = MessageListener(mock_client)
        assert listener is not None
        assert listener.client == mock_client

    @pytest.mark.asyncio
    async def test_on_message_ignores_bot_messages(self):
        """正常系: Botからのメッセージは無視する"""
        mock_client = MagicMock(spec=discord.Client)
        listener = MessageListener(mock_client)

        # Botからのメッセージを作成
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.bot = True

        # on_messageを呼び出し
        result = await listener.on_message(mock_message)

        # Botからのメッセージは処理されない（Noneを返す）
        assert result is None

    @pytest.mark.asyncio
    async def test_on_message_processes_user_messages(self):
        """正常系: ユーザーからのメッセージを処理する"""
        mock_client = MagicMock(spec=discord.Client)
        listener = MessageListener(mock_client)

        # ユーザーからのメッセージを作成
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.content = "テストメッセージ"
        mock_message.author.name = "テストユーザー"
        mock_message.guild.id = 123456789
        mock_message.channel.id = 987654321

        # on_messageを呼び出し
        result = await listener.on_message(mock_message)

        # メッセージ情報が返される
        assert result is not None
        assert result["content"] == "テストメッセージ"
        assert result["author_name"] == "テストユーザー"
        assert result["guild_id"] == 123456789
        assert result["channel_id"] == 987654321

    @pytest.mark.asyncio
    async def test_on_message_handles_dm(self):
        """境界値: DMメッセージ（guildがNone）を処理する"""
        mock_client = MagicMock(spec=discord.Client)
        listener = MessageListener(mock_client)

        # DMメッセージを作成（guildがNone）
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.content = "DMメッセージ"
        mock_message.author.name = "テストユーザー"
        mock_message.guild = None
        mock_message.channel.id = 111111111

        # on_messageを呼び出し
        result = await listener.on_message(mock_message)

        # DMメッセージも処理される（guild_idはNone）
        assert result is not None
        assert result["guild_id"] is None


class TestBotReady:
    """Bot接続のテスト"""

    @pytest.mark.asyncio
    async def test_on_ready_callback_is_called(self):
        """正常系: on_readyコールバックが呼び出される"""
        mock_callback = AsyncMock()
        client = BotClient(on_ready_callback=mock_callback)

        # on_readyを手動で呼び出し
        await client.on_ready()

        # コールバックが呼ばれたことを確認
        mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_ready_without_callback(self):
        """正常系: コールバックなしでもon_readyが動作する"""
        client = BotClient()

        # エラーなしで完了することを確認
        await client.on_ready()


class TestMessageListenerCallback:
    """メッセージリスナーのコールバックテスト"""

    @pytest.mark.asyncio
    async def test_message_callback_is_called(self):
        """正常系: メッセージ受信時にコールバックが呼ばれる"""
        mock_client = MagicMock(spec=discord.Client)
        mock_callback = AsyncMock()
        listener = MessageListener(mock_client, on_message_callback=mock_callback)

        # ユーザーからのメッセージを作成
        mock_message = MagicMock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.content = "テストメッセージ"
        mock_message.author.name = "テストユーザー"
        mock_message.guild.id = 123456789
        mock_message.channel.id = 987654321

        # on_messageを呼び出し
        await listener.on_message(mock_message)

        # コールバックが呼ばれたことを確認
        mock_callback.assert_called_once()
