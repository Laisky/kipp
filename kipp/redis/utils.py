from __future__ import annotations

import logging
import random
import time

import redis

# Poll interval (seconds) when waiting for a key to appear.
# Kept short to balance latency vs CPU usage in busy-wait loops.
WAIT_DB_KEY_DURATION: float = 0.1

# Batch size hint for SCAN commands to limit per-call work on the server.
SCAN_COUNT: int = 10


class RedisUtils:
    """High-level Redis helpers with blocking reads and automatic list trimming.

    Wraps a ``redis.Redis`` client to provide convenience methods ported
    from the Go codebase (WaitDBKeyDuration / ScanCount pattern).
    All string values are decoded from bytes to UTF-8 transparently.
    """

    def __init__(
        self,
        client: redis.Redis,
        logger: logging.Logger | None = None,
    ) -> None:
        self.client = client
        self.logger = logger or logging.getLogger("RedisUtils")

    def _decode(self, data: bytes | str) -> str:
        """Normalize redis response to str, handling both bytes and str returns."""
        return data.decode("utf-8") if isinstance(data, bytes) else data

    def get_item(self, key: str) -> str:
        """Get a single value by key, returning empty string if the key does not exist."""
        self.logger.debug("get redis item", extra={"key": key})
        data = self.client.get(key)
        if data is not None:
            return self._decode(data)
        return ""

    def get_item_blocking(self, key: str, delete: bool = True) -> str:
        """Poll until the key exists, then return its value.

        When ``delete=True`` (default), the key is atomically read and
        deleted using WATCH/MULTI to prevent other consumers from reading
        the same value. On WatchError (concurrent modification), the
        transaction is retried.
        """
        while True:
            if not delete:
                data = self.client.get(key)
                if data is None:
                    time.sleep(WAIT_DB_KEY_DURATION)
                    continue
                return self._decode(data)

            try:
                with self.client.pipeline() as pipe:
                    while True:
                        try:
                            # Optimistic locking: watch the key so the
                            # transaction fails if another client modifies it.
                            pipe.watch(key)
                            data = pipe.get(key)
                            if data is None:
                                pipe.unwatch()
                                time.sleep(WAIT_DB_KEY_DURATION)
                                break
                            pipe.multi()
                            pipe.delete(key)
                            pipe.execute()
                            return self._decode(data)
                        except redis.WatchError:
                            time.sleep(WAIT_DB_KEY_DURATION)
                            continue
            except Exception as err:
                self.logger.error(
                    "Error in get_item_blocking", extra={"key": key, "error": err}
                )
                time.sleep(WAIT_DB_KEY_DURATION)
                continue

    def set_item(self, key: str, val: str, exp: int) -> None:
        """Set a key with a TTL in seconds."""
        self.logger.debug("put redis item", extra={"key": key})
        self.client.set(key, val, ex=exp)

    def get_item_with_prefix(self, key_prefix: str) -> dict[str, str]:
        """Return all key-value pairs matching the given prefix.

        Uses SCAN (not KEYS) to avoid blocking the server on large keyspaces.
        Empty prefix is rejected to prevent accidental full-database scans.
        """
        self.logger.debug(
            "get redis item with prefix", extra={"key_prefix": key_prefix}
        )
        if key_prefix == "":
            raise ValueError("do not scan all keys")

        keys: list[bytes | str] = list(
            self.client.scan_iter(match=key_prefix + "*", count=SCAN_COUNT)
        )
        items: dict[str, str] = {}
        if not keys:
            return items

        values = self.client.mget(keys)
        for key, val in zip(keys, values):
            if val is None:
                continue
            items[self._decode(key)] = self._decode(val)

        return items

    def lpop_keys_blocking(self, keys: list[str]) -> tuple[str, str]:
        """Round-robin LPOP across multiple lists until one yields a value.

        Returns the (key, value) pair from whichever list had data first.
        Useful for consuming from multiple task queues with equal priority.
        """
        while True:
            for key in keys:
                val = self.client.lpop(key)
                if val is not None:
                    value = self._decode(val)
                    return key, value
            time.sleep(WAIT_DB_KEY_DURATION)

    def rpush(self, key: str, *payloads: str | bytes) -> None:
        """Append values to a list, probabilistically trimming to prevent unbounded growth.

        Length is checked only ~1% of the time to amortize the LLEN cost.
        When the list exceeds 100 elements, it is trimmed to the last 10
        to avoid memory issues from forgotten consumer queues.
        """
        length = 0
        # Probabilistic check avoids an LLEN call on every push
        if random.randint(0, 99) == 0:
            length = self.client.llen(key)

        if length >= 100:
            self.client.ltrim(key, -10, -1)
            self.logger.info("trim array", extra={"key": key})

        self.client.rpush(key, *payloads)
