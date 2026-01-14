"""Google Drive storage tests."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.storage.google_drive import GoogleDriveStorage


def test_sanitize_filename() -> None:
    storage = GoogleDriveStorage(access_token="token")
    assert storage._sanitize_filename("../evil.txt") == "evil.txt"
    assert storage._sanitize_filename("") == "unnamed_file"


@pytest.mark.asyncio
async def test_save_file_uploads_and_returns_id() -> None:
    storage = GoogleDriveStorage(access_token="token")

    storage._ensure_target_folder = AsyncMock(return_value="folder-id")

    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"id": "file-id"})
    response.__aenter__.return_value = response
    response.__aexit__.return_value = None

    session = AsyncMock()
    session.post.return_value = response
    storage._ensure_session = AsyncMock(return_value=session)

    result = await storage.save_file(b"data", 1, 2, "file.txt")

    assert result == Path("file-id")


@pytest.mark.asyncio
async def test_get_file_returns_bytes() -> None:
    storage = GoogleDriveStorage(access_token="token")

    response = AsyncMock()
    response.status = 200
    response.read = AsyncMock(return_value=b"data")
    response.__aenter__.return_value = response
    response.__aexit__.return_value = None

    session = AsyncMock()
    session.get.return_value = response
    storage._ensure_session = AsyncMock(return_value=session)

    result = await storage.get_file(Path("file-id"))

    assert result == b"data"
