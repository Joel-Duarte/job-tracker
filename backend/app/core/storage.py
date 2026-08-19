import os
from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Abstract storage provider interface for host filesystem operations."""

    @abstractmethod
    def read_text(self, path: str) -> str | None:
        """Reads text content from a file path. Returns None if file does not exist or fails."""
        pass

    @abstractmethod
    def write_text(self, path: str, content: str) -> bool:
        """Writes text content to a file path. Returns True on success, False on error."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Checks if a file exists at path."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local disk host filesystem storage provider implementation."""

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def read_text(self, path: str) -> str | None:
        if not self.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def write_text(self, path: str, content: str) -> bool:
        try:
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            tmp_path = f"{path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
            return True
        except Exception:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception:
                return False


_DEFAULT_STORAGE_PROVIDER: StorageProvider = LocalStorageProvider()


def get_storage_provider() -> StorageProvider:
    """Returns the globally configured StorageProvider instance."""
    return _DEFAULT_STORAGE_PROVIDER


def set_storage_provider(provider: StorageProvider) -> None:
    """Configures a custom StorageProvider implementation (e.g. for testing)."""
    global _DEFAULT_STORAGE_PROVIDER
    _DEFAULT_STORAGE_PROVIDER = provider
