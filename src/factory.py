"""アプリケーションコンポーネントのファクトリモジュール.

Bot起動に必要なコンポーネントの初期化を一元管理する。
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from src.ai.router import AIRouter
from src.config import AppConfig
from src.db.database import Database
from src.storage.google_drive import GoogleDriveStorage
from src.storage.local import LocalStorage

logger = logging.getLogger(__name__)


@dataclass
class AppComponents:
    """アプリケーションコンポーネントの集約クラス.

    Bot起動に必要な全コンポーネントを保持する。

    Attributes:
        db: データベースインスタンス
        storage: ローカルストレージインスタンス
        router: AIルーター（未設定の場合はNone）
        drive_storage: Google Driveストレージ（未設定の場合はNone）
        drive_auto_upload: 自動アップロードフラグ
        config: アプリケーション設定
    """

    db: Database
    storage: LocalStorage
    router: AIRouter | None
    drive_storage: GoogleDriveStorage | None
    drive_auto_upload: bool
    config: AppConfig


def create_database(
    db_path: Path | str | None = None,
    in_memory: bool = False,
) -> Database:
    """データベースを作成する.

    Args:
        db_path: データベースファイルのパス（in_memory=Trueの場合は無視）
        in_memory: メモリ内データベースを使用するかどうか（テスト用）

    Returns:
        初期化されたDatabaseインスタンス
    """
    if in_memory:
        db = Database(":memory:")
        logger.info("Database initialized: in-memory")
    else:
        path = Path(db_path) if db_path else Path("data/app.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        db = Database(f"sqlite:///{path}")
        logger.info(f"Database initialized: {path}")

    db.create_tables()
    return db


def create_ai_router(config_path: Path | str) -> AIRouter | None:
    """AIルーターを作成する.

    Args:
        config_path: 設定ファイルのパス

    Returns:
        AIRouterインスタンス。設定ファイルがない場合はNone。
    """
    config_path = Path(config_path)
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}. AI features may not work.")
        return None

    try:
        router = AIRouter.from_yaml(str(config_path))
        logger.info("AI Router initialized from config.yaml")
        return router
    except Exception as exc:
        logger.warning(f"Failed to initialize AI Router: {exc}")
        return None


def create_google_drive_storage(
    config: AppConfig,
) -> tuple[GoogleDriveStorage | None, bool]:
    """Google Driveストレージを作成する.

    Args:
        config: アプリケーション設定

    Returns:
        (GoogleDriveStorageインスタンスまたはNone, 自動アップロードフラグ)
    """
    drive_settings = config.google_drive
    drive_auto_upload = bool(drive_settings.get("auto_upload", False))
    drive_enabled = bool(drive_settings.get("enabled", False)) or drive_auto_upload

    if not drive_enabled:
        return None, False

    root_folder_id = drive_settings.get("root_folder_id")
    try:
        drive_storage = GoogleDriveStorage(root_folder_id=root_folder_id)
        logger.info("Google Drive storage initialized")
        return drive_storage, drive_auto_upload
    except Exception as exc:
        logger.warning(f"Failed to initialize Google Drive storage: {exc}")
        return None, False


def create_app_components(
    config_path: Path | str = "config.yaml",
    data_dir: Path | str = "data",
    in_memory_db: bool = False,
) -> AppComponents:
    """アプリケーションコンポーネントを生成する.

    Bot起動に必要な全コンポーネントを初期化して返す。

    Args:
        config_path: 設定ファイルのパス
        data_dir: データディレクトリのパス
        in_memory_db: メモリ内データベースを使用するかどうか（テスト用）

    Returns:
        初期化されたAppComponentsインスタンス
    """
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    # 設定読み込み（1度だけ）
    config = AppConfig.from_yaml(config_path)

    # Database
    db = create_database(data_dir / "app.db", in_memory=in_memory_db)

    # Storage
    storage = LocalStorage(base_path=data_dir / "files")
    logger.info(f"Storage initialized: {storage.base_path}")

    # AIRouter
    router = create_ai_router(config_path)

    # Google Drive
    drive_storage, drive_auto_upload = create_google_drive_storage(config)

    return AppComponents(
        db=db,
        storage=storage,
        router=router,
        drive_storage=drive_storage,
        drive_auto_upload=drive_auto_upload,
        config=config,
    )
