"""会話要約サービス

メッセージのリストを受け取り、AIを使用して要約を生成します。

Example:
    >>> from src.ai.router import AIRouter
    >>> router = AIRouter.from_yaml("config.yaml")
    >>> summarizer = Summarizer(router)
    >>> summary = await summarizer.summarize(messages, days=7)
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from src.ai.base import AIProvider, AIProviderError
from src.ai.providers.anthropic import AnthropicProvider
from src.ai.providers.google import GoogleProvider
from src.ai.providers.groq import GroqProvider
from src.ai.providers.openai import OpenAIProvider
from src.ai.router import AIRouter


class SummaryError(Exception):
    """要約処理エラー

    要約の生成に失敗した場合に発生します。
    """

    pass


class Summarizer:
    """会話要約サービス

    AIRouterを使用して適切なプロバイダーを選択し、
    メッセージの要約を生成します。

    Attributes:
        _router: AIRouter インスタンス

    Example:
        >>> summarizer = Summarizer(router)
        >>> summary = await summarizer.summarize(messages, days=7)
    """

    # 要約の最大入力メッセージ数
    MAX_MESSAGES = 100

    # デフォルトの日数
    DEFAULT_DAYS = 7

    def __init__(self, router: AIRouter) -> None:
        """Summarizerを初期化

        Args:
            router: AIRouterインスタンス
        """
        self._router = router

    async def summarize(
        self,
        messages: list[dict[str, Any]],
        days: int | None = None,
        workspace_id: str | None = None,
        room_id: str | None = None,
    ) -> str:
        """メッセージを要約

        Args:
            messages: メッセージのリスト。各メッセージは以下のキーを持つ:
                - sender_name: 発言者名
                - content: メッセージ内容
                - timestamp: 発言日時 (datetime)
            days: 要約対象の日数（Noneの場合はフィルタリングなし）
            workspace_id: Workspace ID（ルーティングに使用）
            room_id: Room ID（ルーティングに使用）

        Returns:
            生成された要約テキスト

        Raises:
            SummaryError: 要約の生成に失敗した場合
        """
        if not messages:
            return "要約するメッセージがありません。"

        # 日付フィルタリング
        if days is not None:
            messages = self._filter_by_days(messages, days)
            if not messages:
                return f"直近{days}日間にメッセージがありません。"

        # メッセージ数制限
        if len(messages) > self.MAX_MESSAGES:
            messages = messages[: self.MAX_MESSAGES]

        # プロンプト生成
        prompt = self._build_prompt(messages)

        # AIプロバイダーを取得
        try:
            provider = self._get_provider(workspace_id, room_id)
            result = await provider.generate(
                prompt,
                temperature=0.3,  # 要約は低めの温度で
                max_tokens=1024,
            )
            return result
        except AIProviderError as e:
            raise SummaryError(f"要約の生成に失敗しました: {e}") from e

    def _filter_by_days(self, messages: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
        """日数でメッセージをフィルタリング

        Args:
            messages: メッセージのリスト
            days: フィルタリングする日数

        Returns:
            フィルタリングされたメッセージのリスト
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        default_timestamp = datetime.min.replace(tzinfo=UTC)
        return [msg for msg in messages if msg.get("timestamp", default_timestamp) >= cutoff]

    def _build_prompt(self, messages: list[dict[str, Any]]) -> str:
        """要約用プロンプトを生成

        Args:
            messages: メッセージのリスト

        Returns:
            生成されたプロンプト
        """
        # メッセージを時系列順にソート
        sorted_messages = sorted(messages, key=lambda m: m.get("timestamp", datetime.min))

        # メッセージテキストを構築
        message_texts = []
        for msg in sorted_messages:
            sender = msg.get("sender_name", "不明")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            if timestamp:
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                message_texts.append(f"[{time_str}] {sender}: {content}")
            else:
                message_texts.append(f"{sender}: {content}")

        conversation = "\n".join(message_texts)

        prompt = f"""以下の会話を要約してください。

## 要約の形式
- 【決定事項】重要な決定や合意事項をリストアップ
- 【未決事項】まだ決まっていない事項や検討が必要な事項をリストアップ
- 【アクションアイテム】誰が何をするか（もしあれば）

## 会話内容
{conversation}

## 要約"""

        return prompt

    # プロバイダー名とクラスのマッピング
    _PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "groq": GroqProvider,
    }

    def _get_provider(
        self, workspace_id: str | None = None, room_id: str | None = None
    ) -> AIProvider:
        """AIプロバイダーを取得

        config.yamlの設定に基づいて適切なプロバイダーを返す。
        OpenAI, Anthropic, Google, Groqをサポート。

        Args:
            workspace_id: Workspace ID
            room_id: Room ID

        Returns:
            AIProviderインスタンス

        Raises:
            SummaryError: プロバイダーの取得に失敗した場合
        """
        try:
            provider_info = self._router.get_provider_info(
                "summary",
                workspace_id=workspace_id,
                room_id=room_id,
            )
            provider_name = provider_info["provider"]
            provider_config = self._router.get_provider_config(provider_name)

            # プロバイダークラスを取得
            provider_class = self._PROVIDER_CLASSES.get(provider_name)
            if provider_class is None:
                raise SummaryError(
                    f"未対応のプロバイダー: {provider_name}。"
                    f"対応プロバイダー: {list(self._PROVIDER_CLASSES.keys())}"
                )

            # 全プロバイダーは api_key, model を受け取る共通インターフェース
            # cast(Any, ...) で型チェックを回避（各プロバイダーは同一シグネチャを持つ）
            return cast(Any, provider_class)(
                api_key=provider_config["api_key"],
                model=provider_info["model"],
            )
        except Exception as e:
            if isinstance(e, SummaryError):
                raise
            raise SummaryError(f"プロバイダーの取得に失敗しました: {e}") from e
