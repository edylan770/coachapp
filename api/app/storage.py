"""Object storage behind a small interface (spec §2: S3-compatible).

v1 ships a local-filesystem backend (good for dev/single-node); an S3/MinIO
implementation can be added without touching callers — they only see
save/load/exists keyed by opaque string keys.
"""

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class ObjectStorage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...

    def load(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


class LocalObjectStorage:
    def __init__(self, base_dir: Path):
        self._base = base_dir.resolve()

    def _path(self, key: str) -> Path:
        path = (self._base / key).resolve()
        if not path.is_relative_to(self._base):
            raise ValueError("invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValueError:
            return False


@lru_cache
def get_storage() -> ObjectStorage:
    return LocalObjectStorage(Path(get_settings().storage_dir))
