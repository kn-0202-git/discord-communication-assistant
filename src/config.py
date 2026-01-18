"""アプリケーション設定モジュール.

YAMLファイルから設定を読み込み、型安全なアクセスを提供する。
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class AppConfig:
    """アプリケーション設定クラス.

    YAMLファイルから設定を読み込み、プロパティ経由でアクセスを提供する。

    Example:
        config = AppConfig.from_yaml(Path("config.yaml"))
        drive_enabled = config.google_drive.get("enabled", False)
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """設定を初期化する.

        Args:
            config: 設定辞書
        """
        self._config = config

    @classmethod
    def from_yaml(cls, path: Path | str) -> "AppConfig":
        """YAMLファイルから設定を読み込む.

        Args:
            path: 設定ファイルのパス

        Returns:
            AppConfigインスタンス。ファイルが存在しない場合は空の設定を返す。
        """
        path = Path(path)
        if not path.exists():
            logger.info(f"Config file not found: {path}. Using empty config.")
            return cls({})

        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            logger.debug(f"Loaded config from {path}")
            return cls(config)
        except Exception as exc:
            logger.warning(f"Failed to read config file {path}: {exc}. Using empty config.")
            return cls({})

    @property
    def google_drive(self) -> dict[str, Any]:
        """Google Drive設定を取得する."""
        return self._config.get("google_drive") or {}

    @property
    def attachments(self) -> dict[str, Any]:
        """添付ファイル設定を取得する."""
        return self._config.get("attachments") or {}

    @property
    def ai_providers(self) -> dict[str, Any]:
        """AIプロバイダー設定を取得する."""
        return self._config.get("ai_providers") or {}

    @property
    def ai_routing(self) -> dict[str, Any]:
        """AIルーティング設定を取得する."""
        return self._config.get("ai_routing") or {}

    @property
    def raw(self) -> dict[str, Any]:
        """生の設定辞書を取得する."""
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得する.

        Args:
            key: 設定キー
            default: デフォルト値

        Returns:
            設定値またはデフォルト値
        """
        return self._config.get(key, default)

    def __bool__(self) -> bool:
        """設定が空でないかを確認する."""
        return bool(self._config)
