"""Exercise real Redis client parsing/transactions against an offline RESP fixture."""

from contextlib import contextmanager
import socketserver
import threading
import unittest
from unittest.mock import patch

import redis

from kipp.redis.utils import RedisUtils


def response(value, protocol=2):
    if value is None:
        return b"_\r\n" if protocol == 3 else b"$-1\r\n"
    if isinstance(value, int):
        return b":" + str(value).encode() + b"\r\n"
    if isinstance(value, list):
        return (
            b"*"
            + str(len(value)).encode()
            + b"\r\n"
            + b"".join(response(item, protocol) for item in value)
        )
    if isinstance(value, dict):
        return (
            b"%"
            + str(len(value)).encode()
            + b"\r\n"
            + b"".join(
                response(key, protocol) + response(item, protocol)
                for key, item in value.items()
            )
        )
    value = value.encode() if isinstance(value, str) else value
    return b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n"


class RESPFixture(socketserver.StreamRequestHandler):
    def handle(self):
        self.protocol = 2
        transaction = None
        while True:
            header = self.rfile.readline()
            if not header:
                return
            count = int(header[1:])
            command = []
            for _ in range(count):
                length = int(self.rfile.readline()[1:])
                command.append(self.rfile.read(length))
                self.rfile.read(2)
            self.server.commands.append(command)
            name = command[0].upper()
            if name == b"HELLO":
                protocol = int(command[1])
                hello = {
                    b"server": b"redis",
                    b"version": b"7.4.0",
                    b"proto": protocol,
                    b"id": 1,
                    b"mode": b"standalone",
                    b"role": b"master",
                    b"modules": [],
                }
                if protocol == 2:
                    hello = [value for pair in hello.items() for value in pair]
                self.protocol = protocol
                self.wfile.write(response(hello, protocol))
            elif name == b"CLIENT":
                self.wfile.write(b"+OK\r\n")
            elif name in (b"WATCH", b"UNWATCH"):
                self.wfile.write(b"+OK\r\n")
            elif name == b"MULTI":
                transaction = []
                self.wfile.write(b"+OK\r\n")
            elif name == b"EXEC":
                values = [self.dispatch(item) for item in transaction]
                transaction = None
                self.wfile.write(response(values, self.protocol))
            elif transaction is not None:
                transaction.append(command)
                self.wfile.write(b"+QUEUED\r\n")
            else:
                self.wfile.write(response(self.dispatch(command), self.protocol))

    def dispatch(self, command):
        name = command[0].upper()
        values = self.server.values
        if name == b"SET":
            values[command[1]] = command[2]
            return b"OK"
        if name == b"GET":
            return values.get(command[1])
        if name == b"DEL":
            return int(values.pop(command[1], None) is not None)
        if name == b"SCAN":
            return [b"0", sorted(key for key in values if key.startswith(b"pref:"))]
        if name == b"MGET":
            return [values.get(key) for key in command[1:]]
        if name == b"LPOP":
            return b"queued"
        if name in (b"RPUSH", b"LLEN"):
            return 1
        if name == b"LTRIM":
            return b"OK"
        raise AssertionError("Unexpected offline command: %r" % command)


@contextmanager
def offline_client(protocol, decode_responses=False):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), RESPFixture)
    server.daemon_threads = True
    server.values = {}
    server.commands = []
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = redis.Redis(
        host="127.0.0.1",
        port=server.server_address[1],
        protocol=protocol,
        decode_responses=decode_responses,
        socket_timeout=2,
        socket_connect_timeout=2,
        retry=redis.retry.Retry(redis.backoff.NoBackoff(), 0),
    )
    try:
        yield client, server
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


class OfflineRetryError(BaseException):
    """Abort an unexpected fixture retry before a blocking helper can loop."""


class RedisClientCompatibilityTests(unittest.TestCase):
    def test_real_command_encoding_response_decoding_and_transaction(self):
        for protocol in (2, 3):
            for decoded in (False, True):
                with self.subTest(protocol=protocol, decoded=decoded):
                    with offline_client(protocol, decoded) as (client, fixture):
                        helper = RedisUtils(client)
                        helper.set_item("pref:a", "中文", 30)
                        self.assertEqual(helper.get_item("pref:a"), "中文")
                        self.assertEqual(helper.get_item("missing"), "")
                        self.assertEqual(
                            helper.get_item_with_prefix("pref:"), {"pref:a": "中文"}
                        )
                        with patch(
                            "kipp.redis.utils.time.sleep",
                            side_effect=OfflineRetryError(
                                "Unexpected offline transaction retry"
                            ),
                        ):
                            self.assertEqual(helper.get_item_blocking("pref:a"), "中文")
                        self.assertEqual(helper.get_item("pref:a"), "")
                        self.assertEqual(
                            helper.lpop_keys_blocking(["queue"]), ("queue", "queued")
                        )
                        with patch("kipp.redis.utils.random.randint", return_value=1):
                            helper.rpush("queue", "next")
                        self.assertIn(
                            [b"SET", b"pref:a", "中文".encode(), b"EX", b"30"],
                            fixture.commands,
                        )
                        self.assertIn([b"WATCH", b"pref:a"], fixture.commands)
                        self.assertIn([b"MULTI"], fixture.commands)
                        self.assertIn([b"DEL", b"pref:a"], fixture.commands)
                        self.assertIn([b"EXEC"], fixture.commands)


if __name__ == "__main__":
    unittest.main()
