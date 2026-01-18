"""Factory テスト."""

from pathlib import Path

from src.config import AppConfig
from src.factory import (
    AppComponents,
    create_ai_router,
    create_app_components,
    create_database,
    create_google_drive_storage,
)


class TestCreateDatabase:
    """create_databaseのテスト."""

    def test_creates_in_memory_database(self) -> None:
        """メモリ内データベースを作成できる."""
        db = create_database(in_memory=True)

        assert db is not None
        # テーブルが作成されていることを確認（存在しないIDで検索）
        workspace = db.get_workspace_by_discord_id("nonexistent")
        assert workspace is None

        db.close()

    def test_creates_file_database(self, tmp_path: Path) -> None:
        """ファイルデータベースを作成できる."""
        db_path = tmp_path / "test.db"

        db = create_database(db_path=db_path)

        assert db is not None
        assert db_path.exists()

        db.close()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """親ディレクトリを自動作成する."""
        db_path = tmp_path / "subdir" / "test.db"

        db = create_database(db_path=db_path)

        assert db_path.exists()

        db.close()


class TestCreateAIRouter:
    """create_ai_routerのテスト."""

    def test_returns_none_for_missing_config(self) -> None:
        """設定ファイルがない場合、Noneを返す."""
        router = create_ai_router(Path("/nonexistent/config.yaml"))

        assert router is None

    def test_creates_router_from_valid_config(self, tmp_path: Path) -> None:
        """有効な設定からルーターを作成できる."""
        config_content = """
ai_providers:
  openai:
    api_key: "test-key"
    models:
      - gpt-4o

ai_routing:
  summary:
    provider: openai
    model: gpt-4o
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        router = create_ai_router(config_file)

        assert router is not None
        provider_info = router.get_provider_info("summary")
        assert provider_info["provider"] == "openai"


class TestCreateGoogleDriveStorage:
    """create_google_drive_storageのテスト."""

    def test_returns_none_when_disabled(self) -> None:
        """無効化されている場合、Noneを返す."""
        config = AppConfig(
            {
                "google_drive": {
                    "enabled": False,
                    "auto_upload": False,
                },
            }
        )

        storage, auto_upload = create_google_drive_storage(config)

        assert storage is None
        assert auto_upload is False

    def test_returns_none_for_empty_config(self) -> None:
        """設定が空の場合、Noneを返す."""
        config = AppConfig({})

        storage, auto_upload = create_google_drive_storage(config)

        assert storage is None
        assert auto_upload is False


class TestCreateAppComponents:
    """create_app_componentsのテスト."""

    def test_creates_all_components_with_in_memory_db(self, tmp_path: Path) -> None:
        """メモリ内DBで全コンポーネントを作成できる."""
        config_content = """
ai_providers:
  openai:
    api_key: "test-key"
    models:
      - gpt-4o

ai_routing:
  summary:
    provider: openai
    model: gpt-4o
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        components = create_app_components(
            config_path=config_file,
            data_dir=tmp_path / "data",
            in_memory_db=True,
        )

        assert isinstance(components, AppComponents)
        assert components.db is not None
        assert components.storage is not None
        assert components.router is not None
        assert components.config is not None

        components.db.close()

    def test_creates_data_directory(self, tmp_path: Path) -> None:
        """データディレクトリを自動作成する."""
        data_dir = tmp_path / "new_data"

        components = create_app_components(
            config_path=tmp_path / "nonexistent.yaml",
            data_dir=data_dir,
            in_memory_db=True,
        )

        assert data_dir.exists()

        components.db.close()

    def test_router_is_none_without_config(self, tmp_path: Path) -> None:
        """設定ファイルがない場合、routerはNone."""
        components = create_app_components(
            config_path=tmp_path / "nonexistent.yaml",
            data_dir=tmp_path / "data",
            in_memory_db=True,
        )

        assert components.router is None

        components.db.close()
