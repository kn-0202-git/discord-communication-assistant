"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_ai_provider():
    """AIプロバイダーのモック"""
    provider = AsyncMock()
    provider.generate.return_value = "これはモックの応答です"
    provider.embed.return_value = [0.1] * 1536
    return provider


@pytest.fixture
def mock_ai_router(mock_ai_provider):
    """AIルーターのモック"""
    router = AsyncMock()
    router.get_provider.return_value = mock_ai_provider
    return router
