from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: datetime


class InMemoryCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._store: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if not entry:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._store[key] = CacheEntry(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=self._ttl_seconds),
        )

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
