"""Storage module.

ファイルストレージの抽象化レイヤー。
"""

from src.storage.base import StorageProvider
from src.storage.local import LocalStorage

__all__ = ["StorageProvider", "LocalStorage"]
