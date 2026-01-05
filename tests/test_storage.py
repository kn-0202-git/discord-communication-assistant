"""Storage tests.

ストレージプロバイダーのテスト。
"""

from pathlib import Path

import pytest

from src.storage.local import LocalStorage


class TestLocalStorage:
    """LocalStorageのテスト."""

    @pytest.fixture
    def storage(self, tmp_path: Path) -> LocalStorage:
        """一時ディレクトリを使用したストレージを作成."""
        return LocalStorage(base_path=tmp_path)

    @pytest.mark.asyncio
    async def test_save_file_creates_file(self, storage: LocalStorage) -> None:
        """正常系: ファイルが保存される."""
        content = b"test content"

        path = await storage.save_file(
            content=content,
            workspace_id=1,
            room_id=2,
            filename="test.txt",
        )

        assert path.exists()
        assert path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_save_file_creates_directory_structure(self, storage: LocalStorage) -> None:
        """正常系: 正しいディレクトリ構成で保存される."""
        path = await storage.save_file(
            content=b"test",
            workspace_id=123,
            room_id=456,
            filename="photo.jpg",
        )

        # パスに workspace_id と room_id が含まれることを確認
        path_str = str(path)
        assert "123" in path_str
        assert "456" in path_str
        assert "photo.jpg" in path_str

    @pytest.mark.asyncio
    async def test_save_file_handles_filename_collision(self, storage: LocalStorage) -> None:
        """境界値: ファイル名重複時にリネームされる."""
        # 同じファイル名で2回保存
        path1 = await storage.save_file(
            content=b"content1",
            workspace_id=1,
            room_id=1,
            filename="test.txt",
        )
        path2 = await storage.save_file(
            content=b"content2",
            workspace_id=1,
            room_id=1,
            filename="test.txt",
        )

        # パスが異なることを確認
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()
        # 2つ目は連番が付与される
        assert "test_1.txt" in str(path2)

    @pytest.mark.asyncio
    async def test_save_file_handles_multiple_collisions(self, storage: LocalStorage) -> None:
        """境界値: 複数回のファイル名重複."""
        paths = []
        for i in range(5):
            path = await storage.save_file(
                content=f"content{i}".encode(),
                workspace_id=1,
                room_id=1,
                filename="test.txt",
            )
            paths.append(path)

        # 全て異なるパス
        assert len(set(paths)) == 5
        # 全て存在する
        for path in paths:
            assert path.exists()

    @pytest.mark.asyncio
    async def test_get_file_returns_content(self, storage: LocalStorage) -> None:
        """正常系: ファイルの内容を取得できる."""
        content = b"test content for get"

        path = await storage.save_file(
            content=content,
            workspace_id=1,
            room_id=1,
            filename="get_test.txt",
        )

        retrieved = await storage.get_file(path)
        assert retrieved == content

    @pytest.mark.asyncio
    async def test_get_file_raises_for_nonexistent(self, storage: LocalStorage) -> None:
        """異常系: 存在しないファイルでFileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await storage.get_file(Path("/nonexistent/file.txt"))

    @pytest.mark.asyncio
    async def test_delete_file_removes_file(self, storage: LocalStorage) -> None:
        """正常系: ファイルが削除される."""
        path = await storage.save_file(
            content=b"to delete",
            workspace_id=1,
            room_id=1,
            filename="delete_test.txt",
        )
        assert path.exists()

        result = await storage.delete_file(path)

        assert result is True
        assert not path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_returns_false_for_nonexistent(self, storage: LocalStorage) -> None:
        """異常系: 存在しないファイル削除はFalseを返す."""
        result = await storage.delete_file(Path("/nonexistent/file.txt"))
        assert result is False

    @pytest.mark.asyncio
    async def test_save_binary_file(self, storage: LocalStorage) -> None:
        """正常系: バイナリファイル（画像など）を保存できる."""
        # 簡易的なPNGヘッダー
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        path = await storage.save_file(
            content=png_header,
            workspace_id=1,
            room_id=1,
            filename="image.png",
        )

        assert path.exists()
        assert path.read_bytes() == png_header
