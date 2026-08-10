import json
import socket
import struct
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "precision-mcp"))

from precision_mcp.transport import BlenderBridge, BridgeProtocolError


def recv_exact(sock, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class TwoCallPeer:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(2)
        self.listener.settimeout(2)
        self.port = self.listener.getsockname()[1]
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.listener.close()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise AssertionError("fake Blender peer thread did not terminate")
        if exc_type is None and self.error is not None:
            raise self.error
        return False

    def run(self):
        try:
            for index in range(2):
                client, _ = self.listener.accept()
                with client:
                    client.settimeout(2)
                    size = struct.unpack("!I", recv_exact(client, 4))[0]
                    request = json.loads(recv_exact(client, size))
                    response = json.dumps({"status": "success", "request_id": request["request_id"], "result": {"index": index}}).encode()
                    client.sendall(struct.pack("!I", len(response)) + response)
                    if client.recv(1) != b"":
                        raise AssertionError("bridge reused a connection after its call returned")
        except BaseException as error:
            self.error = error
        finally:
            self.listener.close()


class SingleCallPeer:
    def __init__(self, responder):
        self.responder = responder
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(2)
        self.port = self.listener.getsockname()[1]
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.listener.close()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise AssertionError("fake Blender peer thread did not terminate")
        if exc_type is None and self.error is not None:
            raise self.error
        return False

    def run(self):
        try:
            client, _ = self.listener.accept()
            with client:
                client.settimeout(2)
                size = struct.unpack("!I", recv_exact(client, 4))[0]
                request = json.loads(recv_exact(client, size))
                for chunk in self.responder(request):
                    client.sendall(chunk)
                    time.sleep(0.01)
                if client.recv(1) != b"":
                    raise AssertionError("bridge left its call socket open")
        except BaseException as error:
            self.error = error
        finally:
            self.listener.close()


def framed_response(response):
    body = json.dumps(response, separators=(",", ":")).encode("utf-8")
    return struct.pack("!I", len(body)) + body


class PrecisionTransportTests(unittest.TestCase):
    def test_bridge_opens_a_fresh_connection_for_each_call(self):
        with TwoCallPeer() as peer:
            bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1)
            self.assertEqual(bridge.call("ping")["index"], 0)
            self.assertEqual(bridge.call("ping")["index"], 1)
        self.assertFalse(peer.thread.is_alive())
        self.assertIsNone(peer.error)

    def test_partial_header_and_body_chunks_are_read_exactly(self):
        def responder(request):
            frame = framed_response(
                {"status": "success", "request_id": request["request_id"], "result": {"ok": True}}
            )
            return [frame[:1], frame[1:3], frame[3:4], frame[4:6], frame[6:11], frame[11:]]

        with SingleCallPeer(responder) as peer:
            bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1)
            self.assertEqual(bridge.call("chunked"), {"ok": True})

    def test_oversized_encoded_payload_is_rejected(self):
        bridge = BlenderBridge("127.0.0.1", 9, max_message_bytes=8)
        with self.assertRaisesRegex(ValueError, "max_message_bytes"):
            bridge._encode({"payload": "too large"})

    def test_oversized_response_frame_is_rejected(self):
        def responder(_request):
            return [struct.pack("!I", 257)]

        with SingleCallPeer(responder) as peer:
            bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1, max_message_bytes=256)
            with self.assertRaisesRegex(BridgeProtocolError, "response exceeds max_message_bytes"):
                bridge.call("oversized")

    def test_mismatched_response_request_id_raises_protocol_error(self):
        def responder(_request):
            return [framed_response({"status": "success", "request_id": "wrong", "result": {}})]

        with SingleCallPeer(responder) as peer:
            bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1)
            with self.assertRaisesRegex(BridgeProtocolError, "request_id mismatch"):
                bridge.call("mismatch")

    def test_error_status_is_propagated(self):
        def responder(request):
            return [
                framed_response(
                    {"status": "error", "request_id": request["request_id"], "message": "operation failed"}
                )
            ]

        with SingleCallPeer(responder) as peer:
            bridge = BlenderBridge("127.0.0.1", peer.port, timeout=1)
            with self.assertRaisesRegex(RuntimeError, "operation failed"):
                bridge.call("fail")


if __name__ == "__main__":
    unittest.main()
