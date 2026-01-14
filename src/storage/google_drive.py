"""Google Drive storage provider.

Google Drive APIを使用してファイルを保存・取得する。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

from src.storage.base import StorageProvider

GOOGLE_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveStorage(StorageProvider):
    """Google Driveストレージ実装.

    ファイル保存は {workspace_id}/{room_id}/{date}/ で構成する。
    """

    def __init__(
        self,
        access_token: str | None = None,
        root_folder_id: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._access_token = access_token or os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN")
        self._root_folder_id = root_folder_id
        self._session = session

    def _sanitize_filename(self, filename: str) -> str:
        safe_name = Path(filename).name
        if not safe_name or safe_name in (".", ".."):
            safe_name = "unnamed_file"
        return safe_name

    def _headers(self) -> dict[str, str]:
        if not self._access_token:
            raise ValueError("GOOGLE_DRIVE_ACCESS_TOKEN is not set")
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _find_folder(self, name: str, parent_id: str | None) -> str | None:
        session = await self._ensure_session()
        headers = self._headers()

        parent_clause = f"'{parent_id}' in parents and " if parent_id else ""
        query = (
            f"name = '{name}' and {parent_clause}"
            f"mimeType = '{FOLDER_MIME_TYPE}' and trashed = false"
        )

        params = {"q": query, "fields": "files(id,name)"}

        async with session.get(
            f"{GOOGLE_DRIVE_API_BASE}/files", headers=headers, params=params
        ) as response:
            if response.status != 200:
                return None
            payload = await response.json()

        files = payload.get("files", [])
        if not files:
            return None
        return files[0]["id"]

    async def _create_folder(self, name: str, parent_id: str | None) -> str:
        session = await self._ensure_session()
        headers = self._headers()

        metadata: dict[str, Any] = {"name": name, "mimeType": FOLDER_MIME_TYPE}
        if parent_id:
            metadata["parents"] = [parent_id]

        async with session.post(
            f"{GOOGLE_DRIVE_API_BASE}/files",
            headers=headers,
            json=metadata,
            params={"fields": "id"},
        ) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"Failed to create folder: {response.status}")
            payload = await response.json()

        return payload["id"]

    async def _get_or_create_folder(self, name: str, parent_id: str | None) -> str:
        folder_id = await self._find_folder(name, parent_id)
        if folder_id:
            return folder_id
        return await self._create_folder(name, parent_id)

    async def _ensure_target_folder(self, workspace_id: int, room_id: int) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        parent_id = self._root_folder_id

        workspace_folder = await self._get_or_create_folder(str(workspace_id), parent_id)
        room_folder = await self._get_or_create_folder(str(room_id), workspace_folder)
        date_folder = await self._get_or_create_folder(date_str, room_folder)

        return date_folder

    async def save_file(
        self,
        content: bytes,
        workspace_id: int,
        room_id: int,
        filename: str,
    ) -> Path:
        safe_filename = self._sanitize_filename(filename)
        folder_id = await self._ensure_target_folder(workspace_id, room_id)

        metadata = {"name": safe_filename, "parents": [folder_id]}
        boundary = f"==============={uuid.uuid4().hex}"

        body = (
            (
                f"--{boundary}\r\n"
                "Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n"
                f"--{boundary}\r\n"
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + content
            + f"\r\n--{boundary}--".encode()
        )

        headers = {
            **self._headers(),
            "Content-Type": f"multipart/related; boundary={boundary}",
        }

        session = await self._ensure_session()
        async with session.post(
            f"{GOOGLE_DRIVE_UPLOAD_BASE}/files",
            headers=headers,
            params={"uploadType": "multipart", "fields": "id"},
            data=body,
        ) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"Failed to upload file: {response.status}")
            payload = await response.json()

        return Path(payload["id"])

    async def get_file(self, file_path: Path) -> bytes:
        file_id = str(file_path)
        session = await self._ensure_session()
        headers = self._headers()

        async with session.get(
            f"{GOOGLE_DRIVE_API_BASE}/files/{file_id}",
            headers=headers,
            params={"alt": "media"},
        ) as response:
            if response.status != 200:
                raise FileNotFoundError(f"File not found: {file_id}")
            return await response.read()

    async def delete_file(self, file_path: Path) -> bool:
        file_id = str(file_path)
        session = await self._ensure_session()
        headers = self._headers()

        async with session.delete(
            f"{GOOGLE_DRIVE_API_BASE}/files/{file_id}",
            headers=headers,
        ) as response:
            return response.status in (200, 204)
