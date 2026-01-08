"""Local filesystem storage provider.

ローカルファイルシステムへのストレージプロバイダー実装。
"""

from datetime import datetime
from pathlib import Path

import aiofiles
import aiofiles.os

from src.storage.base import StorageProvider


class LocalStorage(StorageProvider):
    """ローカルファイルシステムへのストレージプロバイダー.

    ファイルを以下のディレクトリ構成で保存する:
    {base_path}/{workspace_id}/{room_id}/{date}/

    Attributes:
        base_path: ベースディレクトリのパス

    Example:
        >>> storage = LocalStorage(base_path="data/files")
        >>> path = await storage.save_file(b"content", 1, 2, "photo.jpg")
        >>> print(path)  # data/files/1/2/2025-01-04/photo.jpg
    """

    def __init__(self, base_path: Path | str = "data/files") -> None:
        """LocalStorageを初期化する.

        Args:
            base_path: ベースディレクトリのパス
        """
        self.base_path = Path(base_path)

    def _sanitize_filename(self, filename: str) -> str:
        """ファイル名をサニタイズしてパストラバーサルを防止する.

        Args:
            filename: 元のファイル名

        Returns:
            サニタイズされたファイル名
        """
        # パス区切り文字を除去してベース名のみ取得
        safe_name = Path(filename).name

        # 空になった場合はデフォルト名を使用
        if not safe_name or safe_name in (".", ".."):
            safe_name = "unnamed_file"

        return safe_name

    async def save_file(
        self,
        content: bytes,
        workspace_id: int,
        room_id: int,
        filename: str,
    ) -> Path:
        """ファイルをローカルファイルシステムに保存する.

        ディレクトリ構成: {base_path}/{workspace_id}/{room_id}/{date}/
        ファイル名が重複する場合は連番を付与する。
        ファイル名はサニタイズされ、パストラバーサルを防止する。

        Args:
            content: ファイルの内容（バイナリ）
            workspace_id: Workspace ID
            room_id: Room ID
            filename: ファイル名

        Returns:
            保存先のパス
        """
        # ファイル名をサニタイズ（パストラバーサル対策）
        safe_filename = self._sanitize_filename(filename)

        date_str = datetime.now().strftime("%Y-%m-%d")
        target_dir = self.base_path / str(workspace_id) / str(room_id) / date_str

        # ディレクトリを作成（存在しない場合）
        target_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名重複時の処理
        target_path = target_dir / safe_filename
        if target_path.exists():
            stem = target_path.stem
            suffix = target_path.suffix
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        # ファイルを非同期で書き込み
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)

        return target_path

    async def get_file(self, file_path: Path) -> bytes:
        """ファイルを取得する.

        Args:
            file_path: ファイルのパス

        Returns:
            ファイルの内容（バイナリ）

        Raises:
            FileNotFoundError: ファイルが見つからない場合
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def delete_file(self, file_path: Path) -> bool:
        """ファイルを削除する.

        Args:
            file_path: ファイルのパス

        Returns:
            削除成功ならTrue、ファイルが存在しない場合はFalse
        """
        if not file_path.exists():
            return False

        await aiofiles.os.remove(file_path)
        return True
