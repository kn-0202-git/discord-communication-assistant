"""AI基盤モジュール

このパッケージはAIプロバイダーの抽象化レイヤーとルーティング機能を提供します。

主要なクラス:
    - AIProvider: AIプロバイダーの抽象基底クラス
    - AIRouter: 機能に応じてプロバイダーを選択するルーター

エラークラス:
    - AIProviderError: AI関連エラーの基底クラス
    - AIProviderNotConfiguredError: プロバイダー未設定エラー
    - AIQuotaExceededError: API制限超過エラー
    - AIConnectionError: 接続エラー
    - AIResponseError: 応答エラー

Example:
    >>> from src.ai import AIRouter
    >>> router = AIRouter.from_yaml("config.yaml")
    >>> info = router.get_provider_info("summary")
    >>> print(info)
    {"provider": "openai", "model": "gpt-4o-mini"}
"""

from src.ai.base import (
    AIConnectionError,
    AIProvider,
    AIProviderError,
    AIProviderNotConfiguredError,
    AIQuotaExceededError,
    AIResponseError,
)
from src.ai.router import AIRouter
from src.ai.summarizer import Summarizer, SummaryError

__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIProviderNotConfiguredError",
    "AIQuotaExceededError",
    "AIConnectionError",
    "AIResponseError",
    "AIRouter",
    "Summarizer",
    "SummaryError",
]
