"""Google Drive storage provider.

Google Drive APIを使用してファイルを保存・取得する。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

from src.storage.base import StorageProvider

GOOGLE_DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)


class GoogleDriveStorage(StorageProvider):
    """Google Driveストレージ実装.

    ファイル保存は {workspace_id}/{room_id}/{date}/ で構成する。
    """

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        root_folder_id: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._access_token = access_token or os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN")
        self._refresh_token = refresh_token or os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN")
        self._client_id = client_id or os.getenv("GOOGLE_DRIVE_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")
        self._root_folder_id = root_folder_id
        self._session = session
        self._token_expires_at: datetime | None = None

    def _sanitize_filename(self, filename: str) -> str:
        safe_name = Path(filename).name
        if not safe_name or safe_name in (".", ".."):
            safe_name = "unnamed_file"
        return safe_name

    def _sanitize_folder_name(self, name: str) -> str:
        safe_name = name.strip().replace("\\", "_").replace("/", "_")
        if not safe_name or safe_name in (".", ".."):
            safe_name = "untitled"
        return safe_name

    def _is_token_valid(self) -> bool:
        if not self._access_token:
            return False
        if self._token_expires_at is None:
            return True
        return datetime.now(UTC) < self._token_expires_at

    async def _refresh_access_token(self) -> None:
        if not (self._refresh_token and self._client_id and self._client_secret):
            raise ValueError(
                "Google Drive OAuth settings are missing. "
                "Set GOOGLE_DRIVE_REFRESH_TOKEN, GOOGLE_DRIVE_CLIENT_ID, "
                "GOOGLE_DRIVE_CLIENT_SECRET."
            )

        session = await self._ensure_session()
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }

        async with session.post(GOOGLE_OAUTH_TOKEN_URL, data=payload) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to refresh access token: {response.status}")
            data = await response.json()

        access_token = data.get("access_token")
        if not access_token:
            raise RuntimeError("Access token missing in OAuth response")

        self._access_token = access_token
        expires_in = data.get("expires_in")
        if isinstance(expires_in, int) and expires_in > 0:
            self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
            self._token_expires_at -= TOKEN_EXPIRY_MARGIN
        else:
            self._token_expires_at = None

    async def _get_access_token(self) -> str:
        if self._is_token_valid():
            return self._access_token  # type: ignore[return-value]

        if self._refresh_token:
            await self._refresh_access_token()
            return self._access_token  # type: ignore[return-value]

        raise ValueError("GOOGLE_DRIVE_ACCESS_TOKEN is not set")

    async def _headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _find_folder(self, name: str, parent_id: str | None) -> str | None:
        session = await self._ensure_session()
        headers = await self._headers()

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
        headers = await self._headers()

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

    async def _ensure_folder_path(self, parts: list[str]) -> str:
        parent_id = self._root_folder_id
        for raw_part in parts:
            name = self._sanitize_folder_name(raw_part)
            parent_id = await self._get_or_create_folder(name, parent_id)
        return parent_id

    async def save_file(
        self,
        content: bytes,
        workspace_id: int,
        room_id: int,
        filename: str,
    ) -> Path:
        safe_filename = self._sanitize_filename(filename)
        folder_id = await self._ensure_target_folder(workspace_id, room_id)

        return await self._upload_file(content, safe_filename, folder_id)

    async def save_file_with_folder(
        self,
        content: bytes,
        filename: str,
        folder_parts: list[str],
    ) -> Path:
        safe_filename = self._sanitize_filename(filename)
        folder_id = await self._ensure_folder_path(folder_parts)

        return await self._upload_file(content, safe_filename, folder_id)

    async def _upload_file(self, content: bytes, filename: str, folder_id: str) -> Path:
        metadata = {"name": filename, "parents": [folder_id]}
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
            **(await self._headers()),
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
        headers = await self._headers()

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
        headers = await self._headers()

        async with session.delete(
            f"{GOOGLE_DRIVE_API_BASE}/files/{file_id}",
            headers=headers,
        ) as response:
            return response.status in (200, 204)
