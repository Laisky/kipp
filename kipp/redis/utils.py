import time
import random
import logging

import redis

# Constants similar to WaitDBKeyDuration and ScanCount in Go
WAIT_DB_KEY_DURATION = 0.1
SCAN_COUNT = 10


class RedisUtils:
    """RedisUtils is a utility class for interacting with Redis.
    """
    def __init__(self, client: redis.Redis, logger: logging.Logger = None):
        self.client = client
        self.logger = logger or logging.getLogger("RedisUtils")

    def get_item(self, key: str) -> str:
        """Get item from redis.
        """
        self.logger.debug("get redis item", extra={"key": key})
        data = self.client.get(key)
        if data is not None:
            return data.decode("utf-8") if isinstance(data, bytes) else data
        return ""

    def get_item_blocking(self, key: str, delete: bool = True) -> str:
        """GetItemBlocking get key blocking; will delete key after get by default."""
        while True:
            if not delete:
                data = self.client.get(key)
                if data is None:
                    time.sleep(WAIT_DB_KEY_DURATION)
                    continue
                return data.decode("utf-8") if isinstance(data, bytes) else data

            try:
                with self.client.pipeline() as pipe:
                    while True:
                        try:
                            pipe.watch(key)
                            data = pipe.get(key)
                            if data is None:
                                pipe.unwatch()
                                time.sleep(WAIT_DB_KEY_DURATION)
                                break
                            pipe.multi()
                            pipe.delete(key)
                            pipe.execute()
                            return (
                                data.decode("utf-8")
                                if isinstance(data, bytes)
                                else data
                            )
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
        """SetItem set item with expiration in seconds"""
        self.logger.debug("put redis item", extra={"key": key})
        self.client.set(key, val, ex=exp)

    def get_item_with_prefix(self, key_prefix: str) -> dict:
        """GetItemWithPrefix get items with given prefix, return dict { key: val }"""
        self.logger.debug(
            "get redis item with prefix", extra={"key_prefix": key_prefix}
        )
        if key_prefix == "":
            raise ValueError("do not scan all keys")

        keys = list(self.client.scan_iter(match=key_prefix + "*", count=SCAN_COUNT))
        items = {}
        if not keys:
            return items

        values = self.client.mget(keys)
        for key, val in zip(keys, values):
            if val is None:
                continue
            k = key.decode("utf-8") if isinstance(key, bytes) else key
            v = val.decode("utf-8") if isinstance(val, bytes) else val
            items[k] = v

        return items

    def lpop_keys_blocking(self, keys: list) -> tuple:
        """LPopKeysBlocking LPop from multiple keys, returns the first successful (key, value)"""
        while True:
            for key in keys:
                val = self.client.lpop(key)
                if val is not None:
                    value = val.decode("utf-8") if isinstance(val, bytes) else val
                    return key, value
            time.sleep(WAIT_DB_KEY_DURATION)

    def rpush(self, key: str, *payloads) -> None:
        """RPush rpush keys and truncate its length (default max length is 100)"""
        length = 0
        if random.randint(0, 99) == 0:
            length = self.client.llen(key)

        if length >= 100:
            self.client.ltrim(key, -10, -1)
            self.logger.info("trim array", extra={"key": key})

        self.client.rpush(key, *payloads)
