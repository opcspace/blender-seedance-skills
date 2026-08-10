"""Legacy CAD direct-socket diagnostic; this is not Precision Core V2 proof."""

import json
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def call(command, params=None):
    with socket.create_connection(("127.0.0.1", 9877), timeout=20) as sock:
        sock.sendall(json.dumps({"type": command, "params": params or {}}).encode())
        data = sock.recv(65536)
    response = json.loads(data.decode())
    if response.get("status") == "error":
        raise RuntimeError(response.get("message"))
    return response["result"]


status = call("precision_cad_status")
print("CAD_STATUS", status)
assert status["available"] is True
result = call("precision_create_cad_rectangle", {"name": "PRECISION_CAD_Rectangle", "width": 3.0, "height": 2.0})
print("CAD_RECTANGLE", result)
assert result["solved"] is True
assert result["target_dimensions"] == [3.0, 2.0]
assert result["constraint_count"] >= 6
