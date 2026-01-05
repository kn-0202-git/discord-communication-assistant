"""Storage provider base class.

ストレージプロバイダーの抽象基底クラス。
ローカルストレージ、Google Drive等の差し替えを可能にする。
"""

from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):
    """ストレージプロバイダーの抽象基底クラス.

    ファイルの保存・取得を抽象化し、
    ローカルストレージやクラウドストレージを差し替え可能にする。

    Example:
        >>> class MyStorage(StorageProvider):
        ...     async def save_file(self, content, workspace_id, room_id, filename):
        ...         # 実装
        ...     async def get_file(self, file_path):
        ...         # 実装
    """

    @abstractmethod
    async def save_file(
        self,
        content: bytes,
        workspace_id: int,
        room_id: int,
        filename: str,
    ) -> Path:
        """ファイルを保存する.

        Args:
            content: ファイルの内容（バイナリ）
            workspace_id: Workspace ID
            room_id: Room ID
            filename: ファイル名

        Returns:
            保存先のパス
        """

    @abstractmethod
    async def get_file(self, file_path: Path) -> bytes:
        """ファイルを取得する.

        Args:
            file_path: ファイルのパス

        Returns:
            ファイルの内容（バイナリ）

        Raises:
            FileNotFoundError: ファイルが見つからない場合
        """

    @abstractmethod
    async def delete_file(self, file_path: Path) -> bool:
        """ファイルを削除する.

        Args:
            file_path: ファイルのパス

        Returns:
            削除成功ならTrue
        """
