"""Length-prefixed request transport for the Blender precision bridge."""

from __future__ import annotations

import json
import socket
import struct
import uuid
from typing import Any


MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class BridgeProtocolError(RuntimeError):
    """Raised when the Blender bridge violates the framed protocol."""


def read_exact(sock: socket.socket, size: int) -> bytes:
    """Read exactly ``size`` bytes or fail if the peer closes early."""
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("Blender bridge closed before frame completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class BlenderBridge:
    """Make one framed Blender bridge request per fresh socket connection."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 180,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_message_bytes = max_message_bytes

    def _encode(self, payload: dict[str, Any]) -> bytes:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(body) > self.max_message_bytes:
            raise ValueError("payload exceeds max_message_bytes")
        return struct.pack("!I", len(body)) + body

    def call(self, command: str, params: dict[str, Any] | None = None) -> Any:
        request_id = uuid.uuid4().hex
        request = {
            "request_id": request_id,
            "type": command,
            "params": params or {},
        }
        with socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        ) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(self._encode(request))
            response_size = struct.unpack("!I", read_exact(sock, 4))[0]
            if response_size > self.max_message_bytes:
                raise BridgeProtocolError("response exceeds max_message_bytes")
            response = json.loads(
                read_exact(sock, response_size).decode("utf-8")
            )

        if response.get("request_id") != request_id:
            raise BridgeProtocolError("response request_id mismatch")
        if response.get("status") == "error":
            raise RuntimeError(
                response.get("message", "Blender precision command failed")
            )
        return response.get("result", response)
