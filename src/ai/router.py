"""AIプロバイダーのルーティング

機能（purpose）に応じて適切なAIプロバイダーを選択します。
優先順位: Room設定 > Workspace設定 > グローバル設定

Example:
    >>> router = AIRouter.from_yaml("config.yaml")
    >>> provider_info = router.get_provider_info("summary", workspace_id="workspace_a")
    >>> print(provider_info)
    {"provider": "google", "model": "gemini-1.5-flash"}
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml

from src.ai.base import AIProviderNotConfiguredError


class AIRouter:
    """機能に応じたAIプロバイダーを選択するルーター

    config.yamlの設定に基づいて、適切なプロバイダー情報を返します。
    実際のプロバイダーインスタンスの生成は行わず、プロバイダー情報
    （provider名とmodel名）のみを返します。

    優先順位:
        1. Room設定（room_overrides）
        2. Workspace設定（workspace_overrides）
        3. グローバル設定（ai_routing）

    Attributes:
        _config: 設定辞書

    Example:
        >>> config = {
        ...     "ai_providers": {"openai": {"api_key": "...", "models": ["gpt-4o"]}},
        ...     "ai_routing": {"summary": {"provider": "openai", "model": "gpt-4o"}},
        ... }
        >>> router = AIRouter(config)
        >>> router.get_provider_info("summary")
        {"provider": "openai", "model": "gpt-4o"}
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """AIRouterを初期化

        Args:
            config: 設定辞書。以下のキーが必要:
                - ai_providers: プロバイダーの設定
                - ai_routing: 機能ごとのデフォルト設定

        Raises:
            ValueError: 必要な設定が不足している場合
        """
        self._validate_config(config)
        self._config = config

    def _validate_config(self, config: dict[str, Any]) -> None:
        """設定のバリデーション

        Args:
            config: 検証する設定辞書

        Raises:
            ValueError: 必要な設定が不足している場合
        """
        if not config:
            raise ValueError("Config cannot be empty. Required keys: ai_providers, ai_routing")

        if "ai_providers" not in config:
            raise ValueError("Config must contain 'ai_providers' key")

        if "ai_routing" not in config:
            raise ValueError("Config must contain 'ai_routing' key")

    def get_provider_info(
        self,
        purpose: str,
        workspace_id: str | None = None,
        room_id: str | None = None,
    ) -> dict[str, str]:
        """プロバイダー情報を取得

        指定されたpurpose（機能）に対応するプロバイダー情報を返します。
        優先順位: Room設定 > Workspace設定 > グローバル設定

        Args:
            purpose: 機能名（例: "summary", "rag_answer", "search_embedding"）
            workspace_id: Workspace ID（オプション）
            room_id: Room ID（オプション）

        Returns:
            プロバイダー情報 {"provider": str, "model": str}

        Raises:
            AIProviderNotConfiguredError: 設定が見つからない場合

        Example:
            >>> router.get_provider_info("summary")
            {"provider": "openai", "model": "gpt-4o-mini"}

            >>> router.get_provider_info("summary", workspace_id="workspace_a")
            {"provider": "google", "model": "gemini-1.5-flash"}
        """
        # 1. Room設定を確認
        if room_id:
            room_overrides = self._config.get("room_overrides", {})
            if room_id in room_overrides and purpose in room_overrides[room_id]:
                return self._validate_and_return(room_overrides[room_id][purpose], purpose)

        # 2. Workspace設定を確認
        if workspace_id:
            workspace_overrides = self._config.get("workspace_overrides", {})
            if workspace_id in workspace_overrides and purpose in workspace_overrides[workspace_id]:
                return self._validate_and_return(
                    workspace_overrides[workspace_id][purpose], purpose
                )

        # 3. グローバル設定を確認
        ai_routing = self._config.get("ai_routing", {})
        if purpose in ai_routing:
            return self._validate_and_return(ai_routing[purpose], purpose)

        # 設定が見つからない
        raise AIProviderNotConfiguredError(purpose)

    def _validate_and_return(self, provider_info: dict[str, str], purpose: str) -> dict[str, str]:
        """プロバイダー情報を検証して返す

        Args:
            provider_info: プロバイダー情報
            purpose: 機能名

        Returns:
            検証済みのプロバイダー情報

        Raises:
            AIProviderNotConfiguredError: プロバイダーが未設定の場合
        """
        provider_name = provider_info.get("provider")
        model_name = provider_info.get("model")

        if not provider_name or not model_name:
            raise AIProviderNotConfiguredError(purpose)

        # プロバイダーがai_providersに存在するか確認
        ai_providers = self._config.get("ai_providers", {})
        if provider_name not in ai_providers:
            raise AIProviderNotConfiguredError(purpose, provider=provider_name)

        return {"provider": provider_name, "model": model_name}

    def get_fallback_info(self, purpose: str) -> list[dict[str, str]]:
        """フォールバックプロバイダー情報のリストを取得

        Args:
            purpose: 機能名

        Returns:
            フォールバックプロバイダー情報のリスト。未設定の場合は空リスト。

        Example:
            >>> router.get_fallback_info("summary")
            [
                {"provider": "openai", "model": "gpt-4o-mini"},
                {"provider": "google", "model": "gemini-1.5-flash"},
            ]
        """
        fallback = self._config.get("ai_fallback", {})
        if purpose not in fallback:
            return []

        return [
            {"provider": item["provider"], "model": item["model"]} for item in fallback[purpose]
        ]

    def get_provider_config(self, provider_name: str) -> dict[str, Any]:
        """プロバイダーの設定を取得

        Args:
            provider_name: プロバイダー名

        Returns:
            プロバイダーの設定（api_key, models等）

        Raises:
            AIProviderNotConfiguredError: プロバイダーが未設定の場合
        """
        ai_providers = self._config.get("ai_providers", {})
        if provider_name not in ai_providers:
            raise AIProviderNotConfiguredError("provider lookup", provider=provider_name)
        return ai_providers[provider_name]

    def list_purposes(self) -> list[str]:
        """設定されているpurpose（機能）の一覧を取得

        Returns:
            purpose名のリスト
        """
        return list(self._config.get("ai_routing", {}).keys())

    def list_providers(self) -> list[str]:
        """設定されているプロバイダーの一覧を取得

        Returns:
            プロバイダー名のリスト
        """
        return list(self._config.get("ai_providers", {}).keys())

    @classmethod
    def from_yaml(cls, file_path: str) -> "AIRouter":
        """YAMLファイルからAIRouterを作成

        環境変数（${VAR_NAME}形式）を展開してから設定を読み込みます。

        Args:
            file_path: YAMLファイルのパス

        Returns:
            AIRouterインスタンス

        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: 設定が不正な場合
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            content = f.read()

        # 環境変数を展開
        expanded_content = cls._expand_env_vars(content)

        config = yaml.safe_load(expanded_content)
        return cls(config)

    @staticmethod
    def _expand_env_vars(content: str) -> str:
        """文字列内の環境変数を展開

        ${VAR_NAME}形式の環境変数参照を実際の値に置換します。
        未定義の環境変数は空文字列に置換されます。

        Args:
            content: 環境変数を含む文字列

        Returns:
            環境変数が展開された文字列
        """
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return re.sub(pattern, replace, content)

    @classmethod
    def from_default_config(cls) -> "AIRouter":
        """デフォルトの設定ファイルからAIRouterを作成

        プロジェクトルートのconfig.yamlを読み込みます。

        Returns:
            AIRouterインスタンス
        """
        # プロジェクトルートのconfig.yamlを探す
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # src/ai/ -> src/ -> project_root/
        config_path = project_root / "config.yaml"

        return cls.from_yaml(str(config_path))
