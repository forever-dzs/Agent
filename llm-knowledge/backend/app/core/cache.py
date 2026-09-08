import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional


class TTLCache:
    """轻量级 TTL 缓存，用于减少重复检索与 prompt 重复调用成本。"""

    def __init__(self, ttl_seconds: int = 1800, max_entries: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            value = self._data.get(key)
            if not value:
                return None

            expires_at = value["expires_at"]
            if time.time() > expires_at:
                self._data.pop(key, None)
                return None

            self._data.move_to_end(key)
            return value["value"]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            expires_at = time.time() + (ttl_seconds or self.ttl_seconds)
            self._data[key] = {"value": value, "expires_at": expires_at}
            self._data.move_to_end(key)

            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
